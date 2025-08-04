#!/usr/bin/env python3
"""Generate and send weekly productivity reports for team syncs."""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import GitLabClient
from src.services.weekly_reports import WeeklyProductivityReporter
from src.services.email_service import WeeklyReportEmailSender
from src.templates.weekly_report_email import WeeklyReportEmailTemplate
from src.utils import Config, setup_logging, get_logger
from src.utils.logger import Colors

from src.services.analytics import GitLabAnalytics
from src.services.teams_service import TeamsWebhookService
from src.services.history_service import HistoryService

logger = get_logger(__name__)


def _format_number(value: int, show_sign: bool = False, compact: bool = False) -> str:
    """Format numbers in a compact, readable way."""
    if value == 0:
        return "0"
    
    # Compact formatting for large numbers
    if compact and abs(value) >= 1000:
        if abs(value) >= 1000000:
            formatted = f"{value/1000000:.1f}M"
        elif abs(value) >= 1000:
            formatted = f"{value/1000:.1f}k"
        else:
            formatted = str(value)
    else:
        formatted = str(value)
    
    # Add sign if requested
    if show_sign and value > 0:
        formatted = "+" + formatted
    
    return formatted


def _group_contributors_by_person(contrib_data: List[Dict]) -> List[Tuple[str, List[Dict]]]:
    """Group contributor data by person, sorting by total activity."""
    from collections import defaultdict
    
    groups = defaultdict(list)
    for item in contrib_data:
        contributor = item['contributor']
        groups[contributor].append(item)
    
    # Sort each person's projects by activity
    for contributor in groups:
        groups[contributor].sort(key=lambda x: x['total_activity'], reverse=True)
    
    # Sort contributors by total activity across all projects
    def get_total_activity(contributor_projects):
        return sum(p['total_activity'] for p in contributor_projects[1])
    
    sorted_groups = sorted(groups.items(), key=get_total_activity, reverse=True)
    return sorted_groups


def _format_table(headers: List[str], rows: List[List[str]], title: str = "", max_width: int = None) -> str:
    """Format data as a responsive table with optimized space usage."""
    if not rows:
        return f"\n{title}\nNo data available."
    
    # Get terminal width for responsive layout
    import shutil
    terminal_width = max_width or shutil.get_terminal_size().columns - 2
    
    # Calculate base column widths
    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Optimize column widths for terminal space
    total_width = sum(col_widths) + len(headers) * 3 + 1  # borders and padding
    
    if total_width > terminal_width:
        # Prioritize columns - numbers are compact, text fields need more space
        priority_map = {
            'group': 1, 'project': 4, 'contributor': 4, 'branch': 2,
            'commits': 0, 'total': 0, 'unique': 0, 'contributors': 0,
            'mrs': 0, 'lines±': 1, 'lines±(own)': 1, 'lines±(diff)': 1,
            'issues±': 1, 'total': 0
        }
        
        # Calculate available space and redistribute
        available_space = terminal_width - len(headers) * 3 - 1
        
        # Assign minimum widths first
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if any(x in header_lower for x in ['commits', 'total', 'unique', 'mrs', 'contributors']):
                col_widths[i] = min(col_widths[i], 7)  # Numbers don't need much space
            elif 'lines' in header_lower or 'issues' in header_lower:
                col_widths[i] = min(col_widths[i], 10)  # Formatted numbers
        
        # Redistribute remaining space to text columns
        used_space = sum(col_widths)
        remaining_space = available_space - used_space
        
        if remaining_space > 0:
            text_columns = [i for i, h in enumerate(headers) 
                          if h.lower() in ['group', 'project', 'contributor', 'branch']]
            if text_columns:
                extra_per_col = remaining_space // len(text_columns)
                for i in text_columns:
                    col_widths[i] += extra_per_col
    
    # Create separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    # Format header
    header_row = "|" + "|".join(f" {headers[i]:<{col_widths[i]}} " for i in range(len(headers))) + "|"
    
    # Format rows with intelligent truncation
    formatted_rows = []
    for row in rows:
        formatted_cells = []
        for i, cell in enumerate(row):
            cell_str = str(cell)
            if len(cell_str) > col_widths[i]:
                # Smart truncation based on content type
                header_name = headers[i].lower()
                if header_name in ['project', 'contributor']:
                    # Keep the end for projects/contributors (more distinctive)
                    cell_str = ".." + cell_str[-(col_widths[i]-2):]
                else:
                    # Standard truncation for other fields
                    cell_str = cell_str[:col_widths[i]-2] + ".."
            formatted_cells.append(f" {cell_str:<{col_widths[i]}} ")
        
        formatted_row = "|" + "|".join(formatted_cells) + "|"
        formatted_rows.append(formatted_row)
    
    # Combine everything
    result = []
    if title:
        result.append(f"\n{title}")
    result.append(separator)
    result.append(header_row)
    result.append(separator)
    result.extend(formatted_rows)
    result.append(separator)
    
    return "\n".join(result)


def _display_detailed_tables(tables: Dict[str, List[Dict]], max_width: int = None, max_projects: int = 35, max_contributors: int = 25, compact: bool = False):
    """Display detailed activity tables separated by active/inactive."""
    
    # Project Branch Activity Table
    if tables.get('project_branch_activity'):
        branch_data = tables['project_branch_activity']
        
        # Separate active and inactive branches (use commits_total for backwards compatibility)
        active_branches = [item for item in branch_data if item.get('commits_total', item.get('commits', 0)) > 0]
        inactive_branches = [item for item in branch_data if item.get('commits_total', item.get('commits', 0)) == 0]
        
        # Sort active branches by total activity (commits + contributors)
        active_branches.sort(key=lambda x: (
            x.get('commits_total', x.get('commits', 0)), 
            x['contributors'], 
            x.get('net_lines', 0)
        ), reverse=True)
        
        # Optimized headers - removed status column, shortened names
        headers = ["Group", "Project", "Branch", "Total", "Unique", "Contributors", "Lines±(Own)", "Lines±(Diff)"]
        
        # Display Active Projects
        if active_branches:
            print(f"\n{Colors.BOLD}📊 ACTIVE Projects & Branch Activity (Top {min(len(active_branches), max_projects)}){Colors.RESET}")
            active_rows = []
            
            for item in active_branches[:max_projects]:
                # Backwards compatibility for field names
                total_commits = item.get('commits_total', item.get('commits', 0))
                unique_commits = item.get('commits_unique', 0)
                
                # Line changes with ownership method
                net_lines_own = item.get('net_lines', 0)
                lines_own_str = _format_number(net_lines_own, show_sign=True, compact=True)
                
                # Line changes with git diff method
                net_lines_diff = item.get('net_lines_git_diff', 0)
                if net_lines_diff == 0 and total_commits > 0:
                    lines_diff_str = "N/A"
                else:
                    lines_diff_str = _format_number(net_lines_diff, show_sign=True, compact=True)
                
                active_rows.append([
                    item['group'],  # Let table formatter handle truncation
                    item['project'],  # Let table formatter handle truncation
                    item['branch'],   # Let table formatter handle truncation
                    str(total_commits),
                    str(unique_commits),
                    str(item['contributors']),
                    lines_own_str,
                    lines_diff_str
                ])
            
            active_table = _format_table(headers, active_rows, max_width=max_width)
            print(active_table)
            
            # Compact legend (only show if not in compact mode)
            if not compact:
                print(f"\n{Colors.BOLD}📖{Colors.RESET} Total=all commits | Unique=branch-only | Own=ownership method | Diff=git diff method")
            
            if len(active_branches) > max_projects:
                print(f"{Colors.YELLOW}... and {len(active_branches) - max_projects} more active branches{Colors.RESET}")
        
        # Display Inactive Projects as compact summary
        if inactive_branches:
            print(f"\n{Colors.BOLD}📋 INACTIVE Projects ({len(inactive_branches)} projects with no commits){Colors.RESET}")
            
            # Group by group for more compact display
            inactive_by_group = {}
            for item in inactive_branches:
                group = item['group']
                if group not in inactive_by_group:
                    inactive_by_group[group] = []
                inactive_by_group[group].append(item['project'])
            
            for group, projects in inactive_by_group.items():
                unique_projects = sorted(list(set(projects)))
                if len(unique_projects) <= 8:
                    projects_str = ', '.join(unique_projects)
                else:
                    projects_str = f"{', '.join(unique_projects[:8])} ... (+{len(unique_projects)-8} more)"
                print(f"  {Colors.RED}{group}{Colors.RESET}: {projects_str}")
    
    # Project Contributor Activity Table
    if tables.get('project_contributor_activity'):
        contrib_data = tables['project_contributor_activity']
        
        # Separate active and inactive projects - filter out pure issue-only activity
        active_contribs = [item for item in contrib_data if item['commits'] > 0 or item['mrs'] > 0 or item['net_lines'] != 0]
        inactive_contribs = [item for item in contrib_data if item['commits'] == 0 and item['mrs'] == 0 and item['net_lines'] == 0]
        
        # Sort by contributor name (primary), then by commits+MRs within each contributor (secondary)
        active_contribs.sort(key=lambda x: (x['contributor'], -(x['commits'] + x['mrs'])))
        
        # Group contributors by person for more compact display
        contributor_groups = _group_contributors_by_person(active_contribs)
        
        if contributor_groups:
            print(f"\n{Colors.BOLD}👥 ACTIVE Contributors ({len(contributor_groups)} people across {len(active_contribs)} projects){Colors.RESET}")
            
            # Use command-line option for max contributors (will be passed as a global)
            max_contributors = getattr(args, 'max_contributors', 25) if 'args' in globals() else 25
            
            # Display grouped contributors
            for i, (contributor, projects_data) in enumerate(contributor_groups[:max_contributors], 1):
                if contributor == '-':
                    continue
                    
                # Calculate totals for this contributor
                total_commits = sum(p['commits'] for p in projects_data)
                total_mrs = sum(p['mrs'] for p in projects_data)
                total_lines = sum(p['net_lines'] for p in projects_data)
                total_activity = sum(p['total_activity'] for p in projects_data)
                
                # Format contributor summary line
                lines_str = _format_number(total_lines, show_sign=True)
                print(f"  {Colors.BOLD}{i:2d}. {contributor}{Colors.RESET} → {total_commits} commits, {total_mrs} MRs, {lines_str} lines")
                
                # Show projects for this contributor (if multiple)
                if len(projects_data) > 1:
                    for proj in projects_data[:3]:  # Show top 3 projects
                        proj_lines = _format_number(proj['net_lines'], show_sign=True, compact=True)
                        print(f"      ├─ {proj['project'][:25]} ({proj['group'][:12]}): {proj['commits']}c, {proj['mrs']}mr, {proj_lines}")
                    if len(projects_data) > 3:
                        remaining = len(projects_data) - 3
                        print(f"      └─ ... and {remaining} more project{'s' if remaining > 1 else ''}")
                else:
                    # Single project - show inline
                    proj = projects_data[0]
                    print(f"      └─ {proj['project']} ({proj['group']})")
            
            if len(contributor_groups) > max_contributors:
                print(f"\n{Colors.YELLOW}... and {len(contributor_groups) - max_contributors} more contributors{Colors.RESET}")
        
        # Inactive projects already handled above in branch section
        
        # Enhanced Summary stats
        active_projects = len(set([(p['group'], p['project']) for p in active_contribs]))
        inactive_projects = len(set([(p['group'], p['project']) for p in inactive_contribs]))
        total_projects = active_projects + inactive_projects
        
        # Compact activity summary
        activity_pct = (active_projects/total_projects*100) if total_projects > 0 else 0
        print(f"\n{Colors.BOLD}📊 Summary:{Colors.RESET} {Colors.GREEN}{active_projects} active{Colors.RESET} | {Colors.RED}{inactive_projects} inactive{Colors.RESET} ({activity_pct:.0f}% active)")
        
        if contributor_groups:
            top_contributor = contributor_groups[0]
            top_projects = sum(p['total_activity'] for p in top_contributor[1])
            print(f"🏆 Top contributor: {top_contributor[0]} (Activity score: {top_projects})")


def parse_groups(groups_arg: str) -> List[int]:
    """Parse group IDs from command line argument.
    
    Args:
        groups_arg: Comma-separated group IDs or names
        
    Returns:
        List of group IDs
    """
    if not groups_arg:
        return []
    
    group_items = [item.strip() for item in groups_arg.split(',')]
    group_ids = []
    
    for item in group_items:
        if item.isdigit():
            group_ids.append(int(item))
        else:
            # TODO: Look up group by name
            logger.warning(f"Group name lookup not implemented yet: {item}")
    
    return group_ids


def parse_team_members(members_arg: str) -> List[str]:
    """Parse team member list from command line argument.
    
    Args:
        members_arg: Comma-separated usernames or emails
        
    Returns:
        List of team member identifiers
    """
    if not members_arg:
        return []
    
    return [member.strip() for member in members_arg.split(',')]


def parse_recipients(recipients_arg: str) -> List[str]:
    """Parse email recipients from command line argument.
    
    Args:
        recipients_arg: Comma-separated email addresses
        
    Returns:
        List of email addresses
    """
    if not recipients_arg:
        return []
    
    return [email.strip() for email in recipients_arg.split(',')]


def save_report_to_file(report_data: Dict[str, Any], output_path: Path, format_type: str) -> None:
    """Save report data to file.
    
    Args:
        report_data: Report data to save
        output_path: Output file path
        format_type: Format (json, html, markdown)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format_type == 'json':
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        logger.info(f"Report saved as JSON: {output_path}")
    
    elif format_type == 'html':
        template = WeeklyReportEmailTemplate()
        html_content = template.generate_html_email(report_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Report saved as HTML: {output_path}")
    
    elif format_type == 'markdown':
        markdown_content = generate_markdown_report(report_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logger.info(f"Report saved as Markdown: {output_path}")


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """Generate markdown version of the report.
    
    Args:
        report_data: Report data
        
    Returns:
        Markdown content
    """
    metadata = report_data.get('metadata', {})
    executive_summary = report_data.get('executive_summary', {})
    team_activity = report_data.get('team_activity', {})
    project_breakdown = report_data.get('project_breakdown', {})
    individual_metrics = report_data.get('individual_metrics', {})
    insights = report_data.get('insights_and_actions', {})
    
    # Format dates
    start_date = datetime.fromisoformat(metadata.get('period_start', '')).strftime('%B %d')
    end_date = datetime.fromisoformat(metadata.get('period_end', '')).strftime('%B %d, %Y')
    generated_at = datetime.fromisoformat(metadata.get('generated_at', '')).strftime('%Y-%m-%d %H:%M')
    
    markdown = f"""# Weekly Productivity Report

**Period:** {start_date} - {end_date}  
**Generated:** {generated_at}  
**Groups Analyzed:** {metadata.get('groups_analyzed', 0)}  
**Team Size:** {metadata.get('team_size', 'All contributors')}

## Executive Summary

### Key Metrics
"""
    
    # Key metrics
    key_metrics = executive_summary.get('key_metrics', {})
    if key_metrics:
        markdown += f"""
| Metric | Value |
|--------|-------|
| Total Commits | {key_metrics.get('total_commits', 0)} |
| Total Merge Requests | {key_metrics.get('total_merge_requests', 0)} |
| Merge Rate | {key_metrics.get('merge_rate', 0):.1f}% |
| Active Contributors | {key_metrics.get('active_contributors', 0)} |
| Healthy Projects | {key_metrics.get('healthy_projects', 0)} |
| Projects Needing Attention | {key_metrics.get('projects_needing_attention', 0)} |
"""
    
    # Highlights and concerns
    highlights = executive_summary.get('highlights', [])
    concerns = executive_summary.get('concerns', [])
    
    if highlights:
        markdown += "\n### ✨ Highlights\n"
        for highlight in highlights:
            markdown += f"- {highlight}\n"
    
    if concerns:
        markdown += "\n### ⚠️ Attention Needed\n"
        for concern in concerns:
            markdown += f"- {concern}\n"
    
    # Team Activity
    markdown += "\n## Team Activity\n"
    commits = team_activity.get('commits', {})
    merge_requests = team_activity.get('merge_requests', {})
    issues = team_activity.get('issues', {})
    
    markdown += f"""
| Activity | Count |
|----------|-------|
| Commits | {commits.get('total', 0)} |
| Merge Requests Opened | {merge_requests.get('opened', 0)} |
| Merge Requests Merged | {merge_requests.get('merged', 0)} |
| Issues Created | {issues.get('opened', 0)} |
| Issues Resolved | {issues.get('closed', 0)} |
"""
    
    # Top contributors
    by_author = commits.get('by_author', {})
    if by_author:
        markdown += "\n### Top Contributors\n"
        for author, count in sorted(by_author.items(), key=lambda x: x[1], reverse=True)[:5]:
            markdown += f"- **{author}**: {count} commits\n"
    
    # Project Health
    markdown += "\n## Project Health\n"
    health_summary = project_breakdown.get('health_summary', {})
    
    markdown += f"""
| Status | Count |
|--------|-------|
| Healthy | {health_summary.get('healthy', 0)} |
| Warning | {health_summary.get('warning', 0)} |
| Critical | {health_summary.get('critical', 0)} |
"""
    
    # Critical projects
    projects = project_breakdown.get('projects', [])
    critical_projects = [p for p in projects if p['health_status'] == 'critical']
    
    if critical_projects:
        markdown += "\n### 🚨 Projects Needing Attention\n"
        for project in critical_projects[:5]:
            metrics = project.get('metrics', {})
            markdown += f"- **{project['name']}** (Score: {project['health_score']})\n"
            markdown += f"  - {metrics.get('commits_this_week', 0)} commits this week\n"
            markdown += f"  - {metrics.get('open_issues', 0)} open issues\n"
            if project.get('recommendations'):
                markdown += f"  - Recommendations: {', '.join(project['recommendations'][:2])}\n"
    
    # Team Performance
    markdown += "\n## Team Performance\n"
    team_stats = individual_metrics.get('team_stats', {})
    
    if team_stats:
        markdown += f"""
| Metric | Value |
|--------|-------|
| Active Contributors | {team_stats.get('total_contributors', 0)} |
| Average Commits | {team_stats.get('avg_commits', 0):.1f} |
| Average Productivity Score | {team_stats.get('avg_productivity', 0):.1f} |
"""
        
        if team_stats.get('top_performer'):
            markdown += f"\n**🌟 Top Performer:** {team_stats['top_performer']}\n"
        if team_stats.get('most_collaborative'):
            markdown += f"**🤝 Most Collaborative:** {team_stats['most_collaborative']}\n"
    
    # Insights and Actions
    markdown += "\n## Insights & Next Steps\n"
    
    actions = insights.get('recommended_actions', [])
    if actions:
        markdown += "\n### Recommended Actions\n"
        for action in actions:
            priority = action.get('priority', 'medium').upper()
            markdown += f"- **[{priority}]** {action.get('action', 'Action needed')}\n"
            if action.get('rationale'):
                markdown += f"  - {action['rationale']}\n"
    
    focus_areas = insights.get('team_focus_areas', [])
    if focus_areas:
        markdown += "\n### Team Focus Areas\n"
        for area in focus_areas:
            markdown += f"- {area}\n"
    
    coaching = insights.get('individual_coaching', [])
    if coaching:
        markdown += "\n### Individual Coaching Opportunities\n"
        for item in coaching:
            markdown += f"- **{item.get('focus', 'Focus area')}**: {item.get('suggestion', 'No suggestion')}\n"
    
    markdown += "\n---\n*Generated by GitLab Analytics - Weekly Productivity Reports*"
    
    return markdown

def collect_team_report(group_ids: List[int], report_type: str = 'kickoff') -> Dict[str, Any]:
    """Collect team report data for Monday kickoff or Friday wrap-up.
    
    Args:
        group_ids: List of GitLab group IDs
        report_type: Either 'kickoff' or 'wrapup'
        
    Returns:
        Report data dictionary
    """
    config = Config()
    gitlab_config = config.get_gitlab_config()
    client = GitLabClient(gitlab_config['url'], gitlab_config['token'])
    analytics = GitLabAnalytics(client)
    
    # Get date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    report = {
        'metadata': {
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'generated_at': datetime.now().isoformat(),
            'report_type': report_type,
            'groups_analyzed': len(group_ids)
        },
        'executive_summary': {},
        'team_activity': {},
        'project_health': [],
        'top_contributors': [],
        'deadlines': []
    }
    
    # Collect data using existing analytics service
    for group_id in group_ids:
        group_metrics = analytics.get_group_metrics(group_id)
        # ... process metrics and add to report ...
    
    return report

def generate_email_content(report_data: Dict[str, Any]) -> str:
    """Generate HTML email content from report data.
    
    Args:
        report_data: Report data dictionary
        
    Returns:
        HTML email content
    """
    template = WeeklyReportEmailTemplate()
    return template.generate_html_email(report_data)

def send_scheduled_report(group_ids: List[int], recipients: List[str], report_type: str = 'kickoff') -> None:
    """Send scheduled team report.
    
    Args:
        group_ids: List of GitLab group IDs
        recipients: List of email recipients
        report_type: Either 'kickoff' or 'wrapup'
    """
    # Collect report data
    report_data = collect_team_report(group_ids, report_type)
    
    # Generate email content
    html_content = generate_email_content(report_data)
    
    # Save to temp file (needed for send_html_email)
    temp_path = Path('temp_report.html')
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Send email to each recipient
    subject = f"Team {'Kickoff' if report_type == 'kickoff' else 'Wrap-up'} Report - {datetime.now().strftime('%Y-%m-%d')}"
    for recipient in recipients:
        send_html_email(str(temp_path), recipient, subject)
    
    # Clean up temp file
    temp_path.unlink()

     # Send to MS Teams if configured
    teams_config = config.get_teams_config()
    if teams_config.get('webhook_url'):
        teams_service = TeamsWebhookService()
        teams_service.send_message(
            webhook_url=teams_config['webhook_url'],
            message=teams_service.format_report_for_teams(report_data, report_type)
        )
    
    # Save to history if enabled
    history_config = config.get_history_config()
    if history_config.get('save_to_dashboard'):
        history_service = HistoryService(history_config.get('directory', 'reports/history'))
        history_service.save_report(report_data, report_type)
        
        # Cleanup old reports
        if history_config.get('retention_days'):
            history_service.cleanup_old_reports(history_config['retention_days'])


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate and send weekly productivity reports for team syncs",
        epilog="""
Examples:
  # Generate report for groups 1,2,3 and save as HTML
  python scripts/weekly_reports.py --groups 1,2,3 --output report.html

  # Send email report to team
  python scripts/weekly_reports.py --groups 1,2,3 --email team@company.com,manager@company.com

  # Generate report for specific team members
  python scripts/weekly_reports.py --groups 1,2,3 --team john.doe,jane.smith --output report.json

  # Generate 2-week report with email delivery
  python scripts/weekly_reports.py --groups 1,2,3 --weeks 2 --email team@company.com
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Target groups
    parser.add_argument(
        '--groups', '-g',
        required=True,
        help='Comma-separated list of GitLab group IDs to analyze'
    )
    
    # Team configuration
    parser.add_argument(
        '--team',
        help='Comma-separated list of team member usernames to focus on (optional)'
    )
    parser.add_argument(
        '--team-name',
        default='Development Team',
        help='Name of the team for the report (default: Development Team)'
    )
    
    # Time period
    parser.add_argument(
        '--weeks',
        type=int,
        default=1,
        help='Number of weeks to analyze (default: 1)'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        help='Output file path (format determined by extension: .json, .html, .md)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'html', 'markdown'],
        default='html',
        help='Output format when no extension in output path (default: html)'
    )
    
    # Email options
    parser.add_argument(
        '--email',
        help='Comma-separated list of email recipients'
    )
    parser.add_argument(
        '--email-cc',
        help='Comma-separated list of CC recipients'
    )
    parser.add_argument(
        '--email-attachments',
        help='Comma-separated list of file paths to attach to email'
    )
    parser.add_argument(
        '--no-charts',
        action='store_true',
        help='Disable chart generation in email reports'
    )
    
    # Email testing
    parser.add_argument(
        '--test-email',
        help='Send test email to specified address to verify configuration'
    )
    
    # Configuration
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate report but do not send emails'
    )
    parser.add_argument(
        '--schedule', 
        action='store_true', 
        help='Run in scheduled mode (for automated reports)'
    )
    parser.add_argument(
        '--report-type', 
        choices=['kickoff', 'wrapup'], 
        default='kickoff', 
        help='Type of scheduled report: kickoff (Monday) or wrapup (Friday)'
    )
    
    
    # Space optimization options
    parser.add_argument(
        '--compact',
        action='store_true',
        help='Use compact output format to save space'
    )
    parser.add_argument(
        '--max-width',
        type=int,
        help='Maximum terminal width for table formatting'
    )
    parser.add_argument(
        '--max-contributors',
        type=int,
        default=25,
        help='Maximum number of contributors to show (default: 25)'
    )
    parser.add_argument(
        '--max-projects',
        type=int,
        default=35,
        help='Maximum number of projects to show in activity tables (default: 35)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config(args.config)
    
    # Setup logging
    setup_logging(
        config.get_log_config(),
        console_level=args.log_level
    )
    
    try:
        # Validate configuration
        config.validate()
        
        # Handle test email
        if args.test_email:
            print(f"{Colors.BOLD}Sending test email to {args.test_email}...{Colors.RESET}")
            email_sender = WeeklyReportEmailSender()
            if email_sender.send_test_email(args.test_email):
                print(f"{Colors.GREEN}Test email sent successfully!{Colors.RESET}")
                return 0
            else:
                print(f"{Colors.RED}Failed to send test email. Check configuration and logs.{Colors.RESET}")
                return 1
        
        if args.schedule:
                    group_ids = parse_groups(args.groups)
                    recipients = parse_recipients(args.email)
                    send_scheduled_report(group_ids, recipients, args.report_type)
                    print(f"Scheduled report ({args.report_type}) sent to {recipients}")
                    return 0

        # Validate required arguments
        if not args.groups:
            print(f"{Colors.RED}Error: --groups is required{Colors.RESET}")
            return 1
        
        if not args.output and not args.email:
            print(f"{Colors.RED}Error: Either --output or --email must be specified{Colors.RESET}")
            return 1
        
        # Parse arguments
        group_ids = parse_groups(args.groups)
        team_members = parse_team_members(args.team) if args.team else None
        
        if not group_ids:
            print(f"{Colors.RED}Error: No valid group IDs provided{Colors.RESET}")
            return 1
        
        # Create GitLab client
        gitlab_config = config.get_gitlab_config()
        client = GitLabClient(
            url=gitlab_config['url'],
            token=gitlab_config['token'],
            config=gitlab_config
        )
        
        # Create weekly reporter
        reporter = WeeklyProductivityReporter(client)
        
        print(f"{Colors.BOLD}Generating weekly productivity report...{Colors.RESET}")
        print(f"Groups: {group_ids}")
        print(f"Team: {args.team_name}")
        print(f"Period: {args.weeks} week(s)")
        if team_members:
            print(f"Team members: {len(team_members)} specified")
        
        # Generate report
        report_data = reporter.generate_team_report(
            group_ids=group_ids,
            team_members=team_members,
            weeks_back=args.weeks
        )
        
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            
            # Determine format from extension or argument
            if output_path.suffix:
                if output_path.suffix == '.json':
                    format_type = 'json'
                elif output_path.suffix in ['.html', '.htm']:
                    format_type = 'html'
                elif output_path.suffix in ['.md', '.markdown']:
                    format_type = 'markdown'
                else:
                    format_type = args.format
            else:
                format_type = args.format
                # Add appropriate extension
                extensions = {'json': '.json', 'html': '.html', 'markdown': '.md'}
                output_path = output_path.with_suffix(extensions[format_type])
            
            save_report_to_file(report_data, output_path, format_type)
            print(f"{Colors.GREEN}Report saved: {output_path}{Colors.RESET}")
        
        # Send email if requested
        if args.email and not args.dry_run:
            recipients = parse_recipients(args.email)
            cc_recipients = parse_recipients(args.email_cc) if args.email_cc else None
            attachments = args.email_attachments.split(',') if args.email_attachments else None
            
            print(f"{Colors.BOLD}Sending email report to {len(recipients)} recipients...{Colors.RESET}")
            
            email_sender = WeeklyReportEmailSender()
            success = email_sender.send_team_report(
                report_data=report_data,
                recipients=recipients,
                team_name=args.team_name,
                include_charts=not args.no_charts,
                attachments=attachments
            )
            
            if success:
                print(f"{Colors.GREEN}Email report sent successfully!{Colors.RESET}")
            else:
                print(f"{Colors.RED}Failed to send email report. Check configuration and logs.{Colors.RESET}")
                return 1
        
        elif args.email and args.dry_run:
            recipients = parse_recipients(args.email)
            print(f"{Colors.YELLOW}Dry run: Would send email to {len(recipients)} recipients{Colors.RESET}")
        
        # Print summary
        executive_summary = report_data.get('executive_summary', {})
        key_metrics = executive_summary.get('key_metrics', {})
        
        # Compact summary at the top
        total_commits = key_metrics.get('total_commits', 0)
        active_contributors = key_metrics.get('active_contributors', 0)
        healthy_projects = key_metrics.get('healthy_projects', 0)
        attention_projects = key_metrics.get('projects_needing_attention', 0)
        
        print(f"\n{Colors.BOLD}📊 WEEK SUMMARY:{Colors.RESET} {total_commits} commits by {active_contributors} contributors | "
              f"{Colors.GREEN}{healthy_projects} healthy{Colors.RESET} | {Colors.RED}{attention_projects} need attention{Colors.RESET}")
        
        # Add code and issue metrics in compact format
        contributors_for_metrics = report_data.get('individual_metrics', {}).get('contributors', {})
        if contributors_for_metrics:
            total_net_lines = sum(c.get('net_lines_changed', 0) for c in contributors_for_metrics.values())
            total_issues_opened = sum(c.get('issues_opened_this_week', 0) for c in contributors_for_metrics.values())
            total_issues_closed = sum(c.get('issues_closed_this_week', 0) for c in contributors_for_metrics.values())
            
            lines_str = _format_number(total_net_lines, show_sign=True, compact=True)
            
            code_metrics = []
            if total_net_lines != 0:
                code_metrics.append(f"{lines_str} lines")
            if total_issues_opened > 0 or total_issues_closed > 0:
                code_metrics.append(f"{total_issues_opened} issues opened, {total_issues_closed} closed")
                if total_issues_opened > 0:
                    resolution_rate = (total_issues_closed / total_issues_opened) * 100
                    code_metrics.append(f"{resolution_rate:.0f}% resolution rate")
            
            if code_metrics:
                print(f"{Colors.BOLD}📈 CODE IMPACT:{Colors.RESET} {' | '.join(code_metrics)}")
        
        # Display contributor list in compact format
        contributors_list = report_data.get('individual_metrics', {}).get('contributors', {})
        if contributors_list and not args.dry_run:
            # Use max_contributors from args
            display_max_contributors = args.max_contributors if hasattr(args, 'max_contributors') else 25
            print(f"\n{Colors.BOLD}👥 All Contributors Summary (Total: {len(contributors_list)}):{Colors.RESET}")
            sorted_contributors = sorted(contributors_list.items(), key=lambda x: x[1]['commits'], reverse=True)
            
            # Show contributors in a more compact format
            limit = len(contributors_list) if len(contributors_list) <= 40 else display_max_contributors
            
            for i, (name, stats) in enumerate(sorted_contributors[:limit], 1):
                # Get primary email (first one)
                emails = list(stats.get('emails', set()))
                primary_email = emails[0] if emails else ""
                
                # Format compactly
                commits = stats['commits']
                mrs = stats.get('merge_requests_created', 0)
                lines = stats.get('net_lines_changed', 0)
                lines_str = _format_number(lines, show_sign=True, compact=True) if lines != 0 else ""
                
                activity_parts = [f"{commits}c"]
                if mrs > 0:
                    activity_parts.append(f"{mrs}mr")
                if lines_str:
                    activity_parts.append(lines_str)
                
                activity_summary = ", ".join(activity_parts)
                
                # Show email in parentheses if it's informative
                email_part = ""
                if primary_email and not primary_email.startswith(name.lower().replace(' ', '.')):
                    email_domain = primary_email.split('@')[1] if '@' in primary_email else primary_email
                    if email_domain not in ['thaibev.com', 'gmail.com']:  # Show interesting domains
                        email_part = f" ({email_domain})"
                    elif len(emails) > 1:
                        email_part = f" (+{len(emails)-1} emails)"
                
                print(f"  {i:2d}. {name}{email_part} → {activity_summary}")
                
            if len(contributors_list) > limit:
                remaining = len(contributors_list) - limit
                print(f"\n{Colors.YELLOW}  └─ ... and {remaining} more contributor{'s' if remaining > 1 else ''}{Colors.RESET}")
                
            # Show potential duplicates more compactly
            email_to_names = defaultdict(set)
            for name, stats in contributors_list.items():
                for email in stats.get('emails', set()):
                    email_to_names[email].add(name)
            
            duplicates = {email: names for email, names in email_to_names.items() if len(names) > 1}
            if duplicates:
                print(f"\n{Colors.YELLOW}⚠️  Potential duplicates:{Colors.RESET}")
                for email, names in list(duplicates.items())[:3]:  # Show top 3
                    print(f"  {email} → {', '.join(sorted(names))}")
                if len(duplicates) > 3:
                    print(f"  ... and {len(duplicates) - 3} more potential duplicates")
            else:
                print(f"\n{Colors.GREEN}✓ No obvious duplicates found{Colors.RESET}")
        
        # Display detailed tables
        detailed_tables = report_data.get('detailed_tables', {})
        if detailed_tables and not args.dry_run:
            _display_detailed_tables(
                detailed_tables, 
                max_width=args.max_width,
                max_projects=args.max_projects,
                max_contributors=args.max_contributors,
                compact=args.compact
            )
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.RESET}")
        return 1
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}", exc_info=True)
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())