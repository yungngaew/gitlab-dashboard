from collections import defaultdict, Counter
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from gitlab_api import simple_gitlab_request, get_all_group_ids
from project_analytics import analyze_project
from issue_analytics import collect_issue_analytics, collect_all_issues
from team_analytics import analyze_team_performance
from analytics import generate_ai_recommendations, calculate_aggregate_issues

def analyze_groups(group_ids: List[int], gitlab_url: str, gitlab_token: str, days: int = 30) -> Dict[str, Any]:
    """Analyze multiple GitLab groups with project-based grouping instead of group-based."""
    print(f"[INFO] Analyzing {len(group_ids)} groups over {days} days...")
    
    report_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'start_date': (datetime.now() - timedelta(days=days)).isoformat(),
            'end_date': datetime.now().isoformat(),
            'groups_analyzed': len(group_ids)
        },
        'summary': {
            'total_projects': 0,
            'active_projects': 0,
            'total_commits': 0,
            'total_mrs': 0,
            'total_issues': 0,
            'unique_contributors': set(),
            'health_distribution': {'A+': 0, 'A': 0, 'A-': 0, 'B+': 0, 'B': 0, 'B-': 0, 'C+': 0, 'C': 0, 'C-': 0, 'D': 0}
        },
        'groups': {},  # This will contain actual group data
        'projects': [],
        'contributors': Counter(),
        'daily_activity': defaultdict(int),
        'technology_stack': Counter()
    }
    
    # Track unique projects by ID to avoid duplicates
    unique_projects = {}  # project_id -> project_data
    project_groups = {}   # project_id -> list of group_ids
    group_data = {}       # group_id -> group_info

    # Collect all projects from all groups first
    all_projects = []
    
    for group_id in group_ids:
        print(f"  [INFO] Analyzing group {group_id}...")
        
        # Get group info
        group_info = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"groups/{group_id}",
            {}
        )
        
        if group_info and isinstance(group_info, dict):
            group_data[group_id] = {
                'id': group_id,
                'name': group_info.get('name', f'Group {group_id}'),
                'path': group_info.get('path', ''),
                'description': group_info.get('description', ''),
                'projects_count': group_info.get('projects_count', 0),
                'total_commits': 0,
                'total_mrs': 0,
                'total_issues': 0,
                'active_projects': 0,
                'health_grade': 'D'
            }
        else:
            # Fallback if group info is not available
            group_data[group_id] = {
                'id': group_id,
                'name': f'Group {group_id}',
                'path': '',
                'description': '',
                'projects_count': 0,
                'total_commits': 0,
                'total_mrs': 0,
                'total_issues': 0,
                'active_projects': 0,
                'health_grade': 'D'
            }
        
        # Get projects in group
        projects = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"groups/{group_id}/projects",
            {"include_subgroups": "true", "archived": "false"}
        )
        
        for project in projects:
            project_id = project['id']
            project_name = project['name']
            
            # Check if project already exists
            if project_id in unique_projects:
                print(f"      [INFO] Project {project_name} already found, adding to existing...")
                # Add group info to existing project
                if project_id not in project_groups:
                    project_groups[project_id] = []
                project_groups[project_id].append(group_id)
                continue
            
            print(f"    [INFO] Found project: {project_name} (ID: {project_id})")
            
            # Analyze project
            project_metrics = analyze_project(project, gitlab_url, gitlab_token, days)
            
            # Store unique project
            unique_projects[project_id] = project_metrics
            project_groups[project_id] = [group_id]
            all_projects.append(project_metrics)
    
    # Store actual group data
    report_data['groups'] = group_data
    
    # Now process unique projects for global statistics
    print(f"\n[INFO] Processing {len(unique_projects)} unique projects...")
    
    for project_id, project_metrics in unique_projects.items():
        # Update global statistics
        report_data['summary']['total_commits'] += project_metrics['commits_30d']
        report_data['summary']['total_mrs'] += project_metrics['mrs_created']
        report_data['summary']['total_issues'] += project_metrics['issues_created']
        
        if project_metrics['status'] == 'active':
            report_data['summary']['active_projects'] += 1
        
        # Track contributors
        for contributor, count in project_metrics['contributors'].items():
            report_data['contributors'][contributor] += count
            report_data['summary']['unique_contributors'].add(contributor)
        
        # Track daily activity
        for date, commits in project_metrics['commits_by_day'].items():
            report_data['daily_activity'][date] += commits
        
        # Track technology stack
        for lang, percentage in project_metrics['languages'].items():
            report_data['technology_stack'][lang] += 1
        
        # Track health distribution
        report_data['summary']['health_distribution'][project_metrics['health_grade']] += 1
        
        # Add group information to project
        project_metrics['groups'] = project_groups.get(project_id, [])
        
        # Add to global projects list
        report_data['projects'].append(project_metrics)
    
    # Update group statistics
    for group_id, group_info in group_data.items():
        group_commits = 0
        group_mrs = 0
        group_issues = 0
        group_active_projects = 0
        group_health_scores = []
        
        for project in report_data['projects']:
            if group_id in project.get('groups', []):
                group_commits += project['commits_30d']
                group_mrs += project['mrs_created']
                group_issues += project['issues_created']
                if project['status'] == 'active':
                    group_active_projects += 1
                group_health_scores.append(project['health_score'])
        
        group_info['total_commits'] = group_commits
        group_info['total_mrs'] = group_mrs
        group_info['total_issues'] = group_issues
        group_info['active_projects'] = group_active_projects
        
        # Calculate average health grade for group
        if group_health_scores:
            avg_health = sum(group_health_scores) / len(group_health_scores)
            if avg_health >= 90:
                group_info['health_grade'] = 'A+'
            elif avg_health >= 80:
                group_info['health_grade'] = 'A'
            elif avg_health >= 70:
                group_info['health_grade'] = 'B'
            elif avg_health >= 60:
                group_info['health_grade'] = 'C'
            else:
                group_info['health_grade'] = 'D'
    
    # Convert sets to counts
    report_data['summary']['unique_contributors'] = len(report_data['summary']['unique_contributors'])
    report_data['summary']['total_projects'] = len(unique_projects)
    
    # Sort projects by health score
    report_data['projects'].sort(key=lambda x: x['health_score'], reverse=True)
    
    # Collect comprehensive issue analytics
    print("\n[INFO] Collecting issue analytics across all projects...")
    report_data['issue_analytics'] = collect_issue_analytics(report_data['projects'], gitlab_url, gitlab_token)
    
    # Generate AI recommendations
    print("[INFO] Generating AI recommendations...")
    report_data['ai_recommendations'] = generate_ai_recommendations(
        report_data['issue_analytics'], 
        report_data['projects']
    )
    
    # Analyze team performance
    print("[INFO] Analyzing team performance...")
    report_data['team_analytics'] = analyze_team_performance(report_data['projects'], gitlab_url, gitlab_token, days)
    
    # Collect all issues for Issues Management section
    print("[INFO] Collecting all open issues...")
    report_data['all_issues'] = collect_all_issues(report_data['projects'], gitlab_url, gitlab_token)

    if len(all_projects) > 1:
        print("[INFO] Performing cross-period comparison...")
        from project_analytics import compare_projects_across_periods
        report_data['cross_period_comparison'] = compare_projects_across_periods(
            all_projects, gitlab_url, gitlab_token
        )
    
    return report_data 