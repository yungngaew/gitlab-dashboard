"""Analytics service for GitLab repository metrics."""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from collections import defaultdict
import json

from ..api import GitLabClient
from ..utils.logger import OperationLogger

logger = logging.getLogger(__name__)


class GitLabAnalytics:
    """Service for analyzing GitLab repository metrics."""
    
    def __init__(self, client: GitLabClient):
        """Initialize analytics service.
        
        Args:
            client: GitLab API client
        """
        self.client = client
    
    def get_project_metrics(self, project_id: Union[int, str]) -> Dict[str, Any]:
        """Get comprehensive metrics for a single project.
        
        Args:
            project_id: Project ID or path
            
        Returns:
            Dictionary containing project metrics
        """
        with OperationLogger(logger, "project analytics", project_id=project_id):
            project = self.client.get_project(project_id)
            
            metrics = {
                'project': {
                    'id': project['id'],
                    'name': project['name'],
                    'path': project['path_with_namespace'],
                    'created_at': project['created_at'],
                    'last_activity_at': project['last_activity_at'],
                    'default_branch': project['default_branch'],
                    'visibility': project['visibility'],
                    'archived': project.get('archived', False)
                },
                'commits': self._get_commit_statistics(project_id),
                'branches': self._get_branch_statistics(project_id),
                'issues': self._get_issue_statistics(project_id),
                'merge_requests': self._get_merge_request_statistics(project_id),
                'contributors': self._get_contributor_statistics(project_id)
            }
            
            return metrics
    
    def get_group_metrics(self, group_id: Union[int, str]) -> Dict[str, Any]:
        """Get aggregated metrics for all projects in a group.
        
        Args:
            group_id: Group ID or path
            
        Returns:
            Dictionary containing group-wide metrics
        """
        with OperationLogger(logger, "group analytics", group_id=group_id):
            # Get all projects in the group
            projects = list(self.client.get_projects(
                group_id=group_id,
                include_subgroups=True,
                archived=False
            ))
            
            group_metrics = {
                'group_id': group_id,
                'total_projects': len(projects),
                'projects': [],
                'summary': {
                    'total_commits': 0,
                    'total_branches': 0,
                    'total_issues': 0,
                    'total_merge_requests': 0,
                    'active_contributors': set()
                }
            }
            
            for project in projects:
                try:
                    project_metrics = self.get_project_metrics(project['id'])
                    group_metrics['projects'].append(project_metrics)
                    
                    # Aggregate summary
                    group_metrics['summary']['total_commits'] += project_metrics['commits']['total']
                    group_metrics['summary']['total_branches'] += project_metrics['branches']['total']
                    group_metrics['summary']['total_issues'] += project_metrics['issues']['total']
                    group_metrics['summary']['total_merge_requests'] += project_metrics['merge_requests']['total']
                    
                    # Add contributors
                    for contributor in project_metrics['contributors']['top_contributors']:
                        group_metrics['summary']['active_contributors'].add(contributor['name'])
                        
                except Exception as e:
                    logger.warning(f"Failed to get metrics for project {project['id']}: {e}")
            
            # Convert set to count
            group_metrics['summary']['active_contributors'] = len(
                group_metrics['summary']['active_contributors']
            )
            
            return group_metrics
    
    def _get_commit_statistics(self, project_id: Union[int, str]) -> Dict[str, Any]:
        """Get commit statistics for a project."""
        try:
            # Get commits from last 30 days
            since = (datetime.now() - timedelta(days=30)).isoformat()
            commits = list(self.client._paginated_get(
                f'projects/{project_id}/repository/commits',
                params={'since': since}
            ))
            
            # Calculate statistics
            commits_by_day = defaultdict(int)
            commits_by_author = defaultdict(int)
            
            for commit in commits:
                # Group by day
                commit_date = datetime.fromisoformat(
                    commit['created_at'].replace('Z', '+00:00')
                ).date()
                commits_by_day[str(commit_date)] += 1
                
                # Group by author
                author_name = commit.get('author_name', 'Unknown')
                commits_by_author[author_name] += 1
            
            return {
                'total': len(commits),
                'last_30_days': len(commits),
                'by_day': dict(commits_by_day),
                'by_author': dict(commits_by_author),
                'average_per_day': len(commits) / 30 if commits else 0
            }
        except Exception as e:
            logger.error(f"Failed to get commit statistics: {e}")
            return {
                'total': 0,
                'last_30_days': 0,
                'by_day': {},
                'by_author': {},
                'average_per_day': 0
            }
    
    def _get_branch_statistics(self, project_id: Union[int, str]) -> Dict[str, Any]:
        """Get branch statistics for a project."""
        try:
            branches = list(self.client._paginated_get(
                f'projects/{project_id}/repository/branches'
            ))
            
            active_branches = []
            stale_branches = []
            protected_branches = []
            
            for branch in branches:
                if branch.get('protected'):
                    protected_branches.append(branch['name'])
                
                # Check if branch is stale (no commits in 30 days)
                last_commit_date = datetime.fromisoformat(
                    branch['commit']['created_at'].replace('Z', '+00:00')
                )
                if (datetime.now(last_commit_date.tzinfo) - last_commit_date).days > 30:
                    stale_branches.append(branch['name'])
                else:
                    active_branches.append(branch['name'])
            
            return {
                'total': len(branches),
                'active': len(active_branches),
                'stale': len(stale_branches),
                'protected': len(protected_branches),
                'branch_names': [b['name'] for b in branches]
            }
        except Exception as e:
            logger.error(f"Failed to get branch statistics: {e}")
            return {
                'total': 0,
                'active': 0,
                'stale': 0,
                'protected': 0,
                'branch_names': []
            }
    
    def _get_issue_statistics(self, project_id: Union[int, str]) -> Dict[str, Any]:
        """Get issue statistics for a project."""
        try:
            # Get all issues
            all_issues = list(self.client._paginated_get(
                f'projects/{project_id}/issues',
                params={'scope': 'all'}
            ))
            
            open_issues = [i for i in all_issues if i['state'] == 'opened']
            closed_issues = [i for i in all_issues if i['state'] == 'closed']
            
            # Group by labels
            issues_by_label = defaultdict(int)
            for issue in all_issues:
                for label in issue.get('labels', []):
                    issues_by_label[label] += 1
            
            return {
                'total': len(all_issues),
                'open': len(open_issues),
                'closed': len(closed_issues),
                'by_label': dict(issues_by_label),
                'closure_rate': len(closed_issues) / len(all_issues) if all_issues else 0
            }
        except Exception as e:
            logger.error(f"Failed to get issue statistics: {e}")
            return {
                'total': 0,
                'open': 0,
                'closed': 0,
                'by_label': {},
                'closure_rate': 0
            }
    
    def _get_merge_request_statistics(self, project_id: Union[int, str]) -> Dict[str, Any]:
        """Get merge request statistics for a project."""
        try:
            # Get all merge requests
            all_mrs = list(self.client._paginated_get(
                f'projects/{project_id}/merge_requests',
                params={'scope': 'all'}
            ))
            
            open_mrs = [mr for mr in all_mrs if mr['state'] == 'opened']
            merged_mrs = [mr for mr in all_mrs if mr['state'] == 'merged']
            closed_mrs = [mr for mr in all_mrs if mr['state'] == 'closed']
            
            return {
                'total': len(all_mrs),
                'open': len(open_mrs),
                'merged': len(merged_mrs),
                'closed': len(closed_mrs),
                'merge_rate': len(merged_mrs) / len(all_mrs) if all_mrs else 0
            }
        except Exception as e:
            logger.error(f"Failed to get merge request statistics: {e}")
            return {
                'total': 0,
                'open': 0,
                'merged': 0,
                'closed': 0,
                'merge_rate': 0
            }
    
    def _get_contributor_statistics(self, project_id: Union[int, str]) -> Dict[str, Any]:
        """Get contributor statistics for a project."""
        try:
            # Get contributors from commits
            contributors = list(self.client._paginated_get(
                f'projects/{project_id}/repository/contributors'
            ))
            
            # Sort by commits
            contributors.sort(key=lambda x: x['commits'], reverse=True)
            
            return {
                'total': len(contributors),
                'top_contributors': [
                    {
                        'name': c['name'],
                        'email': c['email'],
                        'commits': c['commits'],
                        'additions': c.get('additions', 0),
                        'deletions': c.get('deletions', 0)
                    }
                    for c in contributors[:10]  # Top 10
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get contributor statistics: {e}")
            return {
                'total': 0,
                'top_contributors': []
            }
    
    def generate_summary_report(
        self, 
        metrics: Dict[str, Any],
        format: str = 'markdown'
    ) -> str:
        """Generate a summary report from metrics.
        
        Args:
            metrics: Metrics dictionary from get_project_metrics or get_group_metrics
            format: Output format ('markdown', 'json', 'text')
            
        Returns:
            Formatted report string
        """
        if format == 'json':
            return json.dumps(metrics, indent=2, default=str)
        
        elif format == 'markdown':
            return self._generate_markdown_report(metrics)
        
        else:  # text
            return self._generate_text_report(metrics)
    
    def _generate_markdown_report(self, metrics: Dict[str, Any]) -> str:
        """Generate markdown formatted report."""
        lines = []
        
        if 'project' in metrics:
            # Single project report
            project = metrics['project']
            lines.append(f"# GitLab Analytics Report: {project['name']}")
            lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"\n## Project Information")
            lines.append(f"- **Path:** {project['path']}")
            lines.append(f"- **Created:** {project['created_at']}")
            lines.append(f"- **Last Activity:** {project['last_activity_at']}")
            lines.append(f"- **Default Branch:** {project['default_branch']}")
            lines.append(f"- **Visibility:** {project['visibility']}")
            
            lines.append(f"\n## Commit Statistics")
            commits = metrics['commits']
            lines.append(f"- **Total Commits (last 30 days):** {commits['total']}")
            lines.append(f"- **Average per Day:** {commits['average_per_day']:.1f}")
            if commits['by_author']:
                lines.append(f"\n### Top Committers")
                for author, count in sorted(
                    commits['by_author'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]:
                    lines.append(f"- {author}: {count} commits")
            
            lines.append(f"\n## Branch Statistics")
            branches = metrics['branches']
            lines.append(f"- **Total Branches:** {branches['total']}")
            lines.append(f"- **Active Branches:** {branches['active']}")
            lines.append(f"- **Stale Branches:** {branches['stale']}")
            lines.append(f"- **Protected Branches:** {branches['protected']}")
            
            lines.append(f"\n## Issue Statistics")
            issues = metrics['issues']
            lines.append(f"- **Total Issues:** {issues['total']}")
            lines.append(f"- **Open Issues:** {issues['open']}")
            lines.append(f"- **Closed Issues:** {issues['closed']}")
            lines.append(f"- **Closure Rate:** {issues['closure_rate']*100:.1f}%")
            
            lines.append(f"\n## Merge Request Statistics")
            mrs = metrics['merge_requests']
            lines.append(f"- **Total MRs:** {mrs['total']}")
            lines.append(f"- **Open MRs:** {mrs['open']}")
            lines.append(f"- **Merged MRs:** {mrs['merged']}")
            lines.append(f"- **Merge Rate:** {mrs['merge_rate']*100:.1f}%")
            
            lines.append(f"\n## Contributors")
            contributors = metrics['contributors']
            lines.append(f"- **Total Contributors:** {contributors['total']}")
            if contributors['top_contributors']:
                lines.append(f"\n### Top Contributors")
                for contributor in contributors['top_contributors'][:5]:
                    lines.append(
                        f"- **{contributor['name']}**: "
                        f"{contributor['commits']} commits, "
                        f"+{contributor['additions']}/-{contributor['deletions']}"
                    )
        
        else:
            # Group report
            lines.append("# GitLab Group Analytics Report")
            lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"\n## Summary")
            summary = metrics['summary']
            lines.append(f"- **Total Projects:** {metrics['total_projects']}")
            lines.append(f"- **Total Commits:** {summary['total_commits']}")
            lines.append(f"- **Total Branches:** {summary['total_branches']}")
            lines.append(f"- **Total Issues:** {summary['total_issues']}")
            lines.append(f"- **Total Merge Requests:** {summary['total_merge_requests']}")
            lines.append(f"- **Active Contributors:** {summary['active_contributors']}")
        
        return '\n'.join(lines)
    
    def _generate_text_report(self, metrics: Dict[str, Any]) -> str:
        """Generate plain text report."""
        # Similar to markdown but without formatting
        return self._generate_markdown_report(metrics).replace('#', '').replace('*', '')