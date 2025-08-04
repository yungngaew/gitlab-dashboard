from collections import defaultdict, Counter
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from gitlab_api import simple_gitlab_request, normalize_contributor_name, build_contributor_mapping
from analytics import _is_overdue

def analyze_team_performance(projects: List[Dict], gitlab_url: str, gitlab_token: str, days: int = 30) -> Dict[str, Any]:
    """Analyze detailed team member contributions and workload with accurate date filtering."""
    team_analytics = {}
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Build contributor mapping for normalization
    name_mapping, email_mapping = build_contributor_mapping()
    
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', 'Unknown')
        
        try:
            # Get commits with consistent API parameters
            all_commits = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/repository/commits",
                {
                    "since": start_date.isoformat(),
                    "until": end_date.isoformat()
                }
            )
            
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
                    print(f"[WARNING] Failed to parse commit date: {e}")
                    continue
            
            for commit in commits:
                author_name = commit.get('author_name', 'Unknown')
                author_email = commit.get('author_email', '')
                
                # Normalize contributor name
                normalized_author = normalize_contributor_name(
                    author_name, author_email, name_mapping, email_mapping
                )
                
                if normalized_author not in team_analytics:
                    team_analytics[normalized_author] = {
                        'commits': 0,
                        'projects': set(),
                        'issues_assigned': 0,
                        'issues_resolved': 0,
                        'merge_requests': 0,
                        'recent_activity': [],
                        'current_workload': {
                            'open_issues': 0,
                            'open_mrs': 0,
                            'overdue_issues': 0
                        }
                    }
                
                team_analytics[normalized_author]['commits'] += 1
                team_analytics[normalized_author]['projects'].add(project_name)
                team_analytics[normalized_author]['recent_activity'].append({
                    'type': 'commit',
                    'project': project_name,
                    'date': commit['created_at'],
                    'message': commit['title']
                })
            
            # Get merge requests with consistent date filtering
            all_mrs = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/merge_requests",
                {
                    "created_after": start_date.isoformat(),
                    "created_before": end_date.isoformat()
                }
            )
            
            # Client-side date filtering for merge requests
            mrs = []
            for mr in all_mrs:
                try:
                    created_at = datetime.fromisoformat(
                        mr['created_at'].replace('Z', '+00:00')
                    )
                    if start_date <= created_at <= end_date:
                        mrs.append(mr)
                except (ValueError, KeyError) as e:
                    print(f"[WARNING] Failed to parse MR date: {e}")
                    continue
            
            for mr in mrs:
                author_name = mr.get('author', {}).get('name', 'Unknown')
                author_email = mr.get('author', {}).get('email', '')
                
                # Normalize contributor name
                normalized_author = normalize_contributor_name(
                    author_name, author_email, name_mapping, email_mapping
                )
                
                if normalized_author not in team_analytics:
                    team_analytics[normalized_author] = {
                        'commits': 0,
                        'projects': set(),
                        'issues_assigned': 0,
                        'issues_resolved': 0,
                        'merge_requests': 0,
                        'recent_activity': [],
                        'current_workload': {
                            'open_issues': 0,
                            'open_mrs': 0,
                            'overdue_issues': 0
                        }
                    }
                
                team_analytics[normalized_author]['merge_requests'] += 1
                team_analytics[normalized_author]['projects'].add(project_name)
            
            # Get issues with date filtering for created/resolved within period
            all_issues = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/issues",
                {
                    "created_after": start_date.isoformat(),
                    "created_before": end_date.isoformat(),
                    "scope": "all"
                }
            )
            
            for issue in all_issues:
                try:
                    created_at = datetime.fromisoformat(
                        issue['created_at'].replace('Z', '+00:00')
                    )
                    
                    # Check if created within our time period
                    if start_date <= created_at <= end_date:
                        assignee = issue.get('assignee')
                        if assignee:
                            assignee_name = assignee.get('name', 'Unknown')
                            assignee_email = assignee.get('email', '')
                            
                            # Normalize contributor name
                            normalized_assignee = normalize_contributor_name(
                                assignee_name, assignee_email, name_mapping, email_mapping
                            )
                            
                            if normalized_assignee not in team_analytics:
                                team_analytics[normalized_assignee] = {
                                    'commits': 0,
                                    'projects': set(),
                                    'issues_assigned': 0,
                                    'issues_resolved': 0,
                                    'merge_requests': 0,
                                    'recent_activity': [],
                                    'current_workload': {
                                        'open_issues': 0,
                                        'open_mrs': 0,
                                        'overdue_issues': 0
                                    }
                                }
                            
                            if issue['state'] == 'opened':
                                team_analytics[normalized_assignee]['issues_assigned'] += 1
                            else:
                                team_analytics[normalized_assignee]['issues_resolved'] += 1
                            
                            team_analytics[normalized_assignee]['projects'].add(project_name)
                
                except (ValueError, KeyError) as e:
                    print(f"[WARNING] Failed to parse issue date: {e}")
                    continue
            
            # Get CURRENT open issues and MRs for workload tracking
            current_open_issues = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/issues",
                {"state": "opened"}
            )
            
            current_open_mrs = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/merge_requests",
                {"state": "opened"}
            )
            
            # Track current workload
            for issue in current_open_issues:
                assignee = issue.get('assignee')
                if assignee:
                    assignee_name = assignee.get('name', 'Unknown')
                    assignee_email = assignee.get('email', '')
                    
                    normalized_assignee = normalize_contributor_name(
                        assignee_name, assignee_email, name_mapping, email_mapping
                    )
                    
                    if normalized_assignee not in team_analytics:
                        team_analytics[normalized_assignee] = {
                            'commits': 0,
                            'projects': set(),
                            'issues_assigned': 0,
                            'issues_resolved': 0,
                            'merge_requests': 0,
                            'recent_activity': [],
                            'current_workload': {
                                'open_issues': 0,
                                'open_mrs': 0,
                                'overdue_issues': 0
                            }
                        }
                    
                    team_analytics[normalized_assignee]['current_workload']['open_issues'] += 1
                    team_analytics[normalized_assignee]['projects'].add(project_name)
                    
                    # Check if overdue
                    if _is_overdue(issue.get('due_date')):
                        team_analytics[normalized_assignee]['current_workload']['overdue_issues'] += 1
            
            # Track current MR workload
            for mr in current_open_mrs:
                author_name = mr.get('author', {}).get('name', 'Unknown')
                author_email = mr.get('author', {}).get('email', '')
                
                normalized_author = normalize_contributor_name(
                    author_name, author_email, name_mapping, email_mapping
                )
                
                if normalized_author not in team_analytics:
                    team_analytics[normalized_author] = {
                        'commits': 0,
                        'projects': set(),
                        'issues_assigned': 0,
                        'issues_resolved': 0,
                        'merge_requests': 0,
                        'recent_activity': [],
                        'current_workload': {
                            'open_issues': 0,
                            'open_mrs': 0,
                            'overdue_issues': 0
                        }
                    }
                
                team_analytics[normalized_author]['current_workload']['open_mrs'] += 1
                team_analytics[normalized_author]['projects'].add(project_name)
                    
        except Exception as e:
            print(f"[WARNING] Failed to analyze project {project_name}: {e}")
            continue
    
    # Convert sets to lists for JSON serialization
    for member in team_analytics:
        team_analytics[member]['projects'] = sorted(list(team_analytics[member]['projects']))
        # Keep only recent 10 activities
        team_analytics[member]['recent_activity'] = \
            sorted(team_analytics[member]['recent_activity'], 
                   key=lambda x: x['date'], reverse=True)[:10]
    
    return team_analytics 