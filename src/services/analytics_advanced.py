"""Advanced analytics features for GitLab repositories."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import statistics
import json
from pathlib import Path

from ..api import GitLabClient
from ..utils.logger import OperationLogger

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """Advanced analytics features including trends, comparisons, and predictions."""
    
    def __init__(self, client: GitLabClient):
        """Initialize advanced analytics service.
        
        Args:
            client: GitLab API client
        """
        self.client = client
        self._cache = {}
        self._cache_expiry = {}
    
    def get_project_trends(
        self, 
        project_id: int, 
        days: int = 90,
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Analyze trends over time for a project.
        
        Args:
            project_id: Project ID
            days: Number of days to analyze
            metrics: List of metrics to analyze (commits, issues, mrs)
            
        Returns:
            Dictionary containing trend data
        """
        if metrics is None:
            metrics = ['commits', 'issues', 'merge_requests']
        
        with OperationLogger(logger, "trend analysis", project_id=project_id):
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            trends = {
                'project_id': project_id,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                },
                'metrics': {}
            }
            
            if 'commits' in metrics:
                trends['metrics']['commits'] = self._analyze_commit_trends(
                    project_id, start_date, end_date
                )
            
            if 'issues' in metrics:
                trends['metrics']['issues'] = self._analyze_issue_trends(
                    project_id, start_date, end_date
                )
            
            if 'merge_requests' in metrics:
                trends['metrics']['merge_requests'] = self._analyze_mr_trends(
                    project_id, start_date, end_date
                )
            
            # Calculate overall health score
            trends['health_score'] = self._calculate_health_score(trends['metrics'])
            
            return trends
    
    def _analyze_commit_trends(
        self, 
        project_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze commit trends over time."""
        try:
            # Get commits in date range
            commits = list(self.client._paginated_get(
                f'projects/{project_id}/repository/commits',
                params={
                    'since': start_date.isoformat(),
                    'until': end_date.isoformat()
                }
            ))
            
            # Group by week
            weeks = defaultdict(list)
            for commit in commits:
                commit_date = datetime.fromisoformat(
                    commit['created_at'].replace('Z', '+00:00')
                )
                week_key = commit_date.strftime('%Y-W%U')
                weeks[week_key].append(commit)
            
            # Calculate weekly metrics
            weekly_counts = []
            weekly_authors = []
            
            for week in sorted(weeks.keys()):
                weekly_counts.append(len(weeks[week]))
                authors = set(c['author_name'] for c in weeks[week])
                weekly_authors.append(len(authors))
            
            # Calculate trends
            if len(weekly_counts) > 1:
                commit_trend = self._calculate_trend(weekly_counts)
                author_trend = self._calculate_trend(weekly_authors)
            else:
                commit_trend = author_trend = 0
            
            return {
                'total_commits': len(commits),
                'weekly_average': statistics.mean(weekly_counts) if weekly_counts else 0,
                'weekly_counts': weekly_counts,
                'unique_authors': len(set(c['author_name'] for c in commits)),
                'commit_trend': commit_trend,  # Positive = increasing
                'author_trend': author_trend,
                'most_active_day': self._find_most_active_day(commits),
                'commit_messages_quality': self._analyze_commit_quality(commits)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze commit trends: {e}")
            return {}
    
    def _analyze_issue_trends(
        self, 
        project_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze issue trends over time."""
        try:
            # Get all issues
            all_issues = list(self.client._paginated_get(
                f'projects/{project_id}/issues',
                params={'scope': 'all'}
            ))
            
            # Filter by date range
            issues_in_range = []
            for issue in all_issues:
                created = datetime.fromisoformat(
                    issue['created_at'].replace('Z', '+00:00')
                )
                if start_date <= created <= end_date:
                    issues_in_range.append(issue)
            
            # Analyze resolution time
            resolution_times = []
            for issue in issues_in_range:
                if issue['state'] == 'closed' and issue.get('closed_at'):
                    created = datetime.fromisoformat(
                        issue['created_at'].replace('Z', '+00:00')
                    )
                    closed = datetime.fromisoformat(
                        issue['closed_at'].replace('Z', '+00:00')
                    )
                    resolution_times.append((closed - created).days)
            
            # Label analysis
            label_counts = Counter()
            for issue in issues_in_range:
                for label in issue.get('labels', []):
                    label_counts[label] += 1
            
            return {
                'total_created': len(issues_in_range),
                'open_issues': len([i for i in issues_in_range if i['state'] == 'opened']),
                'closed_issues': len([i for i in issues_in_range if i['state'] == 'closed']),
                'avg_resolution_days': statistics.mean(resolution_times) if resolution_times else None,
                'median_resolution_days': statistics.median(resolution_times) if resolution_times else None,
                'top_labels': label_counts.most_common(10),
                'issues_without_assignee': len([i for i in issues_in_range if not i.get('assignee')]),
                'overdue_issues': self._count_overdue_issues(issues_in_range)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze issue trends: {e}")
            return {}
    
    def _analyze_mr_trends(
        self, 
        project_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze merge request trends."""
        try:
            # Get all MRs
            all_mrs = list(self.client._paginated_get(
                f'projects/{project_id}/merge_requests',
                params={'scope': 'all'}
            ))
            
            # Filter by date range
            mrs_in_range = []
            for mr in all_mrs:
                created = datetime.fromisoformat(
                    mr['created_at'].replace('Z', '+00:00')
                )
                if start_date <= created <= end_date:
                    mrs_in_range.append(mr)
            
            # Analyze merge times
            merge_times = []
            for mr in mrs_in_range:
                if mr['state'] == 'merged' and mr.get('merged_at'):
                    created = datetime.fromisoformat(
                        mr['created_at'].replace('Z', '+00:00')
                    )
                    merged = datetime.fromisoformat(
                        mr['merged_at'].replace('Z', '+00:00')
                    )
                    merge_times.append((merged - created).total_seconds() / 3600)  # Hours
            
            return {
                'total_created': len(mrs_in_range),
                'merged': len([mr for mr in mrs_in_range if mr['state'] == 'merged']),
                'closed': len([mr for mr in mrs_in_range if mr['state'] == 'closed']),
                'open': len([mr for mr in mrs_in_range if mr['state'] == 'opened']),
                'avg_merge_hours': statistics.mean(merge_times) if merge_times else None,
                'median_merge_hours': statistics.median(merge_times) if merge_times else None,
                'merge_rate': len([mr for mr in mrs_in_range if mr['state'] == 'merged']) / len(mrs_in_range) if mrs_in_range else 0,
                'authors': len(set(mr['author']['username'] for mr in mrs_in_range if mr.get('author')))
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze MR trends: {e}")
            return {}
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend coefficient (-1 to 1, negative = decreasing)."""
        if len(values) < 2:
            return 0
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0
        
        slope = numerator / denominator
        
        # Normalize to -1 to 1 range
        max_slope = max(values) - min(values) if values else 1
        if max_slope == 0:
            return 0
        
        return max(-1, min(1, slope / max_slope))
    
    def _calculate_health_score(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall project health score."""
        scores = []
        factors = {}
        
        # Commit activity score
        if 'commits' in metrics and metrics['commits']:
            commit_data = metrics['commits']
            if commit_data.get('weekly_average', 0) > 0:
                # Good if consistent commits
                commit_score = min(100, commit_data['weekly_average'] * 10)
                if commit_data.get('commit_trend', 0) < -0.5:
                    commit_score *= 0.7  # Penalty for declining activity
                scores.append(commit_score)
                factors['commit_activity'] = commit_score
        
        # Issue resolution score
        if 'issues' in metrics and metrics['issues']:
            issue_data = metrics['issues']
            if issue_data.get('total_created', 0) > 0:
                # Good if issues are being resolved quickly
                resolution_score = 100
                if issue_data.get('avg_resolution_days'):
                    if issue_data['avg_resolution_days'] > 30:
                        resolution_score = 50
                    elif issue_data['avg_resolution_days'] > 14:
                        resolution_score = 75
                
                # Penalty for too many open issues
                open_ratio = issue_data.get('open_issues', 0) / issue_data['total_created']
                if open_ratio > 0.7:
                    resolution_score *= 0.7
                
                scores.append(resolution_score)
                factors['issue_resolution'] = resolution_score
        
        # MR efficiency score
        if 'merge_requests' in metrics and metrics['merge_requests']:
            mr_data = metrics['merge_requests']
            if mr_data.get('total_created', 0) > 0:
                # Good if MRs are merged quickly with high rate
                mr_score = mr_data.get('merge_rate', 0) * 100
                
                if mr_data.get('avg_merge_hours'):
                    if mr_data['avg_merge_hours'] < 24:
                        mr_score *= 1.2  # Bonus for quick merges
                    elif mr_data['avg_merge_hours'] > 168:  # 1 week
                        mr_score *= 0.8  # Penalty for slow merges
                
                scores.append(min(100, mr_score))
                factors['mr_efficiency'] = min(100, mr_score)
        
        overall_score = statistics.mean(scores) if scores else 0
        
        return {
            'score': round(overall_score, 1),
            'grade': self._score_to_grade(overall_score),
            'factors': factors,
            'recommendations': self._generate_recommendations(metrics, overall_score)
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _find_most_active_day(self, commits: List[Dict]) -> str:
        """Find the most active day of the week."""
        if not commits:
            return "N/A"
        
        day_counts = Counter()
        for commit in commits:
            commit_date = datetime.fromisoformat(
                commit['created_at'].replace('Z', '+00:00')
            )
            day_counts[commit_date.strftime('%A')] += 1
        
        return day_counts.most_common(1)[0][0] if day_counts else "N/A"
    
    def _analyze_commit_quality(self, commits: List[Dict]) -> Dict[str, Any]:
        """Analyze commit message quality."""
        if not commits:
            return {'score': 0, 'issues': []}
        
        issues = []
        good_commits = 0
        
        for commit in commits:
            message = commit.get('message', '')
            
            # Check for good practices
            if len(message) < 10:
                issues.append('very_short_messages')
            elif len(message.split('\n')[0]) > 72:
                issues.append('long_subject_lines')
            elif message[0].islower():
                issues.append('lowercase_start')
            else:
                good_commits += 1
        
        quality_score = (good_commits / len(commits)) * 100 if commits else 0
        
        return {
            'score': round(quality_score, 1),
            'issues': Counter(issues).most_common(3)
        }
    
    def _count_overdue_issues(self, issues: List[Dict]) -> int:
        """Count issues that are past their due date."""
        overdue = 0
        now = datetime.now(timezone.utc)
        
        for issue in issues:
            if issue['state'] == 'opened' and issue.get('due_date'):
                due_date = datetime.fromisoformat(issue['due_date'])
                if due_date < now:
                    overdue += 1
        
        return overdue
    
    def _generate_recommendations(self, metrics: Dict[str, Any], score: float) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        if score < 60:
            recommendations.append("⚠️ Project health needs attention")
        
        # Commit recommendations
        if 'commits' in metrics and metrics['commits']:
            commit_data = metrics['commits']
            if commit_data.get('commit_trend', 0) < -0.5:
                recommendations.append("📉 Commit activity is declining - consider reviewing team capacity")
            if commit_data.get('weekly_average', 0) < 1:
                recommendations.append("💤 Very low commit activity - project may be stale")
            if commit_data.get('unique_authors', 0) < 2:
                recommendations.append("👤 Low contributor diversity - consider involving more team members")
        
        # Issue recommendations
        if 'issues' in metrics and metrics['issues']:
            issue_data = metrics['issues']
            if issue_data.get('avg_resolution_days', 0) > 30:
                recommendations.append("🐌 Issues take too long to resolve - review triage process")
            if issue_data.get('issues_without_assignee', 0) > issue_data.get('total_created', 0) * 0.3:
                recommendations.append("👥 Many unassigned issues - improve issue assignment")
            if issue_data.get('overdue_issues', 0) > 0:
                recommendations.append(f"⏰ {issue_data['overdue_issues']} overdue issues need attention")
        
        # MR recommendations
        if 'merge_requests' in metrics and metrics['merge_requests']:
            mr_data = metrics['merge_requests']
            if mr_data.get('merge_rate', 0) < 0.7:
                recommendations.append("🚫 Low merge rate - review MR rejection reasons")
            if mr_data.get('avg_merge_hours', 0) > 168:  # 1 week
                recommendations.append("⏳ Slow MR turnaround - consider smaller MRs or more reviewers")
        
        return recommendations
    
    def compare_projects(
        self, 
        project_ids: List[int], 
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Compare multiple projects across various metrics.
        
        Args:
            project_ids: List of project IDs to compare
            metrics: Metrics to compare
            
        Returns:
            Comparison data
        """
        if metrics is None:
            metrics = ['commits', 'issues', 'merge_requests', 'contributors']
        
        comparison = {
            'projects': {},
            'rankings': defaultdict(list),
            'summary': {}
        }
        
        # Gather data for each project
        for project_id in project_ids:
            try:
                project = self.client.get_project(project_id)
                project_data = {
                    'name': project['name'],
                    'id': project_id,
                    'metrics': {}
                }
                
                # Get trends for last 30 days
                trends = self.get_project_trends(project_id, days=30, metrics=metrics)
                project_data['metrics'] = trends['metrics']
                project_data['health_score'] = trends['health_score']['score']
                
                comparison['projects'][project_id] = project_data
                
            except Exception as e:
                logger.error(f"Failed to get data for project {project_id}: {e}")
        
        # Calculate rankings
        if len(comparison['projects']) > 1:
            # Health score ranking
            health_scores = [
                (pid, data['health_score']) 
                for pid, data in comparison['projects'].items()
            ]
            health_scores.sort(key=lambda x: x[1], reverse=True)
            comparison['rankings']['health_score'] = health_scores
            
            # Activity ranking (by commits)
            commit_counts = [
                (pid, data['metrics'].get('commits', {}).get('total_commits', 0))
                for pid, data in comparison['projects'].items()
            ]
            commit_counts.sort(key=lambda x: x[1], reverse=True)
            comparison['rankings']['activity'] = commit_counts
        
        return comparison
    
    def generate_html_dashboard(
        self, 
        analytics_data: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """Generate an HTML dashboard from analytics data.
        
        Args:
            analytics_data: Analytics data from get_project_trends or compare_projects
            output_path: Optional path to save HTML file
            
        Returns:
            HTML content
        """
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>GitLab Analytics Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .metric-label {
            color: #666;
            margin-top: 5px;
        }
        .health-score {
            text-align: center;
            padding: 40px;
        }
        .health-score .score {
            font-size: 4em;
            font-weight: bold;
        }
        .grade-A { color: #22c55e; }
        .grade-B { color: #84cc16; }
        .grade-C { color: #eab308; }
        .grade-D { color: #f97316; }
        .grade-F { color: #ef4444; }
        .recommendations {
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }
        .recommendations h3 {
            margin-top: 0;
            color: #92400e;
        }
        .recommendations ul {
            margin: 0;
            padding-left: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GitLab Analytics Dashboard</h1>
            <p>Generated: {timestamp}</p>
        </div>
        
        {content}
    </div>
</body>
</html>
        """
        
        content = self._generate_dashboard_content(analytics_data)
        html = html_template.format(
            timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            content=content
        )
        
        if output_path:
            Path(output_path).write_text(html)
            logger.info(f"Dashboard saved to: {output_path}")
        
        return html
    
    def _generate_dashboard_content(self, data: Dict[str, Any]) -> str:
        """Generate the main content for the dashboard."""
        content_parts = []
        
        # Check if it's a single project or comparison
        if 'health_score' in data:
            # Single project dashboard
            content_parts.append(self._generate_project_dashboard(data))
        elif 'projects' in data:
            # Comparison dashboard
            content_parts.append(self._generate_comparison_dashboard(data))
        
        return '\n'.join(content_parts)
    
    def _generate_project_dashboard(self, data: Dict[str, Any]) -> str:
        """Generate dashboard for a single project."""
        parts = []
        
        # Health score
        health = data.get('health_score', {})
        parts.append(f"""
        <div class="metric-card health-score">
            <div class="score grade-{health.get('grade', 'F')}">{health.get('score', 0)}</div>
            <div class="metric-label">Health Score (Grade: {health.get('grade', 'F')})</div>
        </div>
        """)
        
        # Metrics grid
        parts.append('<div class="metrics-grid">')
        
        # Commits metrics
        if 'commits' in data.get('metrics', {}):
            commits = data['metrics']['commits']
            parts.append(f"""
            <div class="metric-card">
                <h3>Commit Activity</h3>
                <div class="metric-value">{commits.get('total_commits', 0)}</div>
                <div class="metric-label">Total Commits</div>
                <p>Weekly Average: {commits.get('weekly_average', 0):.1f}</p>
                <p>Unique Authors: {commits.get('unique_authors', 0)}</p>
                <p>Most Active Day: {commits.get('most_active_day', 'N/A')}</p>
            </div>
            """)
        
        # Issues metrics
        if 'issues' in data.get('metrics', {}):
            issues = data['metrics']['issues']
            parts.append(f"""
            <div class="metric-card">
                <h3>Issue Management</h3>
                <div class="metric-value">{issues.get('open_issues', 0)}</div>
                <div class="metric-label">Open Issues</div>
                <p>Total Created: {issues.get('total_created', 0)}</p>
                <p>Avg Resolution: {issues.get('avg_resolution_days', 'N/A')} days</p>
                <p>Overdue: {issues.get('overdue_issues', 0)}</p>
            </div>
            """)
        
        # MR metrics
        if 'merge_requests' in data.get('metrics', {}):
            mrs = data['metrics']['merge_requests']
            parts.append(f"""
            <div class="metric-card">
                <h3>Merge Requests</h3>
                <div class="metric-value">{mrs.get('merge_rate', 0)*100:.0f}%</div>
                <div class="metric-label">Merge Rate</div>
                <p>Total Created: {mrs.get('total_created', 0)}</p>
                <p>Avg Merge Time: {mrs.get('avg_merge_hours', 0):.1f} hours</p>
                <p>Active Authors: {mrs.get('authors', 0)}</p>
            </div>
            """)
        
        parts.append('</div>')
        
        # Recommendations
        if health.get('recommendations'):
            parts.append("""
            <div class="recommendations">
                <h3>Recommendations</h3>
                <ul>
            """)
            for rec in health['recommendations']:
                parts.append(f"<li>{rec}</li>")
            parts.append("</ul></div>")
        
        return '\n'.join(parts)
    
    def _generate_comparison_dashboard(self, data: Dict[str, Any]) -> str:
        """Generate comparison dashboard for multiple projects."""
        parts = []
        
        # Rankings table
        if 'rankings' in data and data['rankings']:
            parts.append("""
            <div class="metric-card">
                <h2>Project Rankings</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Project</th>
                            <th>Health Score</th>
                            <th>Activity</th>
                        </tr>
                    </thead>
                    <tbody>
            """)
            
            health_ranking = data['rankings'].get('health_score', [])
            for rank, (pid, score) in enumerate(health_ranking, 1):
                project = data['projects'].get(pid, {})
                parts.append(f"""
                <tr>
                    <td>{rank}</td>
                    <td>{project.get('name', f'Project {pid}')}</td>
                    <td>{score:.1f}</td>
                    <td>{project.get('metrics', {}).get('commits', {}).get('total_commits', 0)}</td>
                </tr>
                """)
            
            parts.append("</tbody></table></div>")
        
        return '\n'.join(parts)