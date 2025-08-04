from collections import defaultdict, Counter
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import requests
from gitlab_api import simple_gitlab_request, normalize_contributor_name, build_contributor_mapping
from analytics import calculate_health_score, get_activity_sparkline

def analyze_project(project: Dict, gitlab_url: str, gitlab_token: str, days: int = 30) -> Dict[str, Any]:
    """Analyze a single project with 30-day metrics including branch and issue analysis."""
    project_id = project['id']
    project_name = project['name']
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Initialize metrics
    metrics = {
        'id': project_id,
        'name': project_name,
        'path': project.get('path_with_namespace', ''),
        'description': project.get('description', ''),
        'visibility': project.get('visibility', 'private'),
        'default_branch': project.get('default_branch', 'main'),
        'created_at': project.get('created_at', ''),
        'last_activity': project.get('last_activity_at', ''),
        'commits_30d': 0,
        'commits_by_day': defaultdict(int),
        'contributors_30d': 0,
        'contributors': Counter(),
        'code_changes': {},
        'mrs_created': 0,
        'mrs_merged': 0,
        'mrs_closed': 0,
        'open_mrs': 0,
        'issues_created': 0,
        'issues_closed': 0,
        'open_issues': 0,
        'languages': {},
        'days_since_last_commit': 999,
        'activity_sparkline': '',
        'health_score': 0,
        'health_grade': 'D',
        'status': 'inactive',
        'branch_analysis': {},
        'issue_analysis': {},
        'enhancement_metadata': {
            'has_branch_analysis': False,
            'has_issue_analysis': False,
            'analysis_errors': []
        }
    }
    
    # Build contributor mapping
    name_mapping, email_mapping = build_contributor_mapping()
    
    # Get commits from all branches
    branches = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/repository/branches",
        {}
    )
    
    all_commits = []
    commit_ids = set()
    for branch in branches:
        branch_name = branch['name']
        branch_commits = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"projects/{project_id}/repository/commits",
            {
                "ref_name": branch_name,
                "since": start_date.isoformat(),
                "until": end_date.isoformat()
            }
        )
        for commit in branch_commits:
            if commit['id'] not in commit_ids:
                all_commits.append(commit)
                commit_ids.add(commit['id'])
    
    # Client-side date filtering for accuracy
    commits = []
    for commit in all_commits:
        try:
            commit_date = datetime.fromisoformat(
                commit['created_at'].replace('Z', '+00:00')
            )
            if start_date <= commit_date <= end_date:
                commits.append(commit)
        except (ValueError, KeyError) as e:
            print(f"[WARNING] Failed to parse commit date in project {project_name}: {e}")
            continue
    
    if commits:
        metrics['commits_30d'] = len(commits)
        # Prepare code change summary
        code_changes = {}
        for commit in commits:
            author_name = commit.get('author_name', 'Unknown')
            author_email = commit.get('author_email', '')
            normalized_author = normalize_contributor_name(
                author_name, author_email, name_mapping, email_mapping
            )
            metrics['contributors'][normalized_author] += 1
            commit_date = datetime.fromisoformat(commit['created_at'].replace('Z', '+00:00')).date()
            metrics['commits_by_day'][str(commit_date)] += 1
            
            # Get code change stats
            sha = commit['id']
            stats_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/commits/{sha}"
            try:
                resp = requests.get(stats_url, headers={"Authorization": f"Bearer {gitlab_token}"})
                if resp.status_code == 200:
                    stats = resp.json()
                    additions = stats.get('stats', {}).get('additions', 0)
                    deletions = stats.get('stats', {}).get('deletions', 0)
                else:
                    additions = 0
                    deletions = 0
            except Exception as e:
                print(f"[WARNING] Failed to get commit stats for {sha}: {e}")
                additions = 0
                deletions = 0
            if normalized_author not in code_changes:
                code_changes[normalized_author] = {'additions': 0, 'deletions': 0, 'commits': 0}
            code_changes[normalized_author]['additions'] += additions
            code_changes[normalized_author]['deletions'] += deletions
            code_changes[normalized_author]['commits'] += 1
        metrics['contributors_30d'] = len(metrics['contributors'])
        last_commit_date = datetime.fromisoformat(commits[0]['created_at'].replace('Z', '+00:00'))
        metrics['days_since_last_commit'] = (end_date - last_commit_date).days
        metrics['code_changes'] = code_changes
    
    # Get merge requests
    all_mrs = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/merge_requests",
        {
            "created_after": start_date.isoformat(),
            "created_before": end_date.isoformat(),
            "scope": "all"
        }
    )
    
    # Get all MRs to count open ones
    all_current_mrs = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/merge_requests",
        {"state": "opened"}
    )
    metrics['open_mrs'] = len(all_current_mrs) if all_current_mrs else 0
    
    # Process MRs with client-side date filtering
    for mr in all_mrs:
        try:
            created_at = datetime.fromisoformat(mr['created_at'].replace('Z', '+00:00'))
            
            if start_date <= created_at <= end_date:
                metrics['mrs_created'] += 1
                if mr['state'] == 'merged':
                    metrics['mrs_merged'] += 1
                elif mr['state'] == 'closed':
                    metrics['mrs_closed'] += 1
        except (ValueError, KeyError) as e:
            print(f"[WARNING] Failed to parse MR date in project {project_name}: {e}")
            continue
    
    # Get issues
    all_issues = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/issues",
        {
            "created_after": start_date.isoformat(),
            "created_before": end_date.isoformat(),
            "scope": "all"
        }
    )
    
    # Get all current open issues
    all_current_issues = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/issues",
        {"state": "opened"}
    )
    metrics['open_issues'] = len(all_current_issues) if all_current_issues else 0
    
    # Process issues with client-side date filtering
    for issue in all_issues:
        try:
            created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            
            if start_date <= created_at <= end_date:
                metrics['issues_created'] += 1
                if issue['state'] == 'closed':
                    metrics['issues_closed'] += 1
        except (ValueError, KeyError) as e:
            print(f"[WARNING] Failed to parse issue date in project {project_name}: {e}")
            continue
    
    # Get languages
    try:
        languages_response = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"projects/{project_id}/languages",
            {}
        )
        if isinstance(languages_response, dict):
            metrics['languages'] = languages_response
    except:
        pass
    
    # Generate activity sparkline for last 14 days
    daily_values = []
    for i in range(14):
        date = (end_date - timedelta(days=13-i)).date()
        daily_values.append(metrics['commits_by_day'].get(str(date), 0))
    
    metrics['activity_sparkline'] = get_activity_sparkline(daily_values)
    
    # Calculate health score and grade
    metrics['health_score'], metrics['health_grade'] = calculate_health_score(metrics)
    
    # Determine status
    if metrics['days_since_last_commit'] < 7:
        metrics['status'] = 'active'
    elif metrics['days_since_last_commit'] < 30:
        metrics['status'] = 'maintenance'
    else:
        metrics['status'] = 'inactive'
    
    return metrics

def analyze_project_multi_period(project: Dict, gitlab_url: str, gitlab_token: str) -> Dict[str, Any]:
    """Analyze a single project across multiple time periods (7, 15, 30, 60, 90 days)."""
    project_id = project['id']
    project_name = project['name']
    
    # Define time periods
    periods = [7, 15, 30, 60, 90]
    period_metrics = {}
    
    for days in periods:
        print(f"    [INFO] Analyzing {project_name} for {days} days...")
        period_metrics[f'{days}d'] = analyze_project(project, gitlab_url, gitlab_token, days)
    
    # Calculate trends
    trends = calculate_period_trends(period_metrics)
    
    return {
        'project_name': project_name,
        'project_id': project_id,
        'periods': period_metrics,
        'trends': trends
    }

def calculate_period_trends(period_metrics: Dict[str, Dict]) -> Dict[str, Any]:
    """Calculate trends across different time periods."""
    trends = {
        'commits_trend': {},
        'code_changes_trend': {},
        'contributors_trend': {},
        'health_score_trend': {}
    }
    
    periods = ['7d', '15d', '30d', '60d', '90d']
    
    for i in range(1, len(periods)):
        current_period = periods[i]
        prev_period = periods[i-1]
        
        current_metrics = period_metrics[current_period]
        prev_metrics = period_metrics[prev_period]
        
        # Commits trend
        current_commits = current_metrics.get('commits_30d', 0)
        prev_commits = prev_metrics.get('commits_30d', 0)
        if prev_commits > 0:
            trends['commits_trend'][f'{prev_period}_to_{current_period}'] = {
                'change': current_commits - prev_commits,
                'percentage': ((current_commits - prev_commits) / prev_commits) * 100
            }
        
        # Code changes trend
        current_additions = sum(c['additions'] for c in current_metrics.get('code_changes', {}).values())
        prev_additions = sum(c['additions'] for c in prev_metrics.get('code_changes', {}).values())
        if prev_additions > 0:
            trends['code_changes_trend'][f'{prev_period}_to_{current_period}'] = {
                'additions_change': current_additions - prev_additions,
                'additions_percentage': ((current_additions - prev_additions) / prev_additions) * 100
            }
        
        # Contributors trend
        current_contributors = current_metrics.get('contributors_30d', 0)
        prev_contributors = prev_metrics.get('contributors_30d', 0)
        if prev_contributors > 0:
            trends['contributors_trend'][f'{prev_period}_to_{current_period}'] = {
                'change': current_contributors - prev_contributors,
                'percentage': ((current_contributors - prev_contributors) / prev_contributors) * 100
            }
        
        # Health score trend
        current_health = current_metrics.get('health_score', 0)
        prev_health = prev_metrics.get('health_score', 0)
        if prev_health > 0:
            trends['health_score_trend'][f'{prev_period}_to_{current_period}'] = {
                'change': current_health - prev_health,
                'percentage': ((current_health - prev_health) / prev_health) * 100
            }
    
    return trends

def compare_projects_across_periods(projects_data: List[Dict], gitlab_url: str, gitlab_token: str) -> Dict[str, Any]:
    """Compare multiple projects across different time periods."""
    comparison = {
        'periods': [7, 15, 30, 60, 90],
        'projects': {},
        'rankings': {},
        'summary': {}
    }
    
    # Analyze each project across all periods
    for project in projects_data:
        project_id = project['id']
        project_name = project['name']
        
        print(f"[INFO] Analyzing {project_name} across all periods...")
        multi_period_data = analyze_project_multi_period(project, gitlab_url, gitlab_token)
        comparison['projects'][project_id] = multi_period_data
    
    # Calculate rankings for each period
    for period in comparison['periods']:
        period_key = f'{period}d'
        
        # Health score ranking
        health_scores = []
        for project_id, data in comparison['projects'].items():
            health_score = data['periods'][period_key].get('health_score', 0)
            health_scores.append((project_id, data['project_name'], health_score))
        
        health_scores.sort(key=lambda x: x[2], reverse=True)
        comparison['rankings'][f'health_score_{period_key}'] = health_scores
        
        # Activity ranking (commits)
        commit_counts = []
        for project_id, data in comparison['projects'].items():
            commits = data['periods'][period_key].get('commits_30d', 0)
            commit_counts.append((project_id, data['project_name'], commits))
        
        commit_counts.sort(key=lambda x: x[2], reverse=True)
        comparison['rankings'][f'commits_{period_key}'] = commit_counts
        
        # Code changes ranking
        code_changes = []
        for project_id, data in comparison['projects'].items():
            total_additions = sum(c['additions'] for c in data['periods'][period_key].get('code_changes', {}).values())
            code_changes.append((project_id, data['project_name'], total_additions))
        
        code_changes.sort(key=lambda x: x[2], reverse=True)
        comparison['rankings'][f'code_changes_{period_key}'] = code_changes
    
    return comparison 