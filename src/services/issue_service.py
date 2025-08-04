"""Issue management service."""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Iterator
from datetime import datetime, date, timedelta
import logging
from collections import Counter, defaultdict

from ..api import GitLabClient
from ..models import Issue, IssueCreate, IssueTemplate, IssueType
from ..utils.validators import IssueValidator, FileValidator, ValidationError
from ..utils.logger import OperationLogger
from ..utils import ProgressTracker


logger = logging.getLogger(__name__)


class IssueService:
    """Service for managing GitLab issues."""
    
    def __init__(self, client: GitLabClient):
        """Initialize issue service.
        
        Args:
            client: GitLab API client
        """
        self.client = client
        self.templates: Dict[str, IssueTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load built-in issue templates."""
        # Feature template
        self.templates['feature'] = IssueTemplate(
            name='feature',
            title_template='[Feature] {feature_name}',
            description_template='''## Description
{description}

## Acceptance Criteria
{acceptance_criteria}

## Technical Details
{technical_details}

## Related Issues
{related_issues}
''',
            default_labels=['feature', 'needs-review'],
            default_issue_type=IssueType.FEATURE,
            required_variables=['feature_name', 'description', 'acceptance_criteria'],
            optional_variables=['technical_details', 'related_issues']
        )
        
        # Bug template
        self.templates['bug'] = IssueTemplate(
            name='bug',
            title_template='[Bug] {bug_title}',
            description_template='''## Bug Description
{description}

## Steps to Reproduce
{steps_to_reproduce}

## Expected Behavior
{expected_behavior}

## Actual Behavior
{actual_behavior}

## Environment
- **GitLab Version**: {gitlab_version}
- **Browser**: {browser}
- **OS**: {os}

## Additional Context
{additional_context}
''',
            default_labels=['bug', 'needs-triage'],
            default_issue_type=IssueType.BUG,
            required_variables=['bug_title', 'description', 'steps_to_reproduce', 'expected_behavior', 'actual_behavior'],
            optional_variables=['gitlab_version', 'browser', 'os', 'additional_context']
        )
        
        # Task template
        self.templates['task'] = IssueTemplate(
            name='task',
            title_template='{task_name}',
            description_template='''## Task Description
{description}

## Subtasks
{subtasks}

## Definition of Done
{definition_of_done}

## Notes
{notes}
''',
            default_labels=['task'],
            default_issue_type=IssueType.TASK,
            required_variables=['task_name', 'description'],
            optional_variables=['subtasks', 'definition_of_done', 'notes']
        )
    
    def load_template_from_file(self, file_path: Union[str, Path]) -> IssueTemplate:
        """Load a custom template from file.
        
        Args:
            file_path: Path to template file (YAML)
            
        Returns:
            Loaded template
        """
        path = FileValidator.validate_file_exists(file_path)
        template = IssueTemplate.from_file(str(path))
        self.templates[template.name] = template
        logger.info(f"Loaded template '{template.name}' from {path}")
        return template
    
    def create_issue(
        self,
        project_id: Union[int, str],
        issue_data: Union[IssueCreate, Dict[str, Any]],
        template_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Optional[Issue]:
        """Create a single issue.
        
        Args:
            project_id: Project ID or path
            issue_data: Issue data (IssueCreate or dict)
            template_name: Optional template to apply
            dry_run: Preview without creating
            
        Returns:
            Created issue or None if dry run
        """
        # Convert dict to IssueCreate if needed
        if isinstance(issue_data, dict):
            validated_data = IssueValidator.validate_issue_data(issue_data)
            issue_create = IssueCreate(**validated_data)
        else:
            issue_create = issue_data
        
        # Apply template if specified
        if template_name:
            if template_name not in self.templates:
                raise ValueError(f"Template '{template_name}' not found")
            template = self.templates[template_name]
            issue_create.apply_template(template)
        
        # Add timestamp if configured
        if hasattr(self, 'config') and self.config.get('issue_operations.add_timestamp', True):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if issue_create.description:
                issue_create.description += f"\n\n---\n_Created at: {timestamp}_"
            else:
                issue_create.description = f"_Created at: {timestamp}_"
        
        if dry_run:
            logger.info(f"[DRY RUN] Would create issue: {issue_create.title}")
            return None
        
        with OperationLogger(logger, "create issue", project_id=project_id):
            try:
                response = self.client.create_issue(
                    project_id,
                    **issue_create.to_gitlab_params()
                )
                issue = Issue.from_gitlab_response(response)
                logger.info(f"Created issue #{issue.iid}: {issue.title}")
                return issue
            except Exception as e:
                logger.error(f"Failed to create issue: {e}")
                raise
    
    def create_issues_bulk(
        self,
        project_id: Union[int, str],
        issues_data: List[Union[IssueCreate, Dict[str, Any]]],
        template_name: Optional[str] = None,
        dry_run: bool = False,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """Create multiple issues in bulk.
        
        Args:
            project_id: Project ID or path
            issues_data: List of issue data
            template_name: Optional template to apply to all
            dry_run: Preview without creating
            stop_on_error: Stop if any issue fails
            
        Returns:
            Summary of operation
        """
        results = {
            'total': len(issues_data),
            'created': 0,
            'failed': 0,
            'errors': [],
            'issues': []
        }
        
        progress = ProgressTracker(
            enumerate(issues_data),
            total=len(issues_data),
            description="Creating issues",
            unit="issues"
        )
        
        for i, issue_data in progress:
            try:
                issue = self.create_issue(
                    project_id,
                    issue_data,
                    template_name,
                    dry_run
                )
                if issue:
                    results['created'] += 1
                    results['issues'].append(issue)
                elif dry_run:
                    results['created'] += 1
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Issue {i+1}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                if stop_on_error:
                    break
        
        return results
    
    def import_from_csv(
        self,
        project_id: Union[int, str],
        csv_file: Union[str, Path],
        template_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Import issues from CSV file.
        
        Expected CSV columns:
        - title (required)
        - description
        - labels (comma-separated)
        - due_date (YYYY-MM-DD)
        - weight
        - assignee_usernames (comma-separated)
        - milestone_title
        
        Args:
            project_id: Project ID or path
            csv_file: Path to CSV file
            template_name: Optional template to apply
            dry_run: Preview without creating
            
        Returns:
            Import summary
        """
        path = FileValidator.validate_file_exists(csv_file)
        FileValidator.validate_file_extension(path, ['.csv'])
        
        issues_data = []
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Convert CSV row to issue data
                    issue_data = {
                        'title': row.get('title', '').strip()
                    }
                    
                    if 'description' in row:
                        issue_data['description'] = row['description'].strip()
                    
                    if 'labels' in row and row['labels']:
                        issue_data['labels'] = [
                            label.strip() 
                            for label in row['labels'].split(',')
                            if label.strip()
                        ]
                    
                    if 'due_date' in row and row['due_date']:
                        issue_data['due_date'] = row['due_date'].strip()
                    
                    if 'weight' in row and row['weight']:
                        issue_data['weight'] = int(row['weight'])
                    
                    # Handle template variables
                    if template_name:
                        template_vars = {}
                        for key, value in row.items():
                            if key.startswith('var_'):
                                var_name = key[4:]  # Remove 'var_' prefix
                                template_vars[var_name] = value
                        if template_vars:
                            issue_data['template_variables'] = template_vars
                    
                    issues_data.append(issue_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing CSV row {row_num}: {e}")
                    if not dry_run:
                        raise ValidationError(f"Invalid data in row {row_num}: {e}")
        
        logger.info(f"Parsed {len(issues_data)} issues from CSV")
        
        return self.create_issues_bulk(
            project_id,
            issues_data,
            template_name,
            dry_run
        )
    
    def import_from_json(
        self,
        project_id: Union[int, str],
        json_file: Union[str, Path],
        template_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Import issues from JSON file.
        
        Args:
            project_id: Project ID or path
            json_file: Path to JSON file
            template_name: Optional template to apply
            dry_run: Preview without creating
            
        Returns:
            Import summary
        """
        path = FileValidator.validate_file_exists(json_file)
        FileValidator.validate_file_extension(path, ['.json'])
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'issues' in data:
            issues_data = data['issues']
        elif isinstance(data, list):
            issues_data = data
        else:
            raise ValidationError(
                "Invalid JSON format. Expected list of issues or "
                "object with 'issues' key"
            )
        
        logger.info(f"Loaded {len(issues_data)} issues from JSON")
        
        return self.create_issues_bulk(
            project_id,
            issues_data,
            template_name,
            dry_run
        )
    
    def parse_text_format(self, content: str) -> List[Dict[str, Any]]:
        """Parse issues from the legacy text format.
        
        Args:
            content: Text content in legacy format
            
        Returns:
            List of parsed issue data
        """
        issues = []
        
        # Split by separator
        sections = content.split('_' * 40)
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.strip().split('\n')
            issue_data = {}
            
            # Parse title
            for line in lines:
                if '[Feature]' in line:
                    issue_data['title'] = line.split('[Feature]')[1].strip()
                    issue_data['labels'] = ['feature']
                    break
                elif '[Task]' in line:
                    issue_data['title'] = line.split('[Task]')[1].strip()
                    issue_data['labels'] = ['task']
                    break
                elif '[Bug]' in line:
                    issue_data['title'] = line.split('[Bug]')[1].strip()
                    issue_data['labels'] = ['bug']
                    break
            
            if 'title' not in issue_data:
                continue
            
            # Parse other fields
            description_parts = []
            
            for line in lines:
                if line.strip().startswith('Description:'):
                    desc = line.split('Description:', 1)[1].strip()
                    if desc:
                        description_parts.append(f"## Description\n{desc}")
                elif line.strip().startswith('Acceptance:') or line.strip().startswith('Acceptance Criteria:'):
                    acc = line.split(':', 1)[1].strip()
                    if acc:
                        description_parts.append(f"## Acceptance Criteria\n{acc}")
                elif line.strip().startswith('Labels:'):
                    labels = line.split('Labels:', 1)[1].strip()
                    if labels:
                        issue_data['labels'].extend([
                            label.strip() 
                            for label in labels.split(',')
                            if label.strip()
                        ])
            
            if description_parts:
                issue_data['description'] = '\n\n'.join(description_parts)
            
            issues.append(issue_data)
        
        return issues
    
    def get_project_milestones(
        self, 
        project_id: Union[int, str]
    ) -> List[Dict[str, Any]]:
        """Get available milestones for a project.
        
        Args:
            project_id: Project ID or path
            
        Returns:
            List of milestones
        """
        milestones = list(self.client._paginated_get(
            f'projects/{project_id}/milestones',
            state='active'
        ))
        return milestones
    
    def get_project_members(
        self, 
        project_id: Union[int, str]
    ) -> List[Dict[str, Any]]:
        """Get project members for assignee selection.
        
        Args:
            project_id: Project ID or path
            
        Returns:
            List of project members
        """
        members = list(self.client._paginated_get(
            f'projects/{project_id}/members'
        ))
        return members
    
    def analyze_project_issues(
        self, 
        project_id: Union[int, str],
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze issues for a project with AI-powered insights.
        
        Args:
            project_id: Project ID or path
            days: Number of days to analyze for trends
            
        Returns:
            Dictionary containing comprehensive issue analysis
        """
        with OperationLogger(logger, "issue analysis", project_id=project_id):
            try:
                # Get all open issues
                open_issues = list(self.client._paginated_get(
                    f"projects/{project_id}/issues",
                    params={"state": "opened"}
                ))
                
                # Get closed issues from the time period for trend analysis
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                closed_issues = list(self.client._paginated_get(
                    f"projects/{project_id}/issues",
                    params={
                        "state": "closed",
                        "updated_after": start_date.isoformat()
                    }
                ))
                
                # Analyze issue patterns
                analysis = {
                    'total_open': len(open_issues),
                    'total_closed': len(closed_issues),
                    'by_priority': self._categorize_by_labels(open_issues, ['high', 'medium', 'low', 'critical']),
                    'by_type': self._categorize_by_labels(open_issues, ['bug', 'feature', 'enhancement', 'task', 'epic']),
                    'by_assignee': self._analyze_assignee_distribution(open_issues),
                    'overdue_issues': self._get_overdue_issues(open_issues),
                    'recent_issues': self._get_recent_issues(open_issues, days=7),
                    'stale_issues': self._get_stale_issues(open_issues, days=30),
                    'resolution_metrics': self._calculate_resolution_metrics(closed_issues),
                    'trend_analysis': self._analyze_issue_trends(open_issues + closed_issues, days),
                    'workload_distribution': self._analyze_workload_distribution(open_issues),
                    'recommendations': []
                }
                
                # Generate AI-powered recommendations
                analysis['recommendations'] = self._generate_issue_recommendations(analysis)
                
                return analysis
                
            except Exception as e:
                logger.error(f"Failed to analyze issues for project {project_id}: {e}")
                return {
                    'total_open': 0,
                    'total_closed': 0,
                    'error': str(e),
                    'recommendations': []
                }
    
    def _categorize_by_labels(self, issues: List[Dict], label_keywords: List[str]) -> Dict[str, int]:
        """Categorize issues by label keywords."""
        categorized = {keyword: 0 for keyword in label_keywords}
        categorized['uncategorized'] = 0
        
        for issue in issues:
            labels = [label.lower() for label in issue.get('labels', [])]
            matched = False
            
            for keyword in label_keywords:
                if any(keyword in label for label in labels):
                    categorized[keyword] += 1
                    matched = True
                    break
            
            if not matched:
                categorized['uncategorized'] += 1
        
        return categorized
    
    def _analyze_assignee_distribution(self, issues: List[Dict]) -> Dict[str, Any]:
        """Analyze how issues are distributed among assignees."""
        assignee_counts = Counter()
        unassigned_count = 0
        
        for issue in issues:
            assignee = issue.get('assignee')
            if assignee:
                assignee_name = assignee.get('name', assignee.get('username', 'Unknown'))
                assignee_counts[assignee_name] += 1
            else:
                unassigned_count += 1
        
        total_assigned = sum(assignee_counts.values())
        
        return {
            'assigned_issues': total_assigned,
            'unassigned_issues': unassigned_count,
            'assignee_distribution': dict(assignee_counts.most_common(10)),
            'most_loaded_assignee': assignee_counts.most_common(1) if assignee_counts else None,
            'average_per_assignee': total_assigned / max(len(assignee_counts), 1)
        }
    
    def _get_overdue_issues(self, issues: List[Dict]) -> List[Dict]:
        """Get issues that are overdue based on due date."""
        overdue = []
        now = datetime.now()
        
        for issue in issues:
            due_date_str = issue.get('due_date')
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    if due_date < now:
                        overdue.append({
                            'id': issue['id'],
                            'iid': issue['iid'],
                            'title': issue['title'],
                            'due_date': due_date_str,
                            'days_overdue': (now - due_date).days,
                            'assignee': issue.get('assignee', {}).get('name', 'Unassigned'),
                            'labels': issue.get('labels', [])
                        })
                except (ValueError, TypeError):
                    continue
        
        return sorted(overdue, key=lambda x: x['days_overdue'], reverse=True)
    
    def _get_recent_issues(self, issues: List[Dict], days: int = 7) -> List[Dict]:
        """Get recently created issues."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent = []
        
        for issue in issues:
            created_at_str = issue.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at >= cutoff_date:
                        recent.append({
                            'id': issue['id'],
                            'iid': issue['iid'],
                            'title': issue['title'],
                            'created_at': created_at_str,
                            'author': issue.get('author', {}).get('name', 'Unknown'),
                            'labels': issue.get('labels', [])
                        })
                except (ValueError, TypeError):
                    continue
        
        return sorted(recent, key=lambda x: x['created_at'], reverse=True)
    
    def _get_stale_issues(self, issues: List[Dict], days: int = 30) -> List[Dict]:
        """Get issues that haven't been updated recently."""
        cutoff_date = datetime.now() - timedelta(days=days)
        stale = []
        
        for issue in issues:
            updated_at_str = issue.get('updated_at')
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                    if updated_at < cutoff_date:
                        stale.append({
                            'id': issue['id'],
                            'iid': issue['iid'],
                            'title': issue['title'],
                            'updated_at': updated_at_str,
                            'days_stale': (datetime.now() - updated_at).days,
                            'assignee': issue.get('assignee', {}).get('name', 'Unassigned'),
                            'labels': issue.get('labels', [])
                        })
                except (ValueError, TypeError):
                    continue
        
        return sorted(stale, key=lambda x: x['days_stale'], reverse=True)
    
    def _calculate_resolution_metrics(self, closed_issues: List[Dict]) -> Dict[str, Any]:
        """Calculate issue resolution metrics."""
        if not closed_issues:
            return {
                'average_resolution_time': 0,
                'resolution_rate': 0,
                'fastest_resolution': None,
                'slowest_resolution': None
            }
        
        resolution_times = []
        
        for issue in closed_issues:
            created_at_str = issue.get('created_at')
            closed_at_str = issue.get('closed_at')
            
            if created_at_str and closed_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    closed_at = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                    resolution_time = (closed_at - created_at).days
                    resolution_times.append(resolution_time)
                except (ValueError, TypeError):
                    continue
        
        if resolution_times:
            avg_resolution = sum(resolution_times) / len(resolution_times)
            fastest = min(resolution_times)
            slowest = max(resolution_times)
        else:
            avg_resolution = fastest = slowest = 0
        
        return {
            'average_resolution_time': avg_resolution,
            'resolution_count': len(closed_issues),
            'fastest_resolution': fastest,
            'slowest_resolution': slowest,
            'issues_analyzed': len(resolution_times)
        }
    
    def _analyze_issue_trends(self, all_issues: List[Dict], days: int) -> Dict[str, Any]:
        """Analyze issue creation and closure trends."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_created = defaultdict(int)
        daily_closed = defaultdict(int)
        
        for issue in all_issues:
            # Count created issues
            created_at_str = issue.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if start_date <= created_at <= end_date:
                        date_key = created_at.date().isoformat()
                        daily_created[date_key] += 1
                except (ValueError, TypeError):
                    continue
            
            # Count closed issues
            closed_at_str = issue.get('closed_at')
            if closed_at_str and issue.get('state') == 'closed':
                try:
                    closed_at = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                    if start_date <= closed_at <= end_date:
                        date_key = closed_at.date().isoformat()
                        daily_closed[date_key] += 1
                except (ValueError, TypeError):
                    continue
        
        return {
            'daily_created': dict(daily_created),
            'daily_closed': dict(daily_closed),
            'total_created_in_period': sum(daily_created.values()),
            'total_closed_in_period': sum(daily_closed.values()),
            'net_change': sum(daily_created.values()) - sum(daily_closed.values())
        }
    
    def _analyze_workload_distribution(self, issues: List[Dict]) -> Dict[str, Any]:
        """Analyze workload distribution and bottlenecks."""
        assignee_workload = defaultdict(lambda: {'count': 0, 'priority_breakdown': defaultdict(int)})
        
        for issue in issues:
            assignee = issue.get('assignee')
            assignee_name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
            
            assignee_workload[assignee_name]['count'] += 1
            
            # Analyze priority breakdown
            labels = [label.lower() for label in issue.get('labels', [])]
            priority = 'normal'
            if any('critical' in label for label in labels):
                priority = 'critical'
            elif any('high' in label for label in labels):
                priority = 'high'
            elif any('low' in label for label in labels):
                priority = 'low'
            
            assignee_workload[assignee_name]['priority_breakdown'][priority] += 1
        
        # Find bottlenecks (assignees with too many issues)
        avg_workload = sum(data['count'] for data in assignee_workload.values()) / max(len(assignee_workload), 1)
        bottlenecks = [
            assignee for assignee, data in assignee_workload.items() 
            if data['count'] > avg_workload * 1.5 and assignee != 'Unassigned'
        ]
        
        return {
            'workload_by_assignee': dict(assignee_workload),
            'average_workload': avg_workload,
            'bottlenecks': bottlenecks,
            'unassigned_count': assignee_workload.get('Unassigned', {}).get('count', 0)
        }
    
    def _generate_issue_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate AI-powered recommendations based on issue analysis."""
        recommendations = []
        
        # High priority issue alert
        high_priority_count = analysis['by_priority'].get('high', 0) + analysis['by_priority'].get('critical', 0)
        if high_priority_count > 5:
            recommendations.append({
                'type': 'alert',
                'priority': 'high',
                'title': 'High Priority Issue Backlog',
                'message': f'{high_priority_count} high/critical priority issues require immediate attention',
                'action': 'Consider resource reallocation or emergency sprint planning',
                'impact': 'High'
            })
        
        # Bug vs feature ratio analysis
        total_open = analysis['total_open']
        bug_count = analysis['by_type'].get('bug', 0)
        if total_open > 0 and (bug_count / total_open) > 0.6:
            recommendations.append({
                'type': 'warning',
                'priority': 'medium',
                'title': 'High Bug-to-Feature Ratio',
                'message': f'{bug_count} bugs out of {total_open} total issues ({(bug_count/total_open)*100:.1f}%)',
                'action': 'Implement code review improvements and enhanced testing strategies',
                'impact': 'Medium'
            })
        
        # Workload distribution issues
        bottlenecks = analysis['workload_distribution']['bottlenecks']
        unassigned_count = analysis['workload_distribution']['unassigned_count']
        
        if bottlenecks:
            recommendations.append({
                'type': 'optimization',
                'priority': 'medium',
                'title': 'Workload Imbalance Detected',
                'message': f'Team members overloaded: {", ".join(bottlenecks[:3])}',
                'action': 'Redistribute workload and consider additional resources',
                'impact': 'Medium'
            })
        
        if unassigned_count > 10:
            recommendations.append({
                'type': 'process',
                'priority': 'low',
                'title': 'High Number of Unassigned Issues',
                'message': f'{unassigned_count} issues are unassigned',
                'action': 'Implement issue triage process and assign ownership',
                'impact': 'Low'
            })
        
        # Stale issues warning
        stale_count = len(analysis['stale_issues'])
        if stale_count > 15:
            recommendations.append({
                'type': 'maintenance',
                'priority': 'low',
                'title': 'Stale Issues Cleanup Needed',
                'message': f'{stale_count} issues haven\'t been updated in 30+ days',
                'action': 'Review and close outdated issues or update their status',
                'impact': 'Low'
            })
        
        # Overdue issues critical alert
        overdue_count = len(analysis['overdue_issues'])
        if overdue_count > 0:
            recommendations.append({
                'type': 'critical',
                'priority': 'critical',
                'title': 'Overdue Issues Require Attention',
                'message': f'{overdue_count} issues are past their due date',
                'action': 'Immediate review and resolution or due date adjustment needed',
                'impact': 'High'
            })
        
        # Positive trend recognition
        trend = analysis['trend_analysis']
        if trend['net_change'] < 0:  # More issues closed than opened
            recommendations.append({
                'type': 'success',
                'priority': 'info',
                'title': 'Positive Issue Resolution Trend',
                'message': f'Net reduction of {abs(trend["net_change"])} issues in the analysis period',
                'action': 'Maintain current resolution pace and processes',
                'impact': 'Positive'
            })
        
        return sorted(recommendations, key=lambda x: {
            'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4
        }.get(x['priority'], 5))