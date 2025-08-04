from collections import defaultdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from gitlab_api import simple_gitlab_request
from analytics import _determine_priority, _determine_type, _calculate_age, _is_overdue

def collect_issue_analytics(projects: List[Dict], gitlab_url: str, gitlab_token: str) -> Dict[str, Any]:
    """Collect comprehensive issue analytics across all projects."""
    analytics = {
        'total_open': 0,
        'by_priority': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
        'by_type': {'bug': 0, 'feature': 0, 'enhancement': 0, 'other': 0},
        'by_state': {'to_do': 0, 'in_progress': 0, 'in_review': 0, 'blocked': 0, 'other': 0},
        'overdue': 0,
        'unassigned': 0,
        'stale_issues': 0,
        'project_issues': {},
        'assignee_workload': {},
        'all_issues': [],
        'board_labels_used': False
    }
    
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', 'Unknown')
        
        issues = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"projects/{project_id}/issues",
            {"state": "opened"}
        )
        
        project_issue_count = 0
        
        # Process each issue
        for issue in issues:
            labels = [label.lower() for label in issue.get('labels', [])]
            is_closed = (
                issue['state'] == 'closed'
                or 'complete' in labels
                or 'done' in labels
                or 'finished' in labels
            )
            # Aggregate only if not closed (not complete)
            if not is_closed:
                analytics['total_open'] += 1
                project_issue_count += 1
                
                # Categorize by labels
                priority = _determine_priority(labels)
                issue_type = _determine_type(labels)
                
                analytics['by_priority'][priority] += 1
                analytics['by_type'][issue_type] += 1
                
                # Determine workflow state (simplified)
                workflow_state = 'in_progress' if issue.get('assignee') else 'to_do'
                if any('blocked' in label for label in labels):
                    workflow_state = 'blocked'
                
                analytics['by_state'][workflow_state] += 1
                
                # Check if overdue
                if _is_overdue(issue.get('due_date')):
                    analytics['overdue'] += 1
                
                # Check if stale (not updated in 30 days)
                if _calculate_age(issue.get('updated_at', issue['created_at'])) > 30:
                    analytics['stale_issues'] += 1
                
                # Track assignee workload
                assignee = issue.get('assignee')
                if assignee and issue['state'] == 'opened':
                    assignee_name = assignee.get('name', 'Unknown')
                    analytics['assignee_workload'][assignee_name] = \
                        analytics['assignee_workload'].get(assignee_name, 0) + 1
                else:
                    analytics['unassigned'] += 1
            # Collect enriched issue data (always, but override state if complete)
            enriched_issue = {
                'id': issue['id'],
                'iid': issue['iid'],
                'title': issue['title'],
                'project_id': project_id,
                'project_name': project_name,
                'priority': _determine_priority(labels),
                'type': _determine_type(labels),
                'labels': labels,
                'assignee': issue.get('assignee'),
                'state': 'closed' if is_closed else issue['state'],
                'workflow_state': 'in_progress' if issue.get('assignee') else 'to_do',
                'created_at': issue['created_at'],
                'updated_at': issue['updated_at'],
                'due_date': issue.get('due_date'),
                'web_url': issue['web_url'],
                'age_days': _calculate_age(issue['created_at']),
                'is_overdue': _is_overdue(issue.get('due_date'))
            }
            analytics['all_issues'].append(enriched_issue)
        
        if project_issue_count > 0:
            analytics['project_issues'][project_name] = project_issue_count
    
    return analytics

def collect_all_issues(projects: List[Dict], gitlab_url: str, gitlab_token: str) -> List[Dict]:
    """Collect opened and in-progress issues across projects with full details."""
    all_issues = []
    assignee_workload = defaultdict(lambda: {
        'total_issues': 0,
        'overdue_issues': 0,
        'critical_issues': 0,
        'high_priority_issues': 0
    })
    
    print(f"[INFO] Starting to collect opened and in-progress issues from {len(projects)} projects...")
    
    for project in projects:
        try:
            print(f"    [INFO] Collecting issues for project: {project.get('name', 'Unknown')} (ID: {project.get('id', 'Unknown')})")
            
            # Get opened issues
            opened_issues = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project['id']}/issues",
                {
                    "state": "opened",
                    "per_page": 100,
                    "order_by": "created_at",
                    "sort": "desc"
                }
            )
            
            print(f"      [INFO] Found {len(opened_issues)} opened issues in {project.get('name', 'Unknown')}")
            
            for issue in opened_issues:
                # Enhanced priority detection from labels
                labels = issue.get('labels', [])
                priority = 'medium'  # default
                priority_labels = [label.lower() for label in labels]
                # เพิ่ม pattern สำหรับ label ที่ขึ้นต้นด้วย 'prio:' หรือ 'priority-'
                if any(
                    'critical' in label or 'urgent' in label or 'p0' in label or
                    label.startswith('prio: critical') or label.startswith('priority-critical') or label.startswith('priority:critical')
                    for label in priority_labels):
                    priority = 'critical'
                elif any(
                    'high' in label or 'p1' in label or
                    label.startswith('prio: high') or label.startswith('priority-high') or label.startswith('priority:high')
                    for label in priority_labels):
                    priority = 'high'
                elif any(
                    'low' in label or 'p3' in label or
                    label.startswith('prio: low') or label.startswith('priority-low') or label.startswith('priority:low')
                    for label in priority_labels):
                    priority = 'low'
                
                # Enhanced type detection
                issue_type = 'other'
                type_labels = [label.lower() for label in labels]
                if any('bug' in label or 'defect' in label for label in type_labels):
                    issue_type = 'bug'
                elif any('feature' in label or 'enhancement' in label or 'improvement' in label for label in type_labels):
                    issue_type = 'feature'
                elif any('task' in label for label in type_labels):
                    issue_type = 'task'
                
                # Calculate age
                try:
                    created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                    age_days = (datetime.now(timezone.utc) - created_at).days
                except (ValueError, KeyError):
                    age_days = 0
                
                # Check if overdue
                is_overdue = False
                if issue.get('due_date'):
                    try:
                        if 'T' in issue['due_date']:
                            due_date = datetime.fromisoformat(issue['due_date'].replace('Z', '+00:00'))
                        else:
                            due_date = datetime.fromisoformat(issue['due_date'] + 'T23:59:59+00:00')
                        is_overdue = datetime.now(timezone.utc) > due_date
                    except (ValueError, TypeError):
                        is_overdue = False
                
                # Track assignee workload (only for opened issues)
                assignee = issue.get('assignee')
                if assignee:
                    assignee_name = assignee.get('name', 'Unknown') if assignee else 'Unknown'
                    assignee_workload[assignee_name]['total_issues'] += 1
                    
                    if is_overdue:
                        assignee_workload[assignee_name]['overdue_issues'] += 1
                    
                    if priority == 'critical':
                        assignee_workload[assignee_name]['critical_issues'] += 1
                    elif priority == 'high':
                        assignee_workload[assignee_name]['high_priority_issues'] += 1
                
                # Enrich issue data
                enriched_issue = {
                    'id': issue['id'],
                    'iid': issue['iid'],
                    'title': issue['title'],
                    'description': issue.get('description', ''),
                    'project_id': project['id'],
                    'project_name': project['name'],
                    'state': issue['state'],
                    'created_at': issue['created_at'],
                    'updated_at': issue['updated_at'],
                    'due_date': issue.get('due_date'),
                    'labels': labels,
                    'assignee': assignee or {},
                    'author': issue.get('author', {}),
                    'weight': issue.get('weight', 0),
                    'web_url': issue['web_url'],
                    'priority': priority,
                    'type': issue_type,
                    'age_days': age_days,
                    'is_overdue': is_overdue,
                    'assignee_workload': assignee_workload.get((assignee or {}).get('name', 'Unknown'), {})
                }
                
                all_issues.append(enriched_issue)
                
        except Exception as e:
            print(f"[WARNING] Failed to collect issues for project {project.get('name', 'Unknown')}: {e}")
            continue
    
    print(f"[INFO] Total opened issues collected: {len(all_issues)}")
    
    # Sort by priority, overdue status, and age
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    sorted_issues = sorted(all_issues, key=lambda x: (
        priority_order.get(x['priority'], 2),
        not x['is_overdue'],  # Overdue first
        x['age_days']  # Older first
    ))
    
    print(f"[INFO] Issues sorted and ready for display")
    return sorted_issues 