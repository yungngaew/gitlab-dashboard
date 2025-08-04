"""HTML email template generator for weekly productivity reports."""

import base64
from io import BytesIO
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WeeklyReportEmailTemplate:
    """Generate professional HTML email templates for weekly reports."""
    
    def __init__(self):
        """Initialize template generator."""
        self.chart_cache = {}
    
    def generate_html_email(
        self,
        report_data: Dict[str, Any],
        team_name: str = "Development Team",
        include_charts: bool = True
    ) -> str:
        """Generate complete HTML email for weekly report.
        
        Args:
            report_data: Report data from WeeklyProductivityReporter
            team_name: Name of the team for the report
            include_charts: Whether to include embedded charts
            
        Returns:
            Complete HTML email content
        """
        metadata = report_data.get('metadata', {})
        executive_summary = report_data.get('executive_summary', {})
        team_activity = report_data.get('team_activity', {})
        project_breakdown = report_data.get('project_breakdown', {})
        individual_metrics = report_data.get('individual_metrics', {})
        insights = report_data.get('insights_and_actions', {})
        
        # Generate charts if requested
        charts_html = ""
        if include_charts:
            charts_html = self._generate_charts_section(report_data)
        
        # Get detailed tables if available
        detailed_tables = report_data.get('detailed_tables', {})
        detailed_tables_html = ""
        if detailed_tables:
            detailed_tables_html = self._generate_detailed_tables_section(detailed_tables)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Productivity Report - {team_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        {self._get_email_styles()}
    </style>
</head>
<body>
    <div class="email-container">
        {self._generate_header(team_name, metadata)}
        {self._generate_executive_summary_section(executive_summary)}
        {self._generate_team_activity_section(team_activity, detailed_tables)}
        {detailed_tables_html}
        {self._generate_project_health_section(project_breakdown)}
        {self._generate_individual_highlights_section(individual_metrics)}
        {charts_html}
        {self._generate_insights_section(insights)}
        {self._generate_footer(metadata)}
    </div>
</body>
</html>
        """
        
        return html_content.strip()
    
    def _get_email_styles(self) -> str:
        """Get modern shadcn/ui-inspired CSS styles optimized for email clients."""
        return """
        /* Modern Design System Variables */
        :root {
            --background: #ffffff;
            --foreground: #0f172a;
            --card: #ffffff;
            --card-foreground: #0f172a;
            --primary: #0f172a;
            --primary-foreground: #f8fafc;
            --secondary: #f1f5f9;
            --secondary-foreground: #0f172a;
            --muted: #f8fafc;
            --muted-foreground: #64748b;
            --accent: #f1f5f9;
            --accent-foreground: #0f172a;
            --border: #e2e8f0;
            --input: #e2e8f0;
            --ring: #0f172a;
            --success: #22c55e;
            --success-foreground: #ffffff;
            --warning: #f59e0b;
            --warning-foreground: #ffffff;
            --destructive: #ef4444;
            --destructive-foreground: #ffffff;
        }
        
        /* Reset and base styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--foreground);
            background-color: #f8fafc;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .email-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: var(--background);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            overflow: hidden;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, #334155 100%);
            color: var(--primary-foreground);
            padding: 40px 32px;
            text-align: center;
            border-bottom: 1px solid var(--border);
        }
        
        .header h1 {
            font-size: 32px;
            margin-bottom: 12px;
            font-weight: 700;
            letter-spacing: -0.025em;
        }
        
        .header .period {
            font-size: 18px;
            opacity: 0.9;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        .header .generated {
            font-size: 14px;
            opacity: 0.75;
            font-weight: 400;
        }
        
        /* Sections */
        .section {
            padding: 32px;
            border-bottom: 1px solid var(--border);
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        .section-title {
            font-size: 24px;
            color: var(--foreground);
            margin-bottom: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            letter-spacing: -0.025em;
        }
        
        .section-title .icon {
            margin-right: 12px;
            font-size: 24px;
        }
        
        /* Metrics grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 20px;
            margin: 24px 0;
        }
        
        .metric-card {
            background: var(--card);
            border: 1px solid var(--border);
            padding: 24px 20px;
            border-radius: 8px;
            text-align: center;
            transition: box-shadow 0.2s ease-in-out;
        }
        
        .metric-card:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            color: var(--foreground);
            margin-bottom: 8px;
            letter-spacing: -0.025em;
        }
        
        .metric-label {
            font-size: 14px;
            color: var(--muted-foreground);
            font-weight: 500;
            text-transform: none;
            letter-spacing: 0;
        }
        
        .metric-change {
            font-size: 12px;
            margin-top: 8px;
            font-weight: 500;
        }
        
        .change-positive { color: var(--success); }
        .change-negative { color: var(--destructive); }
        .change-neutral { color: var(--muted-foreground); }
        
        /* Project health */
        .project-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }
        
        .project-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            transition: box-shadow 0.2s ease-in-out;
        }
        
        .project-card:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        .project-name {
            font-weight: 600;
            color: var(--foreground);
            margin-bottom: 12px;
            font-size: 16px;
        }
        
        .project-health {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .health-badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            text-transform: capitalize;
        }
        
        .health-healthy { 
            background: rgba(34, 197, 94, 0.1); 
            color: var(--success); 
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        .health-warning { 
            background: rgba(245, 158, 11, 0.1); 
            color: var(--warning); 
            border: 1px solid rgba(245, 158, 11, 0.2);
        }
        .health-critical { 
            background: rgba(239, 68, 68, 0.1); 
            color: var(--destructive); 
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        
        .project-metrics {
            font-size: 14px;
            color: var(--muted-foreground);
            font-weight: 500;
        }
        
        /* Contributors */
        .contributors-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }
        
        .contributor-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            transition: box-shadow 0.2s ease-in-out;
        }
        
        .contributor-card:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        .contributor-name {
            font-weight: 600;
            color: var(--foreground);
            margin-bottom: 8px;
            font-size: 15px;
        }
        
        .contributor-stats {
            font-size: 13px;
            color: var(--muted-foreground);
            font-weight: 500;
        }
        
        /* Insights */
        .insights-list {
            list-style: none;
            margin: 24px 0;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .insights-list li {
            background: var(--muted);
            padding: 16px 20px;
            border-radius: 8px;
            border-left: 4px solid var(--accent-foreground);
            font-size: 14px;
            font-weight: 500;
        }
        
        .priority-high {
            border-left-color: var(--destructive);
            background: rgba(239, 68, 68, 0.05);
            color: var(--destructive);
        }
        
        .priority-medium {
            border-left-color: var(--warning);
            background: rgba(245, 158, 11, 0.05);
            color: var(--warning);
        }
        
        .priority-low {
            border-left-color: var(--success);
            background: rgba(34, 197, 94, 0.05);
            color: var(--success);
        }
        
        /* Charts */
        .chart-container {
            text-align: center;
            margin: 24px 0;
        }
        
        .chart-image {
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        /* Activity Tables */
        .activity-table {
            width: 100%;
            border-collapse: collapse;
            margin: 24px 0;
            font-size: 14px;
            background: var(--card);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border);
        }
        
        .activity-table th {
            background: var(--muted);
            color: var(--foreground);
            font-weight: 600;
            padding: 16px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
            letter-spacing: 0.025em;
        }
        
        .activity-table td {
            padding: 14px 12px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            color: var(--foreground);
        }
        
        .activity-table tr:hover {
            background-color: var(--muted);
        }
        
        .activity-table tr:last-child td {
            border-bottom: none;
        }
        
        .activity-table .status-active {
            color: var(--success);
            font-weight: 600;
        }
        
        .activity-table .status-inactive {
            color: var(--destructive);
            font-weight: 600;
        }
        
        .activity-table .lines-positive {
            color: var(--success);
            font-weight: 600;
        }
        
        .activity-table .lines-negative {
            color: var(--destructive);
            font-weight: 600;
        }
        
        .inactive-summary {
            background: rgba(239, 68, 68, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin: 16px 0;
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-left: 4px solid var(--destructive);
        }
        
        .inactive-group {
            margin-bottom: 16px;
        }
        
        .inactive-group h5 {
            color: var(--destructive);
            margin: 0 0 8px 0;
            font-size: 16px;
            font-weight: 600;
        }
        
        .inactive-projects {
            color: var(--muted-foreground);
            font-size: 14px;
            line-height: 1.5;
            font-weight: 500;
        }
        
        /* Footer */
        .footer {
            background: var(--muted);
            padding: 32px;
            text-align: center;
            font-size: 14px;
            color: var(--muted-foreground);
            border-top: 1px solid var(--border);
        }
        
        /* Responsive */
        @media (max-width: 600px) {
            .email-container {
                margin: 0;
                box-shadow: none;
                border-radius: 0;
            }
            
            .header, .section {
                padding: 24px 20px;
            }
            
            .section-title {
                font-size: 20px;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
                gap: 16px;
            }
            
            .project-grid,
            .contributors-list {
                grid-template-columns: 1fr;
            }
            
            .activity-table {
                font-size: 12px;
            }
            
            .activity-table th,
            .activity-table td {
                padding: 12px 8px;
            }
            
            .metric-value {
                font-size: 28px;
            }
            
            .header h1 {
                font-size: 28px;
            }
            
            .header .period {
                font-size: 16px;
            }
        }
        """
    
    def _generate_header(self, team_name: str, metadata: Dict) -> str:
        """Generate modern email header section."""
        period_start = datetime.fromisoformat(metadata.get('period_start', '')).strftime('%B %d')
        period_end = datetime.fromisoformat(metadata.get('period_end', '')).strftime('%B %d, %Y')
        generated_at = datetime.fromisoformat(metadata.get('generated_at', '')).strftime('%Y-%m-%d %H:%M')
        
        return f"""
        <div class="header">
            <h1>📊 Weekly Productivity Report</h1>
            <div class="period">{team_name} • {period_start} - {period_end}</div>
            <div class="generated">Generated on {generated_at}</div>
        </div>
        """
    
    def _generate_executive_summary_section(self, summary: Dict) -> str:
        """Generate executive summary section."""
        key_metrics = summary.get('key_metrics', {})
        highlights = summary.get('highlights', [])
        concerns = summary.get('concerns', [])
        
        # Format metrics
        metrics_html = ""
        if key_metrics:
            metrics_html = f"""
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{key_metrics.get('total_commits', 0)}</div>
                    <div class="metric-label">Total Commits</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{key_metrics.get('total_merge_requests', 0)}</div>
                    <div class="metric-label">Merge Requests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{key_metrics.get('merge_rate', 0):.1f}%</div>
                    <div class="metric-label">Merge Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{key_metrics.get('active_contributors', 0)}</div>
                    <div class="metric-label">Contributors</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{key_metrics.get('healthy_projects', 0)}</div>
                    <div class="metric-label">Healthy Projects</div>
                </div>
            </div>
            """
        
        # Format highlights and concerns
        status_html = ""
        if highlights or concerns:
            status_html = "<div style='margin-top: 15px;'>"
            
            if highlights:
                status_html += "<div style='margin-bottom: 10px;'><strong>✨ Highlights:</strong><ul style='margin: 5px 0 0 20px;'>"
                for highlight in highlights[:3]:  # Limit to top 3
                    status_html += f"<li style='color: #28a745; margin-bottom: 3px;'>{highlight}</li>"
                status_html += "</ul></div>"
            
            if concerns:
                status_html += "<div><strong>⚠️ Attention Needed:</strong><ul style='margin: 5px 0 0 20px;'>"
                for concern in concerns[:3]:  # Limit to top 3
                    status_html += f"<li style='color: #dc3545; margin-bottom: 3px;'>{concern}</li>"
                status_html += "</ul></div>"
            
            status_html += "</div>"
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="icon">📋</span>
                Executive Summary
            </h2>
            {metrics_html}
            {status_html}
        </div>
        """
    
    def _generate_team_activity_section(self, activity: Dict, detailed_tables: Dict = None) -> str:
        """Generate team activity metrics section with aggregated data from detailed tables."""
        commits = activity.get('commits', {})
        merge_requests = activity.get('merge_requests', {})
        issues = activity.get('issues', {})
        
        # Use aggregated contributor data from detailed tables if available
        aggregated_contributors = None
        if detailed_tables and 'project_contributor_activity' in detailed_tables:
            aggregated_contributors = self._aggregate_contributors_from_tables(
                detailed_tables['project_contributor_activity']
            )
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="icon">👥</span>
                Team Activity
            </h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{commits.get('total', 0)}</div>
                    <div class="metric-label">Commits</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{merge_requests.get('opened', 0)}</div>
                    <div class="metric-label">MRs Opened</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{merge_requests.get('merged', 0)}</div>
                    <div class="metric-label">MRs Merged</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{issues.get('opened', 0)}</div>
                    <div class="metric-label">Issues Created</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{issues.get('closed', 0)}</div>
                    <div class="metric-label">Issues Resolved</div>
                </div>
            </div>
            
            <div style="margin-top: 15px;">
                <h4 style="color: #495057; margin-bottom: 8px;">Top Contributors This Week</h4>
                <div style="font-size: 13px;">
                    {self._format_top_contributors_from_tables(aggregated_contributors) if aggregated_contributors else self._format_top_contributors(commits.get('by_author', {}))}
                </div>
            </div>
        </div>
        """
    
    def _generate_project_health_section(self, breakdown: Dict) -> str:
        """Generate project health breakdown section."""
        projects = breakdown.get('projects', [])
        health_summary = breakdown.get('health_summary', {})
        
        # Sort projects by health status (critical first for attention)
        critical_projects = [p for p in projects if p['health_status'] == 'critical'][:3]
        healthy_projects = [p for p in projects if p['health_status'] == 'healthy'][:3]
        
        projects_html = ""
        if critical_projects:
            projects_html += "<h4 style='color: #dc3545; margin-bottom: 8px;'>🚨 Needs Attention</h4>"
            projects_html += "<div class='project-grid'>"
            for project in critical_projects:
                projects_html += self._format_project_card(project)
            projects_html += "</div>"
        
        if healthy_projects:
            projects_html += "<h4 style='color: #28a745; margin: 15px 0 8px 0;'>💚 Performing Well</h4>"
            projects_html += "<div class='project-grid'>"
            for project in healthy_projects:
                projects_html += self._format_project_card(project)
            projects_html += "</div>"
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="icon">🏥</span>
                Project Health
            </h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{health_summary.get('healthy', 0)}</div>
                    <div class="metric-label">Healthy</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{health_summary.get('warning', 0)}</div>
                    <div class="metric-label">Warning</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{health_summary.get('critical', 0)}</div>
                    <div class="metric-label">Critical</div>
                </div>
            </div>
            {projects_html}
        </div>
        """
    
    def _generate_individual_highlights_section(self, individual_metrics: Dict) -> str:
        """Generate individual contributor highlights section."""
        contributors = individual_metrics.get('contributors', {})
        team_stats = individual_metrics.get('team_stats', {})
        
        # Get top performers
        top_commits = max(contributors.items(), key=lambda x: x[1]['commits'], default=(None, {}))
        top_productivity = max(contributors.items(), key=lambda x: x[1]['productivity_score'], default=(None, {}))
        top_collaboration = max(contributors.items(), key=lambda x: x[1]['collaboration_score'], default=(None, {}))
        
        highlights_html = ""
        if top_commits[0]:
            highlights_html += f"""
            <div style="margin-bottom: 15px;">
                <h4 style="color: #495057; margin-bottom: 8px;">🌟 Team Highlights</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; font-size: 13px;">
                    <div style="margin-bottom: 5px;"><strong>Most Active:</strong> {top_commits[0]} ({top_commits[1]['commits']} commits)</div>
                    <div style="margin-bottom: 5px;"><strong>Top Productivity:</strong> {top_productivity[0]} (Score: {top_productivity[1]['productivity_score']:.1f})</div>
                    <div><strong>Best Collaborator:</strong> {top_collaboration[0]} (Score: {top_collaboration[1]['collaboration_score']:.1f})</div>
                </div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="icon">👤</span>
                Team Performance
            </h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{team_stats.get('total_contributors', 0)}</div>
                    <div class="metric-label">Active Contributors</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{team_stats.get('avg_commits', 0):.1f}</div>
                    <div class="metric-label">Avg Commits</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{team_stats.get('avg_productivity', 0):.1f}</div>
                    <div class="metric-label">Avg Productivity</div>
                </div>
            </div>
            {highlights_html}
        </div>
        """
    
    def _generate_charts_section(self, report_data: Dict) -> str:
        """Generate charts section with embedded chart images."""
        try:
            # Try to generate charts using matplotlib
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime, timedelta
            
            charts_html = '<div class="section"><h2 class="section-title"><span class="icon">📊</span>Visual Analytics</h2>'
            
            # Commit activity chart
            team_activity = report_data.get('team_activity', {})
            commits_by_day = team_activity.get('commits', {}).get('by_day', {})
            
            if commits_by_day:
                chart_html = self._create_commits_chart(commits_by_day)
                if chart_html:
                    charts_html += chart_html
            
            charts_html += '</div>'
            return charts_html
            
        except ImportError:
            # Fallback: text-based charts
            return self._generate_text_charts_section(report_data)
    
    def _create_commits_chart(self, commits_by_day: Dict) -> str:
        """Create embedded commit activity chart."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime
            
            # Prepare data
            dates = []
            commits = []
            for date_str, count in sorted(commits_by_day.items()):
                dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
                commits.append(count)
            
            if not dates:
                return ""
            
            # Create chart
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(dates, commits, marker='o', linewidth=2, markersize=6, color='#667eea')
            ax.fill_between(dates, commits, alpha=0.3, color='#667eea')
            
            ax.set_title('Daily Commit Activity', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Date', fontsize=10)
            ax.set_ylabel('Commits', fontsize=10)
            ax.grid(True, alpha=0.3)
            
            # Format dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f'''
            <div class="chart-container">
                <img src="data:image/png;base64,{chart_base64}" alt="Daily Commit Activity" class="chart-image">
            </div>
            '''
            
        except Exception as e:
            logger.warning(f"Failed to generate commits chart: {e}")
            return ""
    
    def _generate_text_charts_section(self, report_data: Dict) -> str:
        """Generate text-based charts as fallback."""
        team_activity = report_data.get('team_activity', {})
        commits_by_day = team_activity.get('commits', {}).get('by_day', {})
        
        if not commits_by_day:
            return ""
        
        # Create simple ASCII chart
        max_commits = max(commits_by_day.values()) if commits_by_day else 1
        chart_html = '<div class="section"><h2 class="section-title"><span class="icon">📊</span>Activity Trends</h2>'
        chart_html += '<div style="font-family: monospace; font-size: 12px; background: #f8f9fa; padding: 15px; border-radius: 6px; overflow-x: auto;">'
        
        for date_str, count in sorted(commits_by_day.items())[-7:]:  # Last 7 days
            bar_length = int((count / max_commits) * 20) if max_commits > 0 else 0
            bar = '█' * bar_length + '░' * (20 - bar_length)
            chart_html += f'{date_str}: {bar} {count}<br>'
        
        chart_html += '</div></div>'
        return chart_html
    
    def _generate_insights_section(self, insights: Dict) -> str:
        """Generate insights and recommendations section."""
        actions = insights.get('recommended_actions', [])
        focus_areas = insights.get('team_focus_areas', [])
        coaching = insights.get('individual_coaching', [])
        
        content_html = ""
        
        if actions:
            content_html += "<h4 style='color: #495057; margin-bottom: 8px;'>🎯 Recommended Actions</h4>"
            content_html += "<ul class='insights-list'>"
            for action in actions[:3]:  # Top 3 actions
                priority_class = f"priority-{action.get('priority', 'medium')}"
                content_html += f"<li class='{priority_class}'>{action.get('action', 'Action needed')}</li>"
            content_html += "</ul>"
        
        if focus_areas:
            content_html += "<h4 style='color: #495057; margin: 15px 0 8px 0;'>🎯 Team Focus Areas</h4>"
            content_html += "<ul style='margin: 5px 0 0 20px; font-size: 13px;'>"
            for area in focus_areas[:3]:
                content_html += f"<li style='margin-bottom: 5px;'>{area}</li>"
            content_html += "</ul>"
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="icon">💡</span>
                Insights & Next Steps
            </h2>
            {content_html}
        </div>
        """
    
    def _generate_footer(self, metadata: Dict) -> str:
        """Generate email footer."""
        return """
        <div class="footer">
            <p>This report was automatically generated by GitLab Tools.</p>
            <p>For questions or feedback, please contact your team lead.</p>
        </div>
        """
    
    def _format_top_contributors(self, by_author: Dict) -> str:
        """Format top contributors list from team activity data."""
        if not by_author:
            return "<em>No activity this week</em>"
        
        sorted_authors = sorted(by_author.items(), key=lambda x: x[1], reverse=True)[:5]
        result = ""
        for author, commits in sorted_authors:
            result += f"<div style='margin-bottom: 3px;'><strong>{author}</strong>: {commits} commits</div>"
        
        return result
    
    def _format_top_contributors_from_tables(self, aggregated_contributors: Dict) -> str:
        """Format top contributors list from aggregated detailed table data."""
        if not aggregated_contributors:
            return "<em>No activity this week</em>"
        
        # Sort by total commits
        sorted_contributors = sorted(
            aggregated_contributors.items(), 
            key=lambda x: x[1]['commits'], 
            reverse=True
        )[:5]
        
        result = ""
        for contributor, data in sorted_contributors:
            commits = data['commits']
            result += f"<div style='margin-bottom: 3px;'><strong>{contributor}</strong>: {commits} commits</div>"
        
        return result
    
    def _aggregate_contributors_from_tables(self, contrib_data: List[Dict]) -> Dict[str, Dict]:
        """Aggregate contributor data from detailed tables by contributor name."""
        aggregated = {}
        
        for item in contrib_data:
            contributor = item['contributor']
            if contributor == '-':
                continue
                
            if contributor not in aggregated:
                aggregated[contributor] = {
                    'commits': 0,
                    'mrs': 0,
                    'net_lines': 0,
                    'issues_opened': 0,
                    'issues_closed': 0,
                    'total_activity': 0
                }
            
            # Sum up all activities for this contributor
            aggregated[contributor]['commits'] += item['commits']
            aggregated[contributor]['mrs'] += item['mrs']
            aggregated[contributor]['net_lines'] += item['net_lines']
            aggregated[contributor]['issues_opened'] += item['issues_opened']
            aggregated[contributor]['issues_closed'] += item['issues_closed']
            aggregated[contributor]['total_activity'] += item['total_activity']
        
        return aggregated
    
    def _format_project_card(self, project: Dict) -> str:
        """Format individual project card."""
        health_class = f"health-{project['health_status']}"
        metrics = project.get('metrics', {})
        
        return f"""
        <div class="project-card">
            <div class="project-name">{project['name']}</div>
            <div class="project-health">
                <span class="health-badge {health_class}">{project['health_status'].title()}</span>
                <span style="font-size: 11px; color: #6c757d;">Score: {project['health_score']}</span>
            </div>
            <div class="project-metrics">
                {metrics.get('commits_this_week', 0)} commits • 
                {metrics.get('open_issues', 0)} open issues
            </div>
        </div>
        """
    
    def _generate_detailed_tables_section(self, tables: Dict[str, List[Dict]]) -> str:
        """Generate detailed activity tables section for email."""
        branch_data = tables.get('project_branch_activity', [])
        contrib_data = tables.get('project_contributor_activity', [])
        
        # Separate active and inactive data
        active_branches = [item for item in branch_data if item.get('commits_total', item.get('commits', 0)) > 0]
        inactive_branches = [item for item in branch_data if item.get('commits_total', item.get('commits', 0)) == 0]
        active_contribs = [item for item in contrib_data if item['commits'] > 0 or item['mrs'] > 0 or item['net_lines'] != 0]
        inactive_contribs = [item for item in contrib_data if item['commits'] == 0 and item['mrs'] == 0 and item['net_lines'] == 0]
        
        # Sort active data
        active_branches.sort(key=lambda x: (x.get('commits_total', x.get('commits', 0)), x['contributors'], x['net_lines']), reverse=True)
        active_contribs.sort(key=lambda x: (x['contributor'], -(x['commits'] + x['mrs'])))
        
        content_html = ""
        
        # Active Projects & Branches Table
        if active_branches:
            content_html += "<h3 style='color: #28a745; margin: 20px 0 10px 0; font-size: 18px;'>🟢 Active Projects & Branches</h3>"
            content_html += "<table class='activity-table'>"
            content_html += """
            <thead>
                <tr>
                    <th>Group</th>
                    <th>Project</th>
                    <th>Branch</th>
                    <th>Commits</th>
                    <th>Contributors</th>
                    <th>Lines±</th>
                </tr>
            </thead>
            <tbody>
            """
            
            # Limit to top 15 for email
            for item in active_branches[:15]:
                net_lines = item['net_lines']
                lines_str = f"+{net_lines}" if net_lines > 0 else str(net_lines)
                lines_class = "lines-positive" if net_lines > 0 else "lines-negative"
                
                content_html += f"""
                <tr>
                    <td>{item['group'][:12]}</td>
                    <td>{item['project'][:18]}</td>
                    <td>{item['branch'][:10]}</td>
                    <td style="text-align: center;">{item.get('commits_total', item.get('commits', 0))}</td>
                    <td style="text-align: center;">{item['contributors']}</td>
                    <td style="text-align: center;" class="{lines_class}">{lines_str}</td>
                </tr>
                """
            
            content_html += "</tbody></table>"
            
            if len(active_branches) > 15:
                content_html += f"<p style='font-size: 12px; color: #6c757d; margin: 5px 0;'>... and {len(active_branches) - 15} more active branches</p>"
        
        # Active Contributors by Project Table
        if active_contribs:
            content_html += "<h3 style='color: #007bff; margin: 25px 0 10px 0; font-size: 18px;'>👥 Active Contributors</h3>"
            content_html += "<table class='activity-table'>"
            content_html += """
            <thead>
                <tr>
                    <th>Contributor</th>
                    <th>Project</th>
                    <th>Group</th>
                    <th>Commits</th>
                    <th>MRs</th>
                    <th>Lines±</th>
                    <th>Issues±</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
            """
            
            # Limit to top 20 for email
            for item in active_contribs[:20]:
                net_lines = item['net_lines']
                lines_str = f"+{net_lines}" if net_lines > 0 else str(net_lines)
                lines_class = "lines-positive" if net_lines > 0 else "lines-negative"
                
                issues_opened = item['issues_opened']
                issues_closed = item['issues_closed']
                if issues_opened > 0 or issues_closed > 0:
                    issues_str = f"+{issues_opened}/-{issues_closed}"
                else:
                    issues_str = "0"
                
                content_html += f"""
                <tr>
                    <td>{item['contributor'][:12] if item['contributor'] != '-' else '-'}</td>
                    <td>{item['project'][:15]}</td>
                    <td>{item['group'][:12]}</td>
                    <td style="text-align: center;">{item['commits']}</td>
                    <td style="text-align: center;">{item['mrs']}</td>
                    <td style="text-align: center;" class="{lines_class}">{lines_str}</td>
                    <td style="text-align: center;">{issues_str}</td>
                    <td style="text-align: center;"><strong>{item['total_activity']}</strong></td>
                </tr>
                """
            
            content_html += "</tbody></table>"
            
            if len(active_contribs) > 20:
                content_html += f"<p style='font-size: 12px; color: #6c757d; margin: 5px 0;'>... and {len(active_contribs) - 20} more active contributors</p>"
        
        # Inactive Projects Summary
        if inactive_contribs:
            content_html += "<h3 style='color: #dc3545; margin: 25px 0 10px 0; font-size: 18px;'>🔴 Inactive Projects Summary</h3>"
            content_html += "<div class='inactive-summary'>"
            
            # Group inactive projects by group
            inactive_by_group = {}
            for item in inactive_contribs:
                group = item['group']
                if group not in inactive_by_group:
                    inactive_by_group[group] = set()
                inactive_by_group[group].add(item['project'])
            
            for group, projects in inactive_by_group.items():
                unique_projects = sorted(list(projects))
                content_html += f"""
                <div class="inactive-group">
                    <h5>{group}</h5>
                    <div class="inactive-projects">
                        {len(unique_projects)} inactive projects: {', '.join(unique_projects[:6])}
                        {'...' if len(unique_projects) > 6 else ''}
                    </div>
                </div>
                """
            
            content_html += "</div>"
        
        # Activity summary
        active_projects_count = len(set([(p['group'], p['project']) for p in active_contribs]))
        inactive_projects_count = len(set([(p['group'], p['project']) for p in inactive_contribs]))
        total_projects = active_projects_count + inactive_projects_count
        
        if total_projects > 0:
            content_html += f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #495057;">📊 Activity Summary</h4>
                <div style="display: flex; justify-content: space-around; font-size: 14px;">
                    <div><strong style="color: #28a745;">{active_projects_count}</strong> Active Projects ({active_projects_count/total_projects*100:.1f}%)</div>
                    <div><strong style="color: #dc3545;">{inactive_projects_count}</strong> Inactive Projects ({inactive_projects_count/total_projects*100:.1f}%)</div>
                </div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="icon">📊</span>
                Project Activity Details
            </h2>
            {content_html}
        </div>
        """ if content_html else ""