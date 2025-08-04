#!/usr/bin/env python3
"""Generate executive dashboard with shadcn/ui-inspired design for GitLab analytics."""

import sys
import os
import argparse
import json
import html
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import math
import re
import requests

# Load environment variables from .env file FIRST
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Simple fallback for loading .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Handle GITLAB_API_TOKEN vs GITLAB_TOKEN
if 'GITLAB_API_TOKEN' in os.environ and 'GITLAB_TOKEN' not in os.environ:
    os.environ['GITLAB_TOKEN'] = os.environ['GITLAB_API_TOKEN']

# Now load environment variables
GITLAB_URL = os.getenv('GITLAB_URL')
GITLAB_TOKEN = os.getenv('GITLAB_TOKEN')

def get_all_group_ids():
    headers = {"Authorization": f"Bearer {GITLAB_TOKEN}"}
    group_ids = []
    page = 1
    while True:
        resp = requests.get(
            f"{GITLAB_URL}/api/v4/groups",
            headers=headers,
            params={"per_page": 100, "page": page}
        )
        resp.raise_for_status()
        groups = resp.json()
        if not groups:
            break
        group_ids.extend([g['id'] for g in groups])
        page += 1
    return group_ids

# Safe print function for Windows compatibility
def safe_print(text):
    """Print text with fallback for encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic characters with ASCII alternatives
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text)
    except Exception:
        # Ultimate fallback
        print(str(text).encode('ascii', errors='replace').decode('ascii'))

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our services
from src.api.client import GitLabClient
from src.services.group_enhancement import GroupEnhancementService
from src.services.branch_service import BranchService
from src.services.issue_service import IssueService
from src.services.board_service import BoardService

def get_env_or_exit(key: str, description: str) -> str:
    """Get environment variable or exit with helpful message."""
    value = os.getenv(key)
    if not value:
        safe_print(f"[ERROR] Missing required environment variable: {key}")
        safe_print(f"   {description}")
        sys.exit(1)
    return value

def build_contributor_mapping() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build contributor mapping for name normalization."""
    mapping = {}
    email_mapping = {}
    
    # Add common known mappings for this specific case
    known_mappings = {
        'ta.khongsap@gmail.com': 'Totrakool Khongsap',
        'tkhongsap': 'Totrakool Khongsap',
        'i1032745@THAIBEV.COM': 'Totrakool Khongsap',
        'totrakool.k@thaibev.com': 'Totrakool Khongsap'
    }
    
    for key, canonical in known_mappings.items():
        if '@' in key:
            email_mapping[key.lower()] = canonical
        else:
            mapping[key.lower()] = canonical
    
    return mapping, email_mapping

def normalize_contributor_name(name: str, email: str = '', name_mapping: Optional[Dict[str, str]] = None, email_mapping: Optional[Dict[str, str]] = None) -> str:
    """Normalize contributor name using mapping and email."""
    if name_mapping is None or email_mapping is None:
        name_mapping, email_mapping = build_contributor_mapping()
    
    # First check email-based mapping (most reliable)
    if email:
        email_lower = email.lower()
        if email_lower in email_mapping:
            return email_mapping[email_lower]
    
    # Check explicit name mapping
    if name in name_mapping:
        return name_mapping[name]
    
    # Check case-insensitive name mapping
    name_lower = name.lower()
    if name_lower in name_mapping:
        return name_mapping[name_lower]
    
    # Try to match by email domain patterns
    if email:
        # Extract username from email
        email_username = email.split('@')[0]
        if email_username in name_mapping:
            return name_mapping[email_username]
        
        # Simple heuristics for common patterns
        email_lower = email.lower()
        name_lower = name.lower()
        
        # If email starts with name, they're likely the same person
        if email_lower.startswith(name_lower.replace(' ', '.')):
            return name
        if email_lower.startswith(name_lower.replace(' ', '')):
            return name
    
    return name

def simple_gitlab_request(url: str, token: str, endpoint: str, params: Optional[Dict] = None) -> Any:
    """Make a simple GitLab API request with pagination support."""
    import requests
    
    headers = {"Authorization": f"Bearer {token}"}
    full_url = f"{url}/api/v4/{endpoint}"
    
    all_results = []
    page = 1
    per_page = 100
    
    try:
        while True:
            request_params = params or {}
            request_params.update({'page': page, 'per_page': per_page})
            
            response = requests.get(full_url, headers=headers, params=request_params)
            response.raise_for_status()
            
            results = response.json()
            if not results:
                break
                
            all_results.extend(results)
            
            # Check if there are more pages
            if len(results) < per_page:
                break
            page += 1
            
        return all_results
    except requests.exceptions.RequestException as e:
        safe_print(f"[ERROR] GitLab API Error: {e}")
        return []

def calculate_health_score(metrics: Dict[str, Any]) -> Tuple[int, str]:
    """Calculate project health score and grade."""
    score = 100
    
    # Activity scoring
    if metrics['commits_30d'] == 0:
        score -= 30
    elif metrics['commits_30d'] < 5:
        score -= 15
    elif metrics['commits_30d'] > 50:
        score += 5
    
    # Issue management
    if metrics['open_issues'] > 20:
        score -= 20
    elif metrics['open_issues'] > 10:
        score -= 10
    elif metrics['open_issues'] < 5:
        score += 5
    
    # MR efficiency
    if metrics['open_mrs'] > 10:
        score -= 15
    elif metrics['open_mrs'] > 5:
        score -= 5
    
    # Collaboration
    if metrics['contributors_30d'] == 1:
        score -= 10
    elif metrics['contributors_30d'] > 3:
        score += 10
    
    # Recent activity bonus
    if metrics['days_since_last_commit'] < 3:
        score += 5
    elif metrics['days_since_last_commit'] > 14:
        score -= 20
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    # Assign grade
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

def get_activity_sparkline(daily_commits: List[int]) -> str:
    """Generate sparkline visualization for activity."""
    if not daily_commits:
        return ""
    
    # Normalize to 0-7 range for sparkline characters
    max_val = max(daily_commits) if max(daily_commits) > 0 else 1
    normalized = [int(val / max_val * 7) for val in daily_commits]
    
    # Sparkline characters
    sparks = "▁▂▃▄▅▆▇█"
    
    return ''.join(sparks[n] for n in normalized)


def _determine_priority(labels: List[str]) -> str:
    """Determine issue priority from labels."""
    labels_lower = [label.lower() for label in labels]
    if any('critical' in label or 'urgent' in label for label in labels_lower):
        return 'critical'
    elif any('high' in label for label in labels_lower):
        return 'high'
    elif any('medium' in label for label in labels_lower):
        return 'medium'
    elif any('low' in label for label in labels_lower):
        return 'low'
    return 'medium'  # Default priority

def _determine_type(labels: List[str]) -> str:
    """Determine issue type from labels."""
    labels_lower = [label.lower() for label in labels]
    if any('bug' in label for label in labels_lower):
        return 'bug'
    elif any('feature' in label for label in labels_lower):
        return 'feature'
    elif any('enhancement' in label for label in labels_lower):
        return 'enhancement'
    return 'other'

def _calculate_age(created_at: str) -> int:
    """Calculate age of issue in days."""
    from datetime import timezone
    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc) - created_date).days
    return age

def _is_overdue(due_date: Optional[str]) -> bool:
    """Check if issue is overdue."""
    if not due_date:
        return False
    from datetime import timezone
    try:
        # Handle both ISO format with timezone and date-only format
        if 'T' in due_date:
            due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        else:
            # Date only format (YYYY-MM-DD) - assume end of day UTC
            due = datetime.fromisoformat(due_date + 'T23:59:59+00:00')
        return due < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False

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
    
    # Create GitLab client and board service
    try:
        client = GitLabClient(gitlab_url, gitlab_token)
        board_service = BoardService(client)
        analytics['board_labels_used'] = True
    except Exception as e:
        safe_print(f"Warning: Could not initialize board service, using basic state detection: {e}")
        board_service = None
    
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
            analytics['total_open'] += 1
            project_issue_count += 1
            
            # Categorize by labels
            labels = issue.get('labels', [])
            priority = _determine_priority(labels)
            issue_type = _determine_type(labels)
            
            analytics['by_priority'][priority] += 1
            analytics['by_type'][issue_type] += 1
            
            # Determine workflow state
            if board_service:
                # Try to get board for this project (cached)
                if not hasattr(board_service, '_project_boards'):
                    board_service._project_boards = {}
                
                if project_id not in board_service._project_boards:
                    board = board_service.get_default_board(project_id)
                    if board:
                        board_labels = board_service.get_board_workflow_labels(project_id, board['id'])
                        board_service._project_boards[project_id] = board_labels
                    else:
                        board_service._project_boards[project_id] = None
                
                board_labels = board_service._project_boards[project_id]
                workflow_state = board_service.get_issue_workflow_state(issue, board_labels)
            else:
                # Fallback: use assignee to determine state
                workflow_state = 'in_progress' if issue.get('assignee') else 'to_do'
                # Check for blocked label
                if any('blocked' in label.lower() for label in labels):
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
            if assignee:
                assignee_name = assignee.get('name', 'Unknown')
                analytics['assignee_workload'][assignee_name] = \
                    analytics['assignee_workload'].get(assignee_name, 0) + 1
            else:
                analytics['unassigned'] += 1
            
            # Collect enriched issue data
            enriched_issue = {
                'id': issue['id'],
                'iid': issue['iid'],
                'title': issue['title'],
                'project_id': project_id,
                'project_name': project_name,
                'priority': priority,
                'type': issue_type,
                'labels': labels,
                'assignee': assignee,
                'state': issue['state'],
                'workflow_state': workflow_state,
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

def get_initials(name: str) -> str:
    """Get initials from a name."""
    if not name:
        return "?"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[:2].upper()

def generate_ai_recommendations(issue_analytics: Dict, project_metrics: List[Dict]) -> List[Dict]:
    """Generate strategic recommendations based on issue patterns."""
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
            'projects': critical_projects[:5]  # Show top 5 projects
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

def analyze_team_performance(projects: List[Dict], gitlab_url: str, gitlab_token: str, days: int = 30) -> Dict[str, Any]:
    """Analyze detailed team member contributions and workload with accurate date filtering."""
    from datetime import timezone
    team_analytics = {}
    
    # Calculate date range (aligned with weekly reports logic)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Build contributor mapping for normalization
    name_mapping, email_mapping = build_contributor_mapping()
    
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', 'Unknown')
        
        try:
            # Get commits with consistent API parameters (since and until)
            all_commits = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/repository/commits",
                {
                    "since": start_date.isoformat(),
                    "until": end_date.isoformat()
                }
            )
            
            # Client-side date filtering for accuracy (aligned with weekly reports)
            commits = []
            for commit in all_commits:
                try:
                    commit_date = datetime.fromisoformat(
                        commit['created_at'].replace('Z', '+00:00')
                    )
                    if start_date <= commit_date <= end_date:
                        commits.append(commit)
                except (ValueError, KeyError) as e:
                    safe_print(f"[WARNING] Failed to parse commit date: {e}")
                    continue
            
            for commit in commits:
                author_name = commit.get('author_name', 'Unknown')
                author_email = commit.get('author_email', '')
                
                # Normalize contributor name (aligned with weekly reports)
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
                    safe_print(f"[WARNING] Failed to parse MR date: {e}")
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
                    safe_print(f"[WARNING] Failed to parse issue date: {e}")
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
            safe_print(f"[WARNING] Failed to analyze project {project_name}: {e}")
            continue
    
    # Convert sets to lists for JSON serialization
    for member in team_analytics:
        team_analytics[member]['projects'] = sorted(list(team_analytics[member]['projects']))
        # Keep only recent 10 activities
        team_analytics[member]['recent_activity'] = \
            sorted(team_analytics[member]['recent_activity'], 
                   key=lambda x: x['date'], reverse=True)[:10]
    
    return team_analytics

def analyze_project(project: Dict, gitlab_url: str, gitlab_token: str, days: int = 30) -> Dict[str, Any]:
    """Analyze a single project with 30-day metrics including branch and issue analysis (all branches, code change per contributor)."""
    project_id = project['id']
    project_name = project['name']
    
    from datetime import timezone
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
        'code_changes': {},  # NEW: code change summary per contributor
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
        # New enhanced metrics
        'branch_analysis': {},
        'issue_analysis': {},
        'enhancement_metadata': {
            'has_branch_analysis': False,
            'has_issue_analysis': False,
            'analysis_errors': []
        }
    }
    
    # Initialize enhanced services
    try:
        client = GitLabClient(gitlab_url, gitlab_token)
        branch_service = BranchService(client)
        issue_service = IssueService(client)
        enhanced_services_available = True
    except Exception as e:
        safe_print(f"[WARNING] Enhanced services not available for {project_name}: {e}")
        enhanced_services_available = False
        branch_service = None
        issue_service = None
    
    # Build contributor mapping
    name_mapping, email_mapping = build_contributor_mapping()
    
    # --- ดึง commit จากทุก branch ---
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
    
    # Client-side date filtering for accuracy (aligned with weekly reports)
    commits = []
    for commit in all_commits:
        try:
            commit_date = datetime.fromisoformat(
                commit['created_at'].replace('Z', '+00:00')
            )
            if start_date <= commit_date <= end_date:
                commits.append(commit)
        except (ValueError, KeyError) as e:
            safe_print(f"[WARNING] Failed to parse commit date in project {project_name}: {e}")
            continue
    
    if commits:
        metrics['commits_30d'] = len(commits)
        # NEW: prepare code change summary
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
            # --- get code change stats ---
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
                safe_print(f"[WARNING] Failed to get commit stats for {sha}: {e}")
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
    
    # Get merge requests with consistent API parameters (aligned with weekly reports)
    all_mrs = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/merge_requests",
        {
            "created_after": start_date.isoformat(),
            "created_before": end_date.isoformat(),
            "scope": "all"
        }
    )
    
    # Get all MRs to count open ones (need separate call for current state)
    all_current_mrs = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/merge_requests",
        {"state": "opened"}
    )
    metrics['open_mrs'] = len(all_current_mrs) if all_current_mrs else 0
    
    # Process MRs with client-side date filtering for accuracy
    for mr in all_mrs:
        try:
            created_at = datetime.fromisoformat(mr['created_at'].replace('Z', '+00:00'))
            
            # Client-side date filtering (aligned with weekly reports)
            if start_date <= created_at <= end_date:
                metrics['mrs_created'] += 1
                if mr['state'] == 'merged':
                    metrics['mrs_merged'] += 1
                elif mr['state'] == 'closed':
                    metrics['mrs_closed'] += 1
        except (ValueError, KeyError) as e:
            safe_print(f"[WARNING] Failed to parse MR date in project {project_name}: {e}")
            continue
    
    # Get issues with consistent API parameters (aligned with weekly reports)
    all_issues = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/issues",
        {
            "created_after": start_date.isoformat(),
            "created_before": end_date.isoformat(),
            "scope": "all"
        }
    )
    
    # Get all current open issues (need separate call for current state)
    all_current_issues = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/issues",
        {"state": "opened"}
    )
    metrics['open_issues'] = len(all_current_issues) if all_current_issues else 0
    
    # Process issues with client-side date filtering for accuracy
    for issue in all_issues:
        try:
            created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            
            # Client-side date filtering (aligned with weekly reports)
            if start_date <= created_at <= end_date:
                metrics['issues_created'] += 1
                if issue['state'] == 'closed':
                    metrics['issues_closed'] += 1
        except (ValueError, KeyError) as e:
            safe_print(f"[WARNING] Failed to parse issue date in project {project_name}: {e}")
            continue
    
    # Enhanced Branch Analysis
    if enhanced_services_available and branch_service:
        try:
            safe_print(f"    [INFO] Analyzing branches for {project_name}...")
            branch_analysis = branch_service.analyze_project_branches(project_id, days)
            metrics['branch_analysis'] = branch_analysis
            metrics['enhancement_metadata']['has_branch_analysis'] = True
        except Exception as e:
            safe_print(f"    [WARNING] Branch analysis failed for {project_name}: {e}")
            metrics['enhancement_metadata']['analysis_errors'].append(f"Branch analysis: {str(e)}")
            metrics['branch_analysis'] = {'error': str(e), 'active_branches': [], 'total_branches': 0}
    
    # Enhanced Issue Analysis
    if enhanced_services_available and issue_service:
        try:
            safe_print(f"    [INFO] Analyzing issues for {project_name}...")
            issue_analysis = issue_service.analyze_project_issues(project_id, days)
            metrics['issue_analysis'] = issue_analysis
            metrics['enhancement_metadata']['has_issue_analysis'] = True
        except Exception as e:
            safe_print(f"    [WARNING] Issue analysis failed for {project_name}: {e}")
            metrics['enhancement_metadata']['analysis_errors'].append(f"Issue analysis: {str(e)}")
            metrics['issue_analysis'] = {'error': str(e), 'recommendations': [], 'total_open': metrics['open_issues']}
    
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
        safe_print(f"    [INFO] Analyzing {project_name} for {days} days...")
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
    
    # Calculate trends for each metric
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
        
        safe_print(f"[INFO] Analyzing {project_name} across all periods...")
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

def analyze_groups(group_ids: List[int], gitlab_url: str, gitlab_token: str, days: int = 30) -> Dict[str, Any]:
    """Analyze multiple GitLab groups with project-based grouping instead of group-based."""
    safe_print(f"[INFO] Analyzing {len(group_ids)} groups over {days} days...")
    
    # Initialize GitLab client and group enhancement service
    try:
        client = GitLabClient(gitlab_url, gitlab_token)
        group_service = GroupEnhancementService(client)
    except Exception as e:
        safe_print(f"[WARNING] Could not initialize enhanced services, falling back to simple requests: {e}")
        client = None
        group_service = None
    
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
        'groups': {},  # This will now contain project-based groups
        'projects': [],
        'contributors': Counter(),
        'daily_activity': defaultdict(int),
        'technology_stack': Counter()
    }
    
    # Track unique projects by ID to avoid duplicates
    unique_projects = {}  # project_id -> project_data
    project_groups = {}   # project_id -> list of group_ids

    # Collect all projects from all groups first
    all_projects = []
    
    for group_id in group_ids:
        safe_print(f"  [INFO] Analyzing group {group_id}...")
        
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
                safe_print(f"      [INFO] Project {project_name} already found, adding to existing...")
                # Add group info to existing project
                if project_id not in project_groups:
                    project_groups[project_id] = []
                project_groups[project_id].append(group_id)
                continue
            
            safe_print(f"    [INFO] Found project: {project_name} (ID: {project_id})")
            
            # Analyze project
            project_metrics = analyze_project(project, gitlab_url, gitlab_token, days)
            
            # Store unique project
            unique_projects[project_id] = project_metrics
            project_groups[project_id] = [group_id]
            all_projects.append(project_metrics)
    
    # Now create project-based groups instead of group-based groups
    safe_print(f"\n[INFO] Creating project-based groups from {len(all_projects)} projects...")
    
    for project_metrics in all_projects:
        project_id = project_metrics['id']
        project_name = project_metrics['name']
        
        # Create a group entry for each project
        project_group_data = {
            'name': project_name,  # Use project name instead of group name
            'id': project_id,      # Use project ID instead of group ID
            'description': project_metrics.get('description', ''),
            'metadata': {
                'project_path': project_metrics.get('path', ''),
                'visibility': project_metrics.get('visibility', 'private'),
                'default_branch': project_metrics.get('default_branch', 'main')
            },
            'projects': [project_metrics],  # Single project in this "group"
            'total_commits': project_metrics['commits_30d'],
            'total_mrs': project_metrics['mrs_created'],
            'total_issues': project_metrics['issues_created'],
            'health_grade': project_metrics['health_grade'],
            'active_projects': 1 if project_metrics['status'] == 'active' else 0,
            'enhancement_info': {
                'has_business_name': False,
                'has_business_description': False
            }
        }
        
        # Use project ID as the group key
        report_data['groups'][project_id] = project_group_data
    
    # Now process unique projects for global statistics
    safe_print(f"\n[INFO] Processing {len(unique_projects)} unique projects...")
    
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
    
    # Convert sets to counts
    report_data['summary']['unique_contributors'] = len(report_data['summary']['unique_contributors'])
    report_data['summary']['total_projects'] = len(unique_projects)
    
    # Sort projects by health score
    report_data['projects'].sort(key=lambda x: x['health_score'], reverse=True)
    
    # Collect comprehensive issue analytics
    safe_print("\n[INFO] Collecting issue analytics across all projects...")
    report_data['issue_analytics'] = collect_issue_analytics(report_data['projects'], gitlab_url, gitlab_token)
    
    # Generate AI recommendations
    safe_print("[INFO] Generating AI recommendations...")
    report_data['ai_recommendations'] = generate_ai_recommendations(
        report_data['issue_analytics'], 
        report_data['projects']
    )
    
    # Analyze team performance
    safe_print("[INFO] Analyzing team performance...")
    report_data['team_analytics'] = analyze_team_performance(report_data['projects'], gitlab_url, gitlab_token, days)
    
    # Collect all issues for Issues Management section
    safe_print("[INFO] Collecting all open issues...")
    report_data['all_issues'] = collect_all_issues(report_data['projects'], gitlab_url, gitlab_token)

    if len(all_projects) > 1:
        safe_print("[INFO] Performing cross-period comparison...")
        report_data['cross_period_comparison'] = compare_projects_across_periods(
            all_projects, gitlab_url, gitlab_token
        )
    
    return report_data

def collect_all_issues(projects: List[Dict], gitlab_url: str, gitlab_token: str) -> List[Dict]:
    """Collect opened and in-progress issues across projects with full details."""
    all_issues = []
    assignee_workload = defaultdict(lambda: {
        'total_issues': 0,
        'overdue_issues': 0,
        'critical_issues': 0,
        'high_priority_issues': 0
    })
    
    safe_print(f"[INFO] Starting to collect opened and in-progress issues from {len(projects)} projects...")
    
    for project in projects:
        try:
            safe_print(f"    [INFO] Collecting issues for project: {project.get('name', 'Unknown')} (ID: {project.get('id', 'Unknown')})")
            
            # Get opened issues
            opened_issues = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project['id']}/issues",
                {
                    "state": "opened",  # Only opened issues
                    "per_page": 100,  # Maximum per page
                    "order_by": "created_at",
                    "sort": "desc"  # Most recent first
                }
            )
            
            safe_print(f"      [INFO] Found {len(opened_issues)} opened issues in {project.get('name', 'Unknown')}")
            
            # Debug: Show issue labels
            label_counts = {}
            for issue in opened_issues:
                labels = issue.get('labels', [])
                for label in labels:
                    label_counts[label] = label_counts.get(label, 0) + 1
            
            safe_print(f"      [DEBUG] Issue labels: {label_counts}")
            
            for issue in opened_issues:
                # Enhanced priority detection from labels
                labels = issue.get('labels', [])
                priority = 'medium'  # default
                
                # Check for various priority label formats
                priority_labels = [label.lower() for label in labels]
                if any('critical' in label or 'urgent' in label or 'p0' in label for label in priority_labels):
                    priority = 'critical'
                elif any('high' in label or 'p1' in label for label in priority_labels):
                    priority = 'high'
                elif any('low' in label or 'p3' in label for label in priority_labels):
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
                        # Handle both ISO format and date-only format
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
            safe_print(f"[WARNING] Failed to collect issues for project {project.get('name', 'Unknown')}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    safe_print(f"[INFO] Total opened issues collected: {len(all_issues)}")
    
    # Debug: Show final breakdown
    final_priority_counts = {}
    final_label_counts = {}
    for issue in all_issues:
        priority = issue.get('priority', 'unknown')
        final_priority_counts[priority] = final_priority_counts.get(priority, 0) + 1
        
        labels = issue.get('labels', [])
        for label in labels:
            final_label_counts[label] = final_label_counts.get(label, 0) + 1
    
    safe_print(f"[DEBUG] Final issue priorities: {final_priority_counts}")
    safe_print(f"[DEBUG] Final issue labels: {final_label_counts}")
    
    # Sort by priority, overdue status, and age
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    sorted_issues = sorted(all_issues, key=lambda x: (
        priority_order.get(x['priority'], 2),
        not x['is_overdue'],  # Overdue first
        x['age_days']  # Older first
    ))
    
    safe_print(f"[INFO] Issues sorted and ready for display")
    return sorted_issues


def calculate_aggregate_issues(projects: List[Dict]) -> Dict[str, Any]:
    """Calculate aggregate issue analysis across all projects."""
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
        'recommendations': total_recommendations[:10],  # Top 10 recommendations
        'all_recommendations': total_recommendations,
        'issue_types': dict(issue_types),
        'issue_priorities': dict(issue_priorities)
    }

def validate_and_clean_data(data: Any, data_type: str) -> Any:
    """Validate and clean data from GitLab API responses."""
    if data_type == 'commit':
        required_fields = ['id', 'title', 'created_at', 'author_name']
        if not all(field in data for field in required_fields):
            return None
        
        # Clean author name
        if data.get('author_name'):
            data['author_name'] = data['author_name'].strip()
        
        # Validate date
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
            
    elif data_type == 'merge_request':
        required_fields = ['id', 'title', 'created_at', 'author']
        if not all(field in data for field in required_fields):
            return None
        
        # Validate author structure
        if not isinstance(data.get('author'), dict):
            return None
        
        # Clean author name
        if data['author'].get('name'):
            data['author']['name'] = data['author']['name'].strip()
        
        # Validate date
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
            
    elif data_type == 'issue':
        required_fields = ['id', 'title', 'created_at', 'state']
        if not all(field in data for field in required_fields):
            return None
        
        # Clean assignee if present
        if data.get('assignee') and isinstance(data['assignee'], dict):
            if data['assignee'].get('name'):
                data['assignee']['name'] = data['assignee']['name'].strip()
        
        # Validate date
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    
    return data

def safe_gitlab_request(url: str, token: str, endpoint: str, params: Optional[Dict] = None, data_type: str = 'generic') -> List[Any]:
    """Make a safe GitLab API request with data validation and error handling."""
    try:
        raw_data = simple_gitlab_request(url, token, endpoint, params)
        
        if not isinstance(raw_data, list):
            safe_print(f"[WARNING] Expected list from {endpoint}, got {type(raw_data)}")
            return []
        
        # Validate and clean each item
        cleaned_data = []
        for item in raw_data:
            if isinstance(item, dict):
                cleaned_item = validate_and_clean_data(item, data_type)
                if cleaned_item:
                    cleaned_data.append(cleaned_item)
        
        safe_print(f"[INFO] Retrieved {len(cleaned_data)} valid {data_type} items from {endpoint}")
        return cleaned_data
        
    except Exception as e:
        safe_print(f"[ERROR] Failed to fetch {data_type} from {endpoint}: {e}")
        return []

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate executive dashboard for GitLab analytics",
        epilog="""
Examples:
  # Generate dashboard for specific groups
  python scripts/generate_executive_dashboard.py --groups 1721,1267,1269 --output dashboard.html

  # Generate 60-day analysis
  python scripts/generate_executive_dashboard.py --groups 1721,1267,1269 --days 60 --output dashboard.html

  # Custom team name
  python scripts/generate_executive_dashboard.py --groups 1721,1267,1269 --team-name "AI Development Team"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--groups', '-g',
        help='Comma-separated list of GitLab group IDs to analyze (default: all GitLab groups)'
    )
    parser.add_argument(
        '--all-gitlab-groups',
        action='store_true',
        help='Analyze all groups in GitLab (overrides --groups)'
    )
    parser.add_argument(
        '--output', '-o',
        default='executive_dashboard.html',
        help='Output file path (default: executive_dashboard.html)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    parser.add_argument(
        '--team-name',
        default='Development Team',
        help='Name of the team for the report'
    )
    
    args = parser.parse_args()

    # Get GitLab configuration
    gitlab_url = get_env_or_exit('GITLAB_URL', 'Your GitLab instance URL')
    gitlab_token = get_env_or_exit('GITLAB_TOKEN', 'Your GitLab API token')

    # Parse group IDs
    if args.all_gitlab_groups:
        safe_print("[INFO] Fetching all group IDs from GitLab...")
        group_ids = get_all_group_ids()
        if not group_ids:
            safe_print("[ERROR] No groups found in GitLab.")
            return 1
        safe_print(f"[INFO] Analyzing ALL {len(group_ids)} groups from GitLab.")
    elif args.groups:
        try:
            group_ids = [int(gid.strip()) for gid in args.groups.split(',')]
        except ValueError:
            safe_print("[ERROR] Invalid group IDs. Please provide comma-separated integers.")
            return 1
    else:
        safe_print("[INFO] No groups specified, fetching all group IDs from GitLab...")
        group_ids = get_all_group_ids()
        if not group_ids:
            safe_print("[ERROR] No groups found in GitLab.")
            return 1
        safe_print(f"[INFO] Using all {len(group_ids)} groups from GitLab.")
    
    if not group_ids:
        safe_print("[ERROR] No group IDs to analyze.")
        return 1
    
    try:
        safe_print(">> Starting executive dashboard generation...")
        safe_print(f"   Analyzing {len(group_ids)} groups over {args.days} days")
        
        # Analyze groups
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, args.days)
        
        # เพิ่มการเปรียบเทียบตามช่วงเวลา
        if len(report_data['projects']) > 1:
            safe_print("[INFO] Performing multi-period analysis...")
            report_data['multi_period_analysis'] = compare_projects_across_periods(
                report_data['projects'], gitlab_url, gitlab_token
            )
        
        # Save to file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # เพิ่มการบันทึกข้อมูล JSON สำหรับการวิเคราะห์เพิ่มเติม
        json_output_path = output_path.with_suffix('.json')
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        safe_print(f"[SUCCESS] Dashboard saved to: {output_path}")
        safe_print(f"[SUCCESS] JSON data saved to: {json_output_path}")
        
        # Print summary
        summary = report_data['summary']
        safe_print(f"\n[SUMMARY] Analysis Summary:")
        safe_print(f"   Total Projects: {summary['total_projects']}")
        safe_print(f"   Active Projects: {summary['active_projects']}")
        safe_print(f"   Total Commits: {summary['total_commits']}")
        safe_print(f"   Unique Contributors: {summary['unique_contributors']}")
        safe_print(f"   Health Distribution: A+({summary['health_distribution']['A+']}) A({summary['health_distribution']['A']}) B({summary['health_distribution']['B']}) C({summary['health_distribution']['C']}) D({summary['health_distribution']['D']})")
        
        # เพิ่มการแสดงผลการเปรียบเทียบตามช่วงเวลา
        if 'multi_period_analysis' in report_data:
            safe_print(f"\n[MULTI-PERIOD] Multi-period analysis completed")
            safe_print(f"   Periods analyzed: 7, 15, 30, 60, 90 days")
            safe_print(f"   Projects compared: {len(report_data['projects'])}")
        
        return 0
        
    except KeyboardInterrupt:
        safe_print(f"\n[CANCELLED] Operation cancelled by user")
        return 1
    except Exception as e:
        safe_print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())