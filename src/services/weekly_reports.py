"""Weekly productivity report generation service."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import statistics

from ..api import GitLabClient
from ..utils.logger import OperationLogger
from .analytics_advanced import AdvancedAnalytics
from ..utils.config import Config

logger = logging.getLogger(__name__)


class WeeklyProductivityReporter:
    """Generate comprehensive weekly productivity reports for team syncs."""
    
    def __init__(self, client: GitLabClient, config: Config = None):
        """Initialize weekly reporter.
        
        Args:
            client: GitLab API client
            config: Configuration instance
        """
        self.client = client
        self.analytics = AdvancedAnalytics(client)
        self.config = config or Config()
        self._contributor_mapping = self._build_contributor_mapping()
    
    def _build_contributor_mapping(self) -> Dict[str, str]:
        """Build contributor mapping from configuration."""
        mapping = {}
        email_mapping = {}
        
        # Get contributor mappings from config
        contributor_config = self.config.get('contributors', {})
        for canonical_name, aliases in contributor_config.items():
            mapping[canonical_name] = canonical_name
            if isinstance(aliases, list):
                for alias in aliases:
                    mapping[alias] = canonical_name
                    # If alias looks like email, also map it in email mapping
                    if '@' in alias:
                        email_mapping[alias.lower()] = canonical_name
        
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
        
        self.email_mapping = email_mapping
        return mapping
    
    def _normalize_contributor_name(self, name: str, email: str = '') -> str:
        """Normalize contributor name using mapping and email."""
        # First check email-based mapping (most reliable)
        if email and hasattr(self, 'email_mapping'):
            email_lower = email.lower()
            if email_lower in self.email_mapping:
                return self.email_mapping[email_lower]
        
        # Check explicit name mapping
        if name in self._contributor_mapping:
            return self._contributor_mapping[name]
        
        # Check case-insensitive name mapping
        name_lower = name.lower()
        if name_lower in self._contributor_mapping:
            return self._contributor_mapping[name_lower]
        
        # Try to match by email domain patterns
        if email:
            # Extract username from email
            email_username = email.split('@')[0]
            if email_username in self._contributor_mapping:
                return self._contributor_mapping[email_username]
            
            # Simple heuristics for common patterns
            email_lower = email.lower()
            name_lower = name.lower()
            
            # If email starts with name, they're likely the same person
            if email_lower.startswith(name_lower.replace(' ', '.')):
                return name
            if email_lower.startswith(name_lower.replace(' ', '')):
                return name
        
        return name
    
    def _get_branch_specific_changes(
        self, 
        project_id: int, 
        base_branch: str, 
        target_branch: str
    ) -> Tuple[int, int, int]:
        """Get line changes unique to target branch compared to base branch.
        
        Args:
            project_id: Project ID
            base_branch: Base branch name (usually main/master)
            target_branch: Target branch name
            
        Returns:
            Tuple of (additions, deletions, net_change)
        """
        try:
            # If comparing to the same branch, return 0
            if base_branch == target_branch:
                return (0, 0, 0)
            
            # Use GitLab compare API to get diff between branches
            compare_data = self.client._request(
                'GET',
                f'projects/{project_id}/repository/compare',
                params={
                    'from': base_branch,
                    'to': target_branch,
                    'straight': 'true'  # Direct comparison, not merge base
                }
            )
            
            # Sum up all the diffs
            total_additions = 0
            total_deletions = 0
            
            diffs = compare_data.get('diffs', [])
            for diff in diffs:
                # Parse diff content to count lines
                diff_content = diff.get('diff', '')
                if diff_content:
                    additions, deletions = self._parse_diff_stats(diff_content)
                    total_additions += additions
                    total_deletions += deletions
            
            net_change = total_additions - total_deletions
            return (total_additions, total_deletions, net_change)
            
        except Exception as e:
            logger.debug(f"Failed to get branch diff {base_branch}..{target_branch}: {e}")
            return (0, 0, 0)
    
    def _parse_diff_stats(self, diff_content: str) -> Tuple[int, int]:
        """Parse diff content to count additions and deletions.
        
        Args:
            diff_content: Raw diff content
            
        Returns:
            Tuple of (additions, deletions)
        """
        lines = diff_content.split('\n')
        additions = 0
        deletions = 0
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        
        return (additions, deletions)
        
    def generate_team_report(
        self,
        group_ids: List[int],
        team_members: Optional[List[str]] = None,
        weeks_back: int = 1
    ) -> Dict[str, Any]:
        """Generate comprehensive weekly team productivity report.
        
        Args:
            group_ids: List of GitLab group IDs to analyze
            team_members: List of usernames/emails to focus on (optional)
            weeks_back: Number of weeks to look back (default: 1)
            
        Returns:
            Comprehensive report data
        """
        with OperationLogger(logger, "weekly report generation"):
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(weeks=weeks_back)
            
            logger.info(f"Generating report for {weeks_back} week(s) ending {end_date.date()}")
            logger.info(f"Date range: {start_date.date()} to {end_date.date()} (UTC)")
            logger.debug(f"Start: {start_date.isoformat()}, End: {end_date.isoformat()}")
            
            report = {
                'metadata': {
                    'generated_at': end_date.isoformat(),
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'weeks_analyzed': weeks_back,
                    'groups_analyzed': len(group_ids),
                    'team_size': len(team_members) if team_members else 'All contributors'
                },
                'executive_summary': {},
                'team_activity': {},
                'project_breakdown': {},
                'individual_metrics': {},
                'insights_and_actions': {}
            }
            
            # Collect all projects from groups
            all_projects = []
            for group_id in group_ids:
                projects = list(self.client.get_projects(
                    group_id=group_id,
                    include_subgroups=True,
                    archived=False
                ))
                all_projects.extend(projects)
            
            logger.info(f"Analyzing {len(all_projects)} projects across {len(group_ids)} groups")
            
            # Generate each section
            report['team_activity'] = self._generate_team_activity(
                all_projects, start_date, end_date, team_members
            )
            
            report['project_breakdown'] = self._generate_project_breakdown(
                all_projects, start_date, end_date
            )
            
            report['individual_metrics'] = self._generate_individual_metrics(
                all_projects, start_date, end_date, team_members
            )
            
            report['executive_summary'] = self._generate_executive_summary(
                report['team_activity'], 
                report['project_breakdown'],
                report['individual_metrics'],
                start_date,
                end_date
            )
            
            report['insights_and_actions'] = self._generate_insights_and_actions(
                report
            )
            
            # Add detailed tables
            report['detailed_tables'] = self._generate_detailed_tables(
                all_projects, start_date, end_date, team_members
            )
            
            return report
    
    def _generate_team_activity(
        self,
        projects: List[Dict],
        start_date: datetime,
        end_date: datetime,
        team_members: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate overall team activity metrics."""
        activity = {
            'commits': {'total': 0, 'by_day': defaultdict(int), 'by_author': defaultdict(int)},
            'merge_requests': {'total': 0, 'opened': 0, 'merged': 0, 'closed': 0},
            'issues': {'total': 0, 'opened': 0, 'closed': 0, 'in_progress': 0},
            'velocity_trends': {},
            'collaboration_metrics': {}
        }
        
        for project in projects:
            try:
                project_id = project['id']
                
                # Commits - get all from API first
                all_commits = list(self.client._paginated_get(
                    f'projects/{project_id}/repository/commits',
                    params={
                        'since': start_date.isoformat(),
                        'until': end_date.isoformat()
                    }
                ))
                
                # Client-side date filtering for accurate counts
                commits = []
                for commit in all_commits:
                    try:
                        commit_date = datetime.fromisoformat(
                            commit['created_at'].replace('Z', '+00:00')
                        )
                        if start_date <= commit_date <= end_date:
                            commits.append(commit)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Failed to parse commit date in team activity: {e}")
                        continue
                
                # Debug: Log commit count per project (after filtering)
                if commits:
                    logger.info(f"Project {project['name']}: {len(commits)} commits in period")
                    
                    # Debug: Show unique authors in this project
                    unique_authors = set()
                    for commit in commits:
                        author = commit.get('author_name', 'Unknown')
                        email = commit.get('author_email', '')
                        unique_authors.add(f"{author} <{email}>")
                    
                    if len(unique_authors) > 0:
                        logger.debug(f"  Unique commit authors: {', '.join(sorted(unique_authors))}")
                
                for commit in commits:
                    author = commit.get('author_name', 'Unknown')
                    # Filter by team members if specified
                    if team_members and author not in team_members:
                        continue
                    
                    activity['commits']['total'] += 1
                    activity['commits']['by_author'][author] += 1
                    
                    # Group by day
                    commit_date = datetime.fromisoformat(
                        commit['created_at'].replace('Z', '+00:00')
                    ).date()
                    activity['commits']['by_day'][str(commit_date)] += 1
                
                # Merge Requests
                merge_requests = list(self.client._paginated_get(
                    f'projects/{project_id}/merge_requests',
                    params={
                        'created_after': start_date.isoformat(),
                        'created_before': end_date.isoformat(),
                        'scope': 'all'
                    }
                ))
                
                for mr in merge_requests:
                    author = mr.get('author', {}).get('username', 'Unknown')
                    if team_members and author not in team_members:
                        continue
                    
                    activity['merge_requests']['total'] += 1
                    if mr['state'] == 'opened':
                        activity['merge_requests']['opened'] += 1
                    elif mr['state'] == 'merged':
                        activity['merge_requests']['merged'] += 1
                    elif mr['state'] == 'closed':
                        activity['merge_requests']['closed'] += 1
                
                # Issues
                issues = list(self.client._paginated_get(
                    f'projects/{project_id}/issues',
                    params={
                        'created_after': start_date.isoformat(),
                        'created_before': end_date.isoformat(),
                        'scope': 'all'
                    }
                ))
                
                for issue in issues:
                    assignee = issue.get('assignee', {})
                    if assignee:
                        assignee_username = assignee.get('username', 'Unknown')
                        if team_members and assignee_username not in team_members:
                            continue
                    
                    activity['issues']['total'] += 1
                    if issue['state'] == 'opened':
                        activity['issues']['opened'] += 1
                    elif issue['state'] == 'closed':
                        activity['issues']['closed'] += 1
                
            except Exception as e:
                logger.warning(f"Failed to analyze project {project.get('name', project['id'])}: {e}")
        
        # Calculate velocity trends
        activity['velocity_trends'] = self._calculate_velocity_trends(activity)
        
        # Calculate collaboration metrics
        activity['collaboration_metrics'] = self._calculate_collaboration_metrics(activity)
        
        return activity
    
    def _generate_project_breakdown(
        self,
        projects: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate project-by-project breakdown with health indicators."""
        breakdown = {
            'projects': [],
            'health_summary': {'healthy': 0, 'warning': 0, 'critical': 0},
            'activity_distribution': {}
        }
        
        for project in projects:
            try:
                project_data = {
                    'id': project['id'],
                    'name': project['name'],
                    'path': project['path_with_namespace'],
                    'last_activity': project.get('last_activity_at'),
                    'default_branch': project.get('default_branch'),
                    'visibility': project.get('visibility'),
                    'metrics': {},
                    'health_status': 'unknown',
                    'health_score': 0,
                    'recommendations': []
                }
                
                # Get activity metrics for this project
                project_id = project['id']
                
                # Recent commits (using actual date range)
                recent_commits = list(self.client._paginated_get(
                    f'projects/{project_id}/repository/commits',
                    params={
                        'since': start_date.isoformat(),
                        'until': end_date.isoformat()
                    }
                ))
                
                # Issues in the analysis period
                issues = list(self.client._paginated_get(
                    f'projects/{project_id}/issues',
                    params={'scope': 'all'}
                ))
                
                # Open issues
                open_issues = [i for i in issues if i['state'] == 'opened']
                
                # Issues created in period
                period_issues = [
                    i for i in issues
                    if start_date <= datetime.fromisoformat(
                        i['created_at'].replace('Z', '+00:00')
                    ) <= end_date
                ]
                
                # Merge requests
                merge_requests = list(self.client._paginated_get(
                    f'projects/{project_id}/merge_requests',
                    params={'scope': 'all'}
                ))
                
                open_mrs = [mr for mr in merge_requests if mr['state'] == 'opened']
                
                project_data['metrics'] = {
                    'commits_this_week': len(recent_commits),
                    'open_issues': len(open_issues),
                    'issues_created_period': len(period_issues),
                    'open_merge_requests': len(open_mrs),
                    'last_commit_days_ago': self._days_since_last_commit(project_id)
                }
                
                # Calculate health status
                health_score = self._calculate_project_health(project_data['metrics'])
                project_data['health_score'] = health_score
                
                if health_score >= 80:
                    project_data['health_status'] = 'healthy'
                    breakdown['health_summary']['healthy'] += 1
                elif health_score >= 60:
                    project_data['health_status'] = 'warning'
                    breakdown['health_summary']['warning'] += 1
                else:
                    project_data['health_status'] = 'critical'
                    breakdown['health_summary']['critical'] += 1
                
                # Generate recommendations
                project_data['recommendations'] = self._generate_project_recommendations(
                    project_data['metrics']
                )
                
                breakdown['projects'].append(project_data)
                
            except Exception as e:
                logger.warning(f"Failed to analyze project {project.get('name', project['id'])}: {e}")
        
        # Sort projects by health score (worst first for attention)
        breakdown['projects'].sort(key=lambda x: x['health_score'])
        
        return breakdown
    
    def _generate_individual_metrics(
        self,
        projects: List[Dict],
        start_date: datetime,
        end_date: datetime,
        team_members: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate individual contributor metrics."""
        individuals = defaultdict(lambda: {
            'commits': 0,
            'lines_added': 0,
            'lines_removed': 0,
            'net_lines_changed': 0,  # lines_added - lines_removed
            'gross_lines_changed': 0,  # lines_added + lines_removed (total churn)
            'merge_requests_created': 0,
            'merge_requests_merged': 0,
            'issues_created': 0,
            'issues_resolved': 0,
            'issues_opened_this_week': 0,  # New issues created this week
            'issues_closed_this_week': 0,  # Issues closed this week
            'code_reviews': 0,
            'active_projects': set(),
            'collaboration_score': 0,
            'emails': set(),  # Track all email addresses used
            'usernames': set()  # Track all usernames seen
        })
        
        for project in projects:
            try:
                project_id = project['id']
                
                # Commits - get all from API first
                all_commits = list(self.client._paginated_get(
                    f'projects/{project_id}/repository/commits',
                    params={
                        'since': start_date.isoformat(),
                        'until': end_date.isoformat()
                    }
                ))
                
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
                        logger.warning(f"Failed to parse commit date in individual metrics: {e}")
                        continue
                
                for commit in commits:
                    author_name = commit.get('author_name', 'Unknown')
                    author_email = commit.get('author_email', '')
                    
                    # Normalize contributor name
                    author = self._normalize_contributor_name(author_name, author_email)
                    
                    if team_members and author not in team_members and author_name not in team_members:
                        continue
                    
                    individuals[author]['commits'] += 1
                    individuals[author]['active_projects'].add(project['name'])
                    
                    # Track email addresses and original names
                    if author_email:
                        individuals[author]['emails'].add(author_email)
                    if author_name != author:
                        individuals[author]['original_names'] = individuals[author].get('original_names', set())
                        individuals[author]['original_names'].add(author_name)
                    
                    # Add line stats if available
                    stats = commit.get('stats', {})
                    additions = stats.get('additions', 0)
                    deletions = stats.get('deletions', 0)
                    
                    individuals[author]['lines_added'] += additions
                    individuals[author]['lines_removed'] += deletions
                    individuals[author]['net_lines_changed'] += (additions - deletions)
                    individuals[author]['gross_lines_changed'] += (additions + deletions)
                
                # Merge Requests
                merge_requests = list(self.client._paginated_get(
                    f'projects/{project_id}/merge_requests',
                    params={
                        'created_after': start_date.isoformat(),
                        'created_before': end_date.isoformat(),
                        'scope': 'all'
                    }
                ))
                
                for mr in merge_requests:
                    author_username = mr.get('author', {}).get('username', 'Unknown')
                    author_name = mr.get('author', {}).get('name', '')
                    
                    # Use username as primary identifier for MRs
                    author = author_username
                    if team_members and author not in team_members:
                        continue
                    
                    individuals[author]['merge_requests_created'] += 1
                    individuals[author]['usernames'].add(author_username)
                    if mr['state'] == 'merged':
                        individuals[author]['merge_requests_merged'] += 1
                
                # Issues
                issues = list(self.client._paginated_get(
                    f'projects/{project_id}/issues',
                    params={
                        'created_after': start_date.isoformat(),
                        'created_before': end_date.isoformat(),
                        'scope': 'all'
                    }
                ))
                
                for issue in issues:
                    created_at = datetime.fromisoformat(
                        issue['created_at'].replace('Z', '+00:00')
                    )
                    
                    # Issue creator
                    author = issue.get('author', {}).get('username', 'Unknown')
                    if not team_members or author in team_members:
                        individuals[author]['issues_created'] += 1
                        
                        # Check if created this week
                        if start_date <= created_at <= end_date:
                            individuals[author]['issues_opened_this_week'] += 1
                    
                    # Issue closer (if closed this week)
                    if issue['state'] == 'closed' and issue.get('closed_at'):
                        closed_at = datetime.fromisoformat(
                            issue['closed_at'].replace('Z', '+00:00')
                        )
                        
                        if start_date <= closed_at <= end_date:
                            # Use assignee or closer
                            closer = None
                            if issue.get('closed_by'):
                                closer = issue['closed_by'].get('username', 'Unknown')
                            elif issue.get('assignee'):
                                closer = issue['assignee'].get('username', 'Unknown')
                            
                            if closer and (not team_members or closer in team_members):
                                individuals[closer]['issues_resolved'] += 1
                                individuals[closer]['issues_closed_this_week'] += 1
                
            except Exception as e:
                logger.warning(f"Failed to analyze individual metrics for project {project.get('name')}: {e}")
        
        # Convert to regular dict and calculate derived metrics
        result = {}
        for username, metrics in individuals.items():
            metrics['active_projects'] = list(metrics['active_projects'])
            metrics['project_count'] = len(metrics['active_projects'])
            
            # Calculate collaboration score
            metrics['collaboration_score'] = self._calculate_individual_collaboration_score(metrics)
            
            # Calculate overall productivity score
            metrics['productivity_score'] = self._calculate_productivity_score(metrics)
            
            result[username] = metrics
        
        return {
            'contributors': result,
            'team_stats': self._calculate_team_distribution_stats(result)
        }
    
    def _generate_executive_summary(
        self,
        team_activity: Dict,
        project_breakdown: Dict,
        individual_metrics: Dict,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate executive summary with key insights."""
        # Calculate period information
        days_analyzed = (end_date - start_date).days
        period_desc = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        summary = {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days_analyzed': days_analyzed,
                'description': period_desc
            },
            'key_metrics': {},
            'trends': {},
            'highlights': [],
            'concerns': [],
            'data_quality': []
        }
        
        # Key metrics
        summary['key_metrics'] = {
            'total_commits': team_activity['commits']['total'],
            'total_merge_requests': team_activity['merge_requests']['total'],
            'merge_rate': (
                team_activity['merge_requests']['merged'] / 
                max(team_activity['merge_requests']['total'], 1) * 100
            ),
            'total_issues': team_activity['issues']['total'],
            'active_contributors': len(individual_metrics['contributors']),
            'healthy_projects': project_breakdown['health_summary']['healthy'],
            'projects_needing_attention': (
                project_breakdown['health_summary']['warning'] + 
                project_breakdown['health_summary']['critical']
            ),
            'average_commits_per_contributor': (
                team_activity['commits']['total'] / 
                max(len(individual_metrics['contributors']), 1)
            )
        }
        
        # Highlights
        if summary['key_metrics']['merge_rate'] > 80:
            summary['highlights'].append("🎯 Excellent merge request acceptance rate")
        
        if summary['key_metrics']['healthy_projects'] > project_breakdown['health_summary']['critical']:
            summary['highlights'].append("💚 More healthy projects than critical ones")
        
        top_contributor = max(
            individual_metrics['contributors'].items(),
            key=lambda x: x[1]['commits'],
            default=(None, {'commits': 0})
        )
        if top_contributor[0]:
            summary['highlights'].append(
                f"⭐ Top contributor: {top_contributor[0]} with {top_contributor[1]['commits']} commits this period"
            )
        
        # Concerns
        if project_breakdown['health_summary']['critical'] > 0:
            summary['concerns'].append(
                f"🚨 {project_breakdown['health_summary']['critical']} projects in critical health"
            )
        
        if summary['key_metrics']['merge_rate'] < 50:
            summary['concerns'].append("⚠️ Low merge request acceptance rate")
        
        if team_activity['commits']['total'] < 10:
            summary['concerns'].append("📉 Very low commit activity this week")
        
        return summary
    
    def _generate_insights_and_actions(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable insights and recommended actions."""
        insights = {
            'recommended_actions': [],
            'team_focus_areas': [],
            'individual_coaching': [],
            'process_improvements': []
        }
        
        # Analyze patterns and generate recommendations
        project_breakdown = report['project_breakdown']
        individual_metrics = report['individual_metrics']
        team_activity = report['team_activity']
        
        # Project-based recommendations
        critical_projects = [
            p for p in project_breakdown['projects'] 
            if p['health_status'] == 'critical'
        ]
        
        if critical_projects:
            insights['recommended_actions'].append({
                'priority': 'high',
                'action': f"Address {len(critical_projects)} critical health projects",
                'projects': [p['name'] for p in critical_projects[:3]],
                'rationale': "These projects may be blocking team progress"
            })
        
        # Individual coaching opportunities
        contributors = individual_metrics['contributors']
        if contributors:
            # Find contributors with low collaboration
            low_collaboration = [
                name for name, metrics in contributors.items()
                if metrics['collaboration_score'] < 50
            ]
            
            if low_collaboration:
                insights['individual_coaching'].append({
                    'focus': 'collaboration',
                    'individuals': low_collaboration[:3],
                    'suggestion': 'Encourage more code reviews and cross-project work'
                })
        
        # Process improvements
        if team_activity['merge_requests']['total'] > 0:
            merge_rate = (
                team_activity['merge_requests']['merged'] / 
                team_activity['merge_requests']['total']
            )
            if merge_rate < 0.7:
                insights['process_improvements'].append({
                    'area': 'code_review',
                    'issue': f"Only {merge_rate*100:.1f}% of MRs are being merged",
                    'suggestion': 'Review MR approval process and requirements'
                })
        
        return insights
    
    def _calculate_velocity_trends(self, activity: Dict) -> Dict:
        """Calculate velocity trends from activity data."""
        # Simple trend calculation based on daily commits
        daily_commits = list(activity['commits']['by_day'].values())
        if len(daily_commits) < 2:
            return {'trend': 'insufficient_data', 'direction': 'neutral'}
        
        # Calculate simple trend
        recent_avg = statistics.mean(daily_commits[-3:]) if len(daily_commits) >= 3 else daily_commits[-1]
        early_avg = statistics.mean(daily_commits[:3]) if len(daily_commits) >= 3 else daily_commits[0]
        
        if recent_avg > early_avg * 1.2:
            direction = 'increasing'
        elif recent_avg < early_avg * 0.8:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'trend': 'calculated',
            'direction': direction,
            'recent_average': recent_avg,
            'early_average': early_avg
        }
    
    def _calculate_collaboration_metrics(self, activity: Dict) -> Dict:
        """Calculate team collaboration metrics."""
        total_authors = len(activity['commits']['by_author'])
        if total_authors == 0:
            return {'collaboration_score': 0, 'distribution': 'no_activity'}
        
        # Calculate contribution distribution
        commit_counts = list(activity['commits']['by_author'].values())
        
        if len(commit_counts) == 1:
            distribution = 'single_contributor'
        else:
            # Gini coefficient for distribution equality
            sorted_counts = sorted(commit_counts)
            n = len(sorted_counts)
            cumsum = [sum(sorted_counts[:i+1]) for i in range(n)]
            gini = (n + 1 - 2 * sum((n + 1 - i) * count for i, count in enumerate(sorted_counts))) / (n * sum(sorted_counts))
            
            if gini < 0.3:
                distribution = 'well_distributed'
            elif gini < 0.6:
                distribution = 'moderately_distributed'
            else:
                distribution = 'concentrated'
        
        collaboration_score = max(0, 100 - (len(commit_counts) * 10))  # Simple scoring
        
        return {
            'collaboration_score': collaboration_score,
            'distribution': distribution,
            'active_contributors': total_authors,
            'gini_coefficient': gini if 'gini' in locals() else 0
        }
    
    def _calculate_project_health(self, metrics: Dict) -> float:
        """Calculate project health score based on activity metrics."""
        score = 100
        
        # Penalize based on various factors
        if metrics['commits_this_week'] == 0:
            score -= 30
        elif metrics['commits_this_week'] < 3:
            score -= 15
        
        if metrics['open_issues'] > 20:
            score -= 20
        elif metrics['open_issues'] > 10:
            score -= 10
        
        if metrics['last_commit_days_ago'] > 7:
            score -= 25
        elif metrics['last_commit_days_ago'] > 3:
            score -= 10
        
        if metrics['open_merge_requests'] > 10:
            score -= 15
        
        return max(0, min(100, score))
    
    def _days_since_last_commit(self, project_id: int) -> int:
        """Calculate days since last commit in project."""
        try:
            commits = list(self.client._paginated_get(
                f'projects/{project_id}/repository/commits',
                params={'per_page': 1}
            ))
            
            if commits:
                last_commit_date = datetime.fromisoformat(
                    commits[0]['created_at'].replace('Z', '+00:00')
                )
                return (datetime.now(timezone.utc) - last_commit_date).days
            
            return 999  # Very old or no commits
            
        except Exception:
            return 999
    
    def _generate_project_recommendations(self, metrics: Dict) -> List[str]:
        """Generate specific recommendations for a project."""
        recommendations = []
        
        if metrics['commits_this_week'] == 0:
            recommendations.append("No commits this week - check if project is active")
        
        if metrics['open_issues'] > 20:
            recommendations.append("High issue count - consider triaging and prioritizing")
        
        if metrics['last_commit_days_ago'] > 14:
            recommendations.append("No recent activity - verify project status")
        
        if metrics['open_merge_requests'] > 5:
            recommendations.append("Review backlog of merge requests")
        
        return recommendations
    
    def _calculate_individual_collaboration_score(self, metrics: Dict) -> float:
        """Calculate individual collaboration score."""
        score = 0
        
        # Points for different activities
        score += min(metrics['code_reviews'] * 5, 25)  # Up to 25 points
        score += min(metrics['project_count'] * 10, 30)  # Up to 30 points
        score += min(metrics['merge_requests_created'] * 3, 20)  # Up to 20 points
        score += min(metrics['issues_created'] * 2, 15)  # Up to 15 points
        score += min(metrics['issues_resolved'] * 3, 10)  # Up to 10 points
        
        return min(100, score)
    
    def _calculate_productivity_score(self, metrics: Dict) -> float:
        """Calculate overall productivity score for individual."""
        # Weighted scoring
        score = 0
        score += metrics['commits'] * 2
        score += metrics['merge_requests_merged'] * 5
        score += metrics['issues_resolved'] * 3
        score += metrics['project_count'] * 5
        
        # Normalize to 0-100 scale (adjust divisor based on your team's typical output)
        return min(100, score / 2)
    
    def _calculate_team_distribution_stats(self, contributors: Dict) -> Dict:
        """Calculate team distribution statistics."""
        if not contributors:
            return {}
        
        commit_counts = [m['commits'] for m in contributors.values()]
        productivity_scores = [m['productivity_score'] for m in contributors.values()]
        
        return {
            'total_contributors': len(contributors),
            'avg_commits': statistics.mean(commit_counts) if commit_counts else 0,
            'median_commits': statistics.median(commit_counts) if commit_counts else 0,
            'avg_productivity': statistics.mean(productivity_scores) if productivity_scores else 0,
            'top_performer': max(contributors.items(), key=lambda x: x[1]['productivity_score'], default=(None, {}))[0],
            'most_collaborative': max(contributors.items(), key=lambda x: x[1]['collaboration_score'], default=(None, {}))[0]
        }
    
    def _generate_detailed_tables(
        self,
        projects: List[Dict],
        start_date: datetime,
        end_date: datetime,
        team_members: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate detailed tables for project and contributor activity."""
        tables = {
            'project_branch_activity': [],
            'project_contributor_activity': []
        }
        
        # Get group information for projects
        group_cache = {}
        
        for project in projects:
            try:
                project_id = project['id']
                project_name = project['name']
                
                # Get group info
                if project.get('namespace', {}).get('parent_id'):
                    group_id = project['namespace']['parent_id']
                else:
                    group_id = project['namespace']['id']
                
                if group_id not in group_cache:
                    try:
                        group_info = self.client._get(f'groups/{group_id}')
                        group_cache[group_id] = group_info.get('name', f'Group-{group_id}')
                    except:
                        group_cache[group_id] = f'Group-{group_id}'
                
                group_name = group_cache[group_id]
                
                # Get all branches with recent activity
                branches = list(self.client._paginated_get(f'projects/{project_id}/repository/branches'))
                
                # Determine the base branch for comparisons
                base_branch = project.get('default_branch', 'main')
                if not base_branch:
                    # Fallback logic to find main branch
                    branch_names = [b['name'] for b in branches]
                    if 'main' in branch_names:
                        base_branch = 'main'
                    elif 'master' in branch_names:
                        base_branch = 'master'
                    elif 'develop' in branch_names:
                        base_branch = 'develop'
                    else:
                        base_branch = branches[0]['name'] if branches else 'main'
                
                # Separate tracking: project-level for contributor table, branch-level for branch table
                project_contributors = defaultdict(lambda: {
                    'commits': 0, 
                    'mrs': 0,
                    'net_lines': 0,
                    'issues_opened': 0,
                    'issues_closed': 0
                })
                
                # Track processed commits to avoid double-counting line changes across branches
                project_processed_commits = set()
                # Track commit ownership (which branch first processed each commit)
                commit_ownership = {}  # commit_id -> branch_name
                # Track all commits per branch for unique commit calculation
                branch_commit_sets = {}  # branch_name -> set of commit_ids
                
                # First pass: collect commits for all branches
                branch_commits_data = {}  # branch_name -> filtered commits list
                
                for branch in branches:
                    branch_name = branch['name']
                    
                    # Get commits for this branch (using correct 'ref' parameter)
                    all_branch_commits = list(self.client._paginated_get(
                        f'projects/{project_id}/repository/commits',
                        since=start_date.isoformat(),
                        until=end_date.isoformat(),
                        ref=branch_name
                    ))
                    
                    # Client-side date filtering to ensure accuracy
                    branch_commits = []
                    for commit in all_branch_commits:
                        try:
                            commit_date = datetime.fromisoformat(
                                commit['created_at'].replace('Z', '+00:00')
                            )
                            if start_date <= commit_date <= end_date:
                                branch_commits.append(commit)
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Failed to parse commit date for {commit.get('id', 'unknown')}: {e}")
                            continue
                    
                    branch_commits_data[branch_name] = branch_commits
                    branch_commit_sets[branch_name] = set(c['id'] for c in branch_commits)
                    
                    # Debug logging for branch commits
                    if branch_commits:
                        logger.debug(f"Branch {branch_name}: {len(branch_commits)} commits after filtering")
                        if len(branch_commits) > 0:
                            first_commit_id = branch_commits[0]['id'][:8]
                            logger.debug(f"  First commit: {first_commit_id}")
                
                # Calculate unique commits per branch (commits not in other branches)
                unique_commits_per_branch = {}
                for branch_name, commit_ids in branch_commit_sets.items():
                    other_branches_commits = set()
                    for other_branch, other_commits in branch_commit_sets.items():
                        if other_branch != branch_name:
                            other_branches_commits.update(other_commits)
                    
                    unique_commits = commit_ids - other_branches_commits
                    unique_commits_per_branch[branch_name] = unique_commits
                
                # Second pass: process commits and calculate metrics
                for branch in branches:
                    branch_name = branch['name']
                    branch_commits = branch_commits_data[branch_name]
                    
                    # Debug logging for branch commits
                    logger.debug(f"Project {project_name}/{branch_name}: {len(branch_commits)} commits in date range")
                    if branch_commits and logger.isEnabledFor(logging.DEBUG):
                        commit_ids = [c['id'][:8] for c in branch_commits[:3]]
                        logger.debug(f"First 3 commit IDs in {branch_name}: {commit_ids}")
                    
                    # Calculate different types of line changes
                    unique_commit_ids = unique_commits_per_branch[branch_name]
                    unique_commits_count = len(unique_commit_ids)
                    
                    # Method 1: Git diff approach (branch vs base)
                    if branch_name != base_branch:
                        git_diff_additions, git_diff_deletions, git_diff_net = self._get_branch_specific_changes(
                            project_id, base_branch, branch_name
                        )
                    else:
                        # For base branch, use total changes in the period
                        git_diff_net = 0  # Will be calculated from commits below
                        git_diff_additions = 0
                        git_diff_deletions = 0
                    
                    # Track branch-specific metrics (separate from project accumulation)
                    branch_contributors = set()
                    branch_net_lines = 0
                    
                    # Limit stat fetches to avoid too many API calls
                    max_stat_fetches = 10  # Only fetch stats for first 10 commits per branch
                    stat_fetch_count = 0
                    
                    for commit in branch_commits:
                        author_name = commit.get('author_name', 'Unknown')
                        author_email = commit.get('author_email', '')
                        author = self._normalize_contributor_name(author_name, author_email)
                        
                        if team_members and author not in team_members and author_name not in team_members:
                            continue
                        
                        # Branch-specific tracking (for branch activity table)
                        branch_contributors.add(author)
                        
                        # Project-level tracking (for contributor activity table)
                        project_contributors[author]['commits'] += 1
                        
                        # Calculate line changes - need to fetch individual commit for stats
                        commit_id = commit['id']
                        
                        # Track commit ownership and calculate line changes
                        if commit_id not in project_processed_commits:
                            # This is the first branch to process this commit
                            commit_ownership[commit_id] = branch_name
                            
                            stats = commit.get('stats', {})
                            
                            # If no stats and we haven't hit our limit, fetch individual commit details
                            if not stats and stat_fetch_count < max_stat_fetches:
                                try:
                                    commit_details = self.client._request(
                                        'GET',
                                        f'projects/{project_id}/repository/commits/{commit_id}'
                                    )
                                    stats = commit_details.get('stats', {})
                                    stat_fetch_count += 1
                                except Exception as e:
                                    logger.debug(f"Failed to fetch commit stats for {commit_id}: {e}")
                                    stats = {}
                            
                            additions = stats.get('additions', 0)
                            deletions = stats.get('deletions', 0)
                            net_change = additions - deletions
                            
                            # Debug logging for line changes
                            if net_change != 0 and logger.isEnabledFor(logging.DEBUG):
                                logger.debug(f"  Commit {commit_id[:8]} on {branch_name}: {net_change:+d} lines (OWNER)")
                            
                            # Mark this commit as processed
                            project_processed_commits.add(commit_id)
                            
                            # Only the owning branch gets the line changes in current method
                            branch_net_lines += net_change
                            # For base branch, also add to git_diff_net if it's the base
                            if branch_name == base_branch:
                                git_diff_net += net_change
                            
                            # Project-level line changes
                            project_contributors[author]['net_lines'] += net_change
                        else:
                            # Debug logging for skipped commits
                            if logger.isEnabledFor(logging.DEBUG):
                                owner = commit_ownership.get(commit_id, 'unknown')
                                logger.debug(f"  Commit {commit_id[:8]} on {branch_name}: INHERITED (owned by {owner})")
                    
                    # Determine ownership indicators for display
                    owned_commits = sum(1 for commit in branch_commits if commit_ownership.get(commit['id']) == branch_name)
                    inherited_commits = len(branch_commits) - owned_commits
                    
                    # Create ownership indicator for line changes
                    if branch_net_lines > 0:
                        if inherited_commits > 0:
                            lines_indicator = f"+{branch_net_lines}"  # Mixed ownership
                        else:
                            lines_indicator = f"+{branch_net_lines}"  # Full ownership
                    elif branch_net_lines < 0:
                        lines_indicator = f"{branch_net_lines}"
                    else:
                        if len(branch_commits) > 0 and inherited_commits == len(branch_commits):
                            lines_indicator = "0*"  # All inherited
                        else:
                            lines_indicator = "0"
                    
                    # Debug: Show final branch metrics
                    if branch_commits and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Branch {branch_name} final: {len(branch_commits)} total commits ({owned_commits} owned, {inherited_commits} inherited), {branch_net_lines:+d} lines, git_diff: {git_diff_net:+d}")
                    
                    # Add to branch activity table with comprehensive metrics
                    tables['project_branch_activity'].append({
                        'group': group_name,
                        'project': project_name,
                        'branch': branch_name,
                        'commits_total': len(branch_commits),
                        'commits_unique': unique_commits_count,
                        'commits_owned': owned_commits,
                        'commits_inherited': inherited_commits,
                        'contributors': len(branch_contributors),
                        'net_lines': branch_net_lines,  # Current method (ownership-based)
                        'net_lines_git_diff': git_diff_net,  # Git diff method
                        'lines_indicator': lines_indicator,
                        'base_branch': base_branch,
                        'status': 'Active' if len(branch_commits) > 0 else 'Inactive'
                    })
                    
                    # Note: Don't accumulate branch commits to avoid double-counting shared commits
                
                # Get merge requests for project with client-side date filtering
                all_merge_requests = list(self.client._paginated_get(
                    f'projects/{project_id}/merge_requests',
                    created_after=start_date.isoformat(),
                    created_before=end_date.isoformat(),
                    scope='all'
                ))
                
                # Client-side date filtering for merge requests
                merge_requests = []
                for mr in all_merge_requests:
                    try:
                        created_at = datetime.fromisoformat(mr['created_at'].replace('Z', '+00:00'))
                        if start_date <= created_at <= end_date:
                            merge_requests.append(mr)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Failed to parse MR date for {mr.get('id', 'unknown')}: {e}")
                        continue
                
                logger.debug(f"Project {project_name}: {len(all_merge_requests)} total MRs, {len(merge_requests)} in date range")
                
                for mr in merge_requests:
                    author_username = mr.get('author', {}).get('username', 'Unknown')
                    if team_members and author_username not in team_members:
                        continue
                    project_contributors[author_username]['mrs'] += 1
                
                # Get issues for project
                issues = list(self.client._paginated_get(
                    f'projects/{project_id}/issues',
                    scope='all',
                    updated_after=start_date.isoformat(),
                    updated_before=end_date.isoformat()
                ))
                
                # Track issues opened and closed this week
                for issue in issues:
                    created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                    
                    # Issue opened this week
                    if start_date <= created_at <= end_date:
                        author = issue.get('author', {}).get('username', 'Unknown')
                        if not team_members or author in team_members:
                            project_contributors[author]['issues_opened'] += 1
                    
                    # Issue closed this week
                    if issue['state'] == 'closed' and issue.get('closed_at'):
                        closed_at = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00'))
                        if start_date <= closed_at <= end_date:
                            closer = None
                            if issue.get('closed_by'):
                                closer = issue['closed_by'].get('username', 'Unknown')
                            elif issue.get('assignee'):
                                closer = issue['assignee'].get('username', 'Unknown')
                            
                            if closer and (not team_members or closer in team_members):
                                project_contributors[closer]['issues_closed'] += 1
                
                # Add to contributor activity table
                if project_contributors:
                    for contributor, stats in project_contributors.items():
                        tables['project_contributor_activity'].append({
                            'group': group_name,
                            'project': project_name,
                            'contributor': contributor,
                            'commits': stats['commits'],
                            'mrs': stats['mrs'],
                            'net_lines': stats['net_lines'],
                            'issues_opened': stats['issues_opened'],
                            'issues_closed': stats['issues_closed'],
                            'total_activity': stats['commits'] + stats['mrs'] + stats['issues_opened'] + stats['issues_closed']
                        })
                else:
                    # Add inactive project entry
                    tables['project_contributor_activity'].append({
                        'group': group_name,
                        'project': project_name,
                        'contributor': '-',
                        'commits': 0,
                        'mrs': 0,
                        'net_lines': 0,
                        'issues_opened': 0,
                        'issues_closed': 0,
                        'total_activity': 0
                    })
                
                # Project-level summary logging
                if project_contributors:
                    total_project_commits = sum(stats['commits'] for stats in project_contributors.values())
                    logger.info(f"Project {project_name}: {total_project_commits} unique commits, {len(project_contributors)} contributors, {len(merge_requests)} MRs in date range")
                
            except Exception as e:
                logger.warning(f"Failed to analyze project {project.get('name', project_id)}: {e}")
        
        # Sort tables by activity (use new field names)
        tables['project_branch_activity'].sort(key=lambda x: x.get('commits_total', x.get('commits', 0)), reverse=True)
        tables['project_contributor_activity'].sort(key=lambda x: x['total_activity'], reverse=True)
        
        return tables