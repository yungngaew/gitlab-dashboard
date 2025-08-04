from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta, timezone
import requests

# Health score calculation
def calculate_health_score(metrics: Dict[str, Any]) -> Tuple[int, str]:
    score = 100
    if metrics['commits_30d'] == 0:
        score -= 30
    elif metrics['commits_30d'] < 5:
        score -= 15
    elif metrics['commits_30d'] > 50:
        score += 5
    if metrics['open_issues'] > 20:
        score -= 20
    elif metrics['open_issues'] > 10:
        score -= 10
    elif metrics['open_issues'] < 5:
        score += 5
    if metrics['open_mrs'] > 10:
        score -= 15
    elif metrics['open_mrs'] > 5:
        score -= 5
    if metrics['contributors_30d'] == 1:
        score -= 10
    elif metrics['contributors_30d'] > 3:
        score += 10
    if metrics['days_since_last_commit'] < 3:
        score += 5
    elif metrics['days_since_last_commit'] > 14:
        score -= 20
    score = max(0, min(100, score))
    
    if score >= 95:
        grade = 'A+'
    elif score >= 90:
        grade = 'A'
    elif score >= 85:
        grade = 'A-'
    elif score >= 80:
        grade = 'B+'
    elif score >= 75:
        grade = 'B'
    elif score >= 70:
        grade = 'B-'
    elif score >= 65:
        grade = 'C+'
    elif score >= 60:
        grade = 'C'
    elif score >= 55:
        grade = 'C-'
    else:
        grade = 'D'
    
    return score, grade

# Activity sparkline generation
def get_activity_sparkline(daily_commits: List[int]) -> str:
    if not daily_commits:
        return ""
    max_val = max(daily_commits) if max(daily_commits) > 0 else 1
    normalized = [int(val / max_val * 7) for val in daily_commits]
    sparks = "▁▂▃▄▅▆▇█"
    return ''.join(sparks[n] for n in normalized)

# Issue priority determination
def _determine_priority(labels: List[str]) -> str:
    labels_lower = [label.lower() for label in labels]
    if any('critical' in label or 'urgent' in label for label in labels_lower):
        return 'critical'
    elif any('high' in label for label in labels_lower):
        return 'high'
    elif any('medium' in label for label in labels_lower):
        return 'medium'
    elif any('low' in label for label in labels_lower):
        return 'low'
    return 'medium'

# Issue type determination
def _determine_type(labels: List[str]) -> str:
    labels_lower = [label.lower() for label in labels]
    if any('bug' in label for label in labels_lower):
        return 'bug'
    elif any('feature' in label for label in labels_lower):
        return 'feature'
    elif any('enhancement' in label for label in labels_lower):
        return 'enhancement'
    return 'other'

# Calculate age of issue
def _calculate_age(created_at: str) -> int:
    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc) - created_date).days
    return age

# Check if issue is overdue
def _is_overdue(due_date: Optional[str]) -> bool:
    if not due_date:
        return False
    try:
        if 'T' in due_date:
            due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        else:
            due = datetime.fromisoformat(due_date + 'T23:59:59+00:00')
        return due < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False

# Get initials from name
def get_initials(name: str) -> str:
    if not name:
        return "?"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[:2].upper()

# Generate AI recommendations
def generate_ai_recommendations(issue_analytics: Dict, project_metrics: List[Dict]) -> List[Dict]:
    recommendations = []
    
    # High priority issue alert
    if issue_analytics['by_priority']['critical'] > 3:
        critical_projects = []
        for issue in issue_analytics['all_issues']:
            if issue['priority'] == 'critical' and issue['project_name'] not in critical_projects:
                critical_projects.append(issue['project_name'])
        
        recommendations.append({
            'type': 'critical',
            'title': 'Critical Issues Require Immediate Attention',
            'message': f"{issue_analytics['by_priority']['critical']} critical issues are open",
            'action': 'Allocate senior developers to resolve critical issues immediately',
            'projects': critical_projects[:5]
        })
    
    # Workload imbalance
    workload = issue_analytics['assignee_workload']
    if workload and len(workload) > 1:
        max_load = max(workload.values())
        avg_load = sum(workload.values()) / len(workload)
        if max_load > avg_load * 2:
            overloaded = [k for k, v in workload.items() if v == max_load][0]
            recommendations.append({
                'type': 'high',
                'title': 'Workload Imbalance Detected',
                'message': f"{overloaded} has {max_load} issues (2x average of {avg_load:.1f})",
                'action': 'Redistribute issues to balance team workload',
                'team_member': overloaded
            })
    
    # Bug ratio analysis
    if issue_analytics['total_open'] > 0:
        bug_ratio = issue_analytics['by_type']['bug'] / issue_analytics['total_open']
        if bug_ratio > 0.6:
            recommendations.append({
                'type': 'medium',
                'title': 'High Bug-to-Feature Ratio',
                'message': f"{bug_ratio:.0%} of open issues are bugs",
                'action': 'Schedule dedicated bug-fixing sprint and improve QA processes'
            })
    
    # Stale issues
    if issue_analytics.get('stale_issues', 0) > 10:
        recommendations.append({
            'type': 'medium',
            'title': 'Stale Issues Need Review',
            'message': f"{issue_analytics['stale_issues']} issues haven't been updated in 30+ days",
            'action': 'Review and close or reprioritize stale issues'
        })
    
    # Unassigned issues
    if issue_analytics['unassigned'] > 5:
        recommendations.append({
            'type': 'medium',
            'title': 'Many Unassigned Issues',
            'message': f"{issue_analytics['unassigned']} issues lack assignees",
            'action': 'Assign team members to unowned issues for accountability'
        })
    
    # Positive feedback
    if issue_analytics['total_open'] < 20 and issue_analytics['by_priority']['critical'] == 0:
        recommendations.append({
            'type': 'success',
            'title': 'Excellent Issue Management',
            'message': 'Low issue count with no critical issues',
            'action': 'Maintain current practices and document successful processes'
        })
    
    # Project-specific recommendations
    if issue_analytics['project_issues']:
        sorted_projects = sorted(issue_analytics['project_issues'].items(), 
                               key=lambda x: x[1], reverse=True)
        if sorted_projects[0][1] > 20:
            recommendations.append({
                'type': 'high',
                'title': f'High Issue Concentration in {sorted_projects[0][0]}',
                'message': f'{sorted_projects[0][1]} open issues in one project',
                'action': 'Consider splitting into smaller work items or allocating more resources',
                'project': sorted_projects[0][0]
            })
    
    return recommendations

# Calculate period trends
def calculate_period_trends(period_metrics: Dict[str, Dict]) -> Dict[str, Any]:
    trends = {
        'commits_trend': {},
        'code_changes_trend': {},
        'contributors_trend': {},
        'health_score_trend': {}
    }
    
    periods = ['7d', '15d', '30d', '60d']
    
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

# Calculate aggregate issues
def calculate_aggregate_issues(projects: List[Dict]) -> Dict[str, Any]:
    total_open = 0
    total_recommendations = []
    projects_with_issues = 0
    issue_types = defaultdict(int)
    issue_priorities = defaultdict(int)
    
    for project in projects:
        issue_analysis = project.get('issue_analysis', {})
        if issue_analysis and not issue_analysis.get('error'):
            projects_with_issues += 1
            total_open += issue_analysis.get('total_open', 0)
            
            # Aggregate recommendations
            for rec in issue_analysis.get('recommendations', []):
                total_recommendations.append({
                    'project': project['name'],
                    'project_id': project['id'],
                    **rec
                })
            
            # Aggregate issue types and priorities
            by_type = issue_analysis.get('by_type', {})
            by_priority = issue_analysis.get('by_priority', {})
            
            for issue_type, count in by_type.items():
                issue_types[issue_type] += count
            
            for priority, count in by_priority.items():
                issue_priorities[priority] += count
    
    # Sort recommendations by priority
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    total_recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'info'), 5))
    
    return {
        'total_open_issues': total_open,
        'projects_with_analysis': projects_with_issues,
        'total_projects': len(projects),
        'recommendations': total_recommendations[:10],
        'all_recommendations': total_recommendations,
        'issue_types': dict(issue_types),
        'issue_priorities': dict(issue_priorities)
    } 