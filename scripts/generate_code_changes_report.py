#!/usr/bin/env python3
"""Generate code changes report showing lines added/removed by project and group."""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("💡 Tip: Install python-dotenv to load .env files automatically")
    print("   pip install python-dotenv")
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

# Try to import rich for beautiful table formatting
try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("💡 Tip: Install rich for beautiful table formatting")
    print("   pip install rich")

# Group name mapping
GROUP_NAMES = {
    1721: "AI-ML-Services",
    1267: "Research Repos", 
    1269: "Internal Services",
    119: "iland"
}

def get_env_or_exit(key: str, description: str) -> str:
    """Get environment variable or exit with helpful message."""
    value = os.getenv(key)
    if not value:
        print(f"❌ Missing required environment variable: {key}")
        print(f"   {description}")
        sys.exit(1)
    return value

def simple_gitlab_request(url: str, token: str, endpoint: str, params: Dict = None) -> Any:
    """Make a simple GitLab API request with pagination support."""
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
        print(f"❌ GitLab API Error: {e}")
        return []

def get_commit_stats_by_branch(gitlab_url: str, gitlab_token: str, project_id: int, since_date: datetime, default_branch_only: bool = False) -> Dict[str, Dict[str, Any]]:
    """Get commit statistics by branch for a project since a date."""
    
    if default_branch_only:
        # Get only default branch commits
        commits = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"projects/{project_id}/repository/commits",
            {"since": since_date.isoformat(), "with_stats": "true"}
        )
        
        branch_stats = {}
        if commits:
            additions = sum(commit.get('stats', {}).get('additions', 0) for commit in commits)
            deletions = sum(commit.get('stats', {}).get('deletions', 0) for commit in commits)
            contributors = set(commit.get('author_name', 'Unknown') for commit in commits)
            
            branch_stats['default'] = {
                'additions': additions,
                'deletions': deletions,
                'contributors': len(contributors),
                'contributor_names': contributors,
                'commits': len(commits)
            }
        
        return branch_stats
    
    # Get all branches for the project
    branches = simple_gitlab_request(
        gitlab_url, gitlab_token,
        f"projects/{project_id}/repository/branches",
        {}
    )
    
    branch_stats = {}
    processed_commits = set()  # To avoid counting the same commit multiple times across branches
    
    for branch in branches:
        branch_name = branch.get('name', '')
        if not branch_name:
            continue
            
        try:
            # Get commits for this specific branch
            branch_commits = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"projects/{project_id}/repository/commits",
                {"ref_name": branch_name, "since": since_date.isoformat(), "with_stats": "true"}
            )
            
            if not branch_commits:
                continue  # Skip branches with no recent commits
            
            # Filter out commits we've already seen in other branches
            unique_commits = []
            for commit in branch_commits:
                commit_sha = commit.get('id', '')
                if commit_sha not in processed_commits:
                    unique_commits.append(commit)
                    processed_commits.add(commit_sha)
            
            if not unique_commits:
                continue  # Skip if no unique commits
            
            # Calculate stats for this branch
            additions = sum(commit.get('stats', {}).get('additions', 0) for commit in unique_commits)
            deletions = sum(commit.get('stats', {}).get('deletions', 0) for commit in unique_commits)
            contributors = set(commit.get('author_name', 'Unknown') for commit in unique_commits)
            
            branch_stats[branch_name] = {
                'additions': additions,
                'deletions': deletions,
                'contributors': len(contributors),
                'contributor_names': contributors,
                'commits': len(unique_commits)
            }
                    
        except Exception as e:
            print(f"      ⚠️ Error processing branch {branch_name}: {e}")
            continue
    
    return branch_stats



def analyze_project_code_changes(project: Dict, gitlab_url: str, gitlab_token: str, default_branch_only: bool = False) -> List[Dict[str, Any]]:
    """Analyze code changes for a single project across different time periods, returning one row per active branch."""
    project_id = project['id']
    project_name = project['name']
    
    # Calculate date ranges
    now = datetime.now(timezone.utc)
    date_7d = now - timedelta(days=7)
    date_15d = now - timedelta(days=15)
    date_30d = now - timedelta(days=30)
    date_60d = now - timedelta(days=60)
    date_90d = now - timedelta(days=90)
    
    print(f"    📊 Analyzing {project_name}...")
    
    try:
        # Get branch statistics for each period
        branch_stats_7d = get_commit_stats_by_branch(gitlab_url, gitlab_token, project_id, date_7d, default_branch_only)
        branch_stats_15d = get_commit_stats_by_branch(gitlab_url, gitlab_token, project_id, date_15d, default_branch_only)
        branch_stats_30d = get_commit_stats_by_branch(gitlab_url, gitlab_token, project_id, date_30d, default_branch_only)
        branch_stats_60d = get_commit_stats_by_branch(gitlab_url, gitlab_token, project_id, date_60d, default_branch_only)
        branch_stats_90d = get_commit_stats_by_branch(gitlab_url, gitlab_token, project_id, date_90d, default_branch_only)
        
        # Get all unique branches across all periods
        all_branches = set()
        all_branches.update(branch_stats_7d.keys())
        all_branches.update(branch_stats_15d.keys())
        all_branches.update(branch_stats_30d.keys())
        all_branches.update(branch_stats_60d.keys())
        all_branches.update(branch_stats_90d.keys())
        
        if not all_branches:
            print(f"      ⚠️ No active branches found for {project_name}")
            return []
        
        print(f"      🌿 Found {len(all_branches)} active branches: {', '.join(sorted(all_branches)[:5])}")
        
        # Create one row per branch
        branch_rows = []
        for branch_name in sorted(all_branches):
            # Get stats for this branch across all periods
            stats_7d = branch_stats_7d.get(branch_name, {'additions': 0, 'deletions': 0, 'contributors': 0, 'commits': 0})
            stats_15d = branch_stats_15d.get(branch_name, {'additions': 0, 'deletions': 0, 'contributors': 0, 'commits': 0})
            stats_30d = branch_stats_30d.get(branch_name, {'additions': 0, 'deletions': 0, 'contributors': 0, 'commits': 0})
            stats_60d = branch_stats_60d.get(branch_name, {'additions': 0, 'deletions': 0, 'contributors': 0, 'commits': 0})
            stats_90d = branch_stats_90d.get(branch_name, {'additions': 0, 'deletions': 0, 'contributors': 0, 'commits': 0})
            
            branch_rows.append({
                'project_name': project_name,
                'project_id': project_id,
                'branch_name': branch_name,
                'web_url': project.get('web_url', ''),
                'contributors_7d': stats_7d['contributors'],
                'contributors_15d': stats_15d['contributors'],
                'contributors_30d': stats_30d['contributors'],
                'contributors_60d': stats_60d['contributors'],
                'contributors_90d': stats_90d['contributors'],
                'code_changes_7d': {
                    'additions': stats_7d['additions'],
                    'deletions': stats_7d['deletions'],
                    'net_change': stats_7d['additions'] - stats_7d['deletions'],
                    'total_lines': stats_7d['additions'] + stats_7d['deletions']
                },
                'code_changes_15d': {
                    'additions': stats_15d['additions'],
                    'deletions': stats_15d['deletions'],
                    'net_change': stats_15d['additions'] - stats_15d['deletions'],
                    'total_lines': stats_15d['additions'] + stats_15d['deletions']
                },
                'code_changes_30d': {
                    'additions': stats_30d['additions'],
                    'deletions': stats_30d['deletions'],
                    'net_change': stats_30d['additions'] - stats_30d['deletions'],
                    'total_lines': stats_30d['additions'] + stats_30d['deletions']
                },
                'code_changes_60d': {
                    'additions': stats_60d['additions'],
                    'deletions': stats_60d['deletions'],
                    'net_change': stats_60d['additions'] - stats_60d['deletions'],
                    'total_lines': stats_60d['additions'] + stats_60d['deletions']
                },
                'code_changes_90d': {
                    'additions': stats_90d['additions'],
                    'deletions': stats_90d['deletions'],
                    'net_change': stats_90d['additions'] - stats_90d['deletions'],
                    'total_lines': stats_90d['additions'] + stats_90d['deletions']
                }
            })
        
        return branch_rows
        
    except Exception as e:
        print(f"    ⚠️ Error analyzing {project_name}: {e}")
        return [{
            'project_name': project_name,
            'project_id': project_id,
            'branch_name': 'error',
            'web_url': project.get('web_url', ''),
            'contributors_7d': 0,
            'contributors_15d': 0,
            'contributors_30d': 0,
            'contributors_60d': 0,
            'contributors_90d': 0,
            'code_changes_7d': {'additions': 0, 'deletions': 0, 'net_change': 0, 'total_lines': 0},
            'code_changes_15d': {'additions': 0, 'deletions': 0, 'net_change': 0, 'total_lines': 0},
            'code_changes_30d': {'additions': 0, 'deletions': 0, 'net_change': 0, 'total_lines': 0},
            'code_changes_60d': {'additions': 0, 'deletions': 0, 'net_change': 0, 'total_lines': 0},
            'code_changes_90d': {'additions': 0, 'deletions': 0, 'net_change': 0, 'total_lines': 0},
            'error': str(e)
        }]

def analyze_groups_code_changes(group_ids: List[int], gitlab_url: str, gitlab_token: str, default_branch_only: bool = False) -> List[Dict[str, Any]]:
    """Analyze code changes across multiple GitLab groups."""
    print(f"📊 Analyzing code changes for {len(group_ids)} groups...")
    
    all_projects_data = []
    
    for group_id in group_ids:
        group_display_name = GROUP_NAMES.get(group_id, f"Group {group_id}")
        print(f"  📁 Analyzing group {group_id} ({group_display_name})...")
        
        # Get projects in group
        projects = simple_gitlab_request(
            gitlab_url, gitlab_token,
            f"groups/{group_id}/projects",
            {"include_subgroups": "true", "archived": "false"}
        )
        
        if not projects:
            print(f"    ⚠️ No projects found in group {group_id}")
            continue
        
        for project in projects:
            # Special filtering for iland group (119) - only show llama-index projects
            if group_id == 119 and 'llama-index' not in project['name'].lower():
                print(f"    ⏭️ Skipping {project['name']} (not llama-index project)")
                continue
                
            branch_rows = analyze_project_code_changes(project, gitlab_url, gitlab_token, default_branch_only)
            for branch_data in branch_rows:
                branch_data['group_id'] = group_id
                branch_data['group_name'] = group_display_name
                all_projects_data.append(branch_data)
    
    # Sort by: Group (A-Z), Project (A-Z case-insensitive), then 7-day code changes (descending)
    all_projects_data.sort(key=lambda x: (
        x['group_name'].lower(),           # Group alphabetically A-Z (case-insensitive)
        x['project_name'].lower(),         # Project alphabetically A-Z (case-insensitive)
        -x['code_changes_7d']['total_lines']  # Within project: branches by 7-day activity (high to low)
    ))
    
    return all_projects_data

def format_code_change(change_data: Dict) -> str:
    """Format code change data into a readable string."""
    additions = change_data['additions']
    deletions = change_data['deletions']
    net_change = change_data['net_change']
    
    if additions == 0 and deletions == 0:
        return "No changes"
    
    net_sign = "+" if net_change >= 0 else ""
    return f"+{additions:,} -{deletions:,} (net: {net_sign}{net_change:,})"

def display_table_rich(projects_data: List[Dict[str, Any]]):
    """Display results in a beautiful table using Rich."""
    console = Console()
    
    # Create table
    table = Table(
        title="📊 Code Changes Report by Group, Project, and Branch",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold blue",
        title_style="bold green"
    )
    
    # Add columns
    table.add_column("Group", style="cyan", width=15)
    table.add_column("Project", style="yellow", width=20)
    table.add_column("Branch", style="bright_cyan", width=15)
    table.add_column("Contributors\n(90d)", justify="center", style="magenta", width=10)
    table.add_column("7 days", style="green", width=20)
    table.add_column("15 days", style="blue", width=20) 
    table.add_column("30 days", style="red", width=20)
    table.add_column("60 days", style="yellow", width=20)
    table.add_column("90 days", style="purple", width=20)
    
    # Group projects by group and project for display
    grouped_data = defaultdict(lambda: defaultdict(list))
    for project in projects_data:
        grouped_data[project['group_name']][project['project_name']].append(project)
    
    # Add rows grouped by group and project
    for group_name in sorted(grouped_data.keys(), key=str.lower):
        group_projects = grouped_data[group_name]
        group_first_row = True
        
        for project_name in sorted(group_projects.keys(), key=str.lower):
            project_branches = group_projects[project_name]
            project_first_row = True
            
            for branch_data in project_branches:
                # Show group name only on first row of group
                group_cell = group_name if group_first_row else ""
                # Show project name only on first row of project
                project_cell = project_name if project_first_row else ""
                
                group_first_row = False
                project_first_row = False
            
                # Format project name (truncate if too long)
                display_project_name = project_cell
                if display_project_name and len(display_project_name) > 18:
                    display_project_name = display_project_name[:15] + "..."
                
                # Color code based on activity level (using 7d for current activity)
                total_changes_7d = branch_data['code_changes_7d']['total_lines']
                if total_changes_7d > 500:
                    branch_style = "bold green"
                elif total_changes_7d > 100:
                    branch_style = "bold yellow"
                elif total_changes_7d > 0:
                    branch_style = "yellow"
                else:
                    branch_style = "dim"
                
                table.add_row(
                    group_cell,
                    Text(display_project_name, style="bold" if project_cell else "dim"),
                    Text(branch_data['branch_name'], style=branch_style),
                    str(branch_data['contributors_90d']),
                    format_code_change(branch_data['code_changes_7d']),
                    format_code_change(branch_data['code_changes_15d']),
                    format_code_change(branch_data['code_changes_30d']),
                    format_code_change(branch_data['code_changes_60d']),
                    format_code_change(branch_data['code_changes_90d'])
                )
        
        # Add separator between groups
        if group_name != sorted(grouped_data.keys(), key=str.lower)[-1]:  # Not the last group
            table.add_row("", "", "", "", "", "", "", "", "", "")
    
    console.print(table)

def display_table_simple(projects_data: List[Dict[str, Any]]):
    """Display results in a simple text table."""
    # Header
    print("\n" + "="*180)
    print("📊 CODE CHANGES REPORT BY GROUP, PROJECT, AND BRANCH")
    print("="*180)
    
    # Column headers
    header = f"{'Group':<15} {'Project':<20} {'Branch':<15} {'Contributors':<12} {'7 Days':<20} {'15 Days':<20} {'30 Days':<20} {'60 Days':<20} {'90 Days':<20}"
    print(header)
    print("-" * 180)
    
    # Group projects by group and project for display
    grouped_data = defaultdict(lambda: defaultdict(list))
    for project in projects_data:
        grouped_data[project['group_name']][project['project_name']].append(project)
    
    # Display rows grouped by group and project
    for group_name in sorted(grouped_data.keys(), key=str.lower):
        group_projects = grouped_data[group_name]
        group_first_row = True
        
        for project_name in sorted(group_projects.keys(), key=str.lower):
            project_branches = group_projects[project_name]
            project_first_row = True
            
            for branch_data in project_branches:
                # Show group name only on first row of group
                group_cell = group_name if group_first_row else ""
                # Show project name only on first row of project
                project_cell = project_name if project_first_row else ""
                
                group_first_row = False
                project_first_row = False
                
                # Truncate project name if too long
                display_project_name = project_cell
                if display_project_name and len(display_project_name) > 18:
                    display_project_name = display_project_name[:15] + "..."
                
                # Truncate branch names if too long
                branch_name = branch_data['branch_name']
                if len(branch_name) > 13:
                    branch_name = branch_name[:10] + "..."
                
                row = f"{group_cell:<15} {display_project_name:<20} {branch_name:<15} {branch_data['contributors_90d']:<12} {format_code_change(branch_data['code_changes_7d']):<20} {format_code_change(branch_data['code_changes_15d']):<20} {format_code_change(branch_data['code_changes_30d']):<20} {format_code_change(branch_data['code_changes_60d']):<20} {format_code_change(branch_data['code_changes_90d']):<20}"
                print(row)
        
        # Add separator between groups
        if group_name != sorted(grouped_data.keys(), key=str.lower)[-1]:  # Not the last group
            print()

def generate_html_report(projects_data: List[Dict[str, Any]], output_file: str):
    """Generate a beautiful HTML report in shadcn/ui style."""
    # Calculate summary stats
    total_branches = len(projects_data)
    unique_projects = len(set(p['project_name'] for p in projects_data))
    
    # Calculate project-level totals for all time periods to avoid double-counting commits across branches
    projects_grouped = defaultdict(list)
    for branch_data in projects_data:
        projects_grouped[branch_data['project_name']].append(branch_data)
    
    # Calculate totals for each time period
    periods = ['7d', '15d', '30d', '60d', '90d']
    period_totals = {}
    
    for period in periods:
        project_totals = defaultdict(lambda: {'additions': 0, 'deletions': 0})
        
        # For each project, sum all unique branch contributions for this period
        for project_name, branches in projects_grouped.items():
            project_additions = sum(b[f'code_changes_{period}']['additions'] for b in branches)
            project_deletions = sum(b[f'code_changes_{period}']['deletions'] for b in branches)
            project_totals[project_name]['additions'] = project_additions
            project_totals[project_name]['deletions'] = project_deletions
        
        # Sum across all projects for this period
        total_additions = sum(p['additions'] for p in project_totals.values())
        total_deletions = sum(p['deletions'] for p in project_totals.values())
        period_totals[period] = {
            'additions': total_additions,
            'deletions': total_deletions,
            'net': total_additions - total_deletions
        }
    
    # Active branches (branches with changes in different periods)
    active_branches_7d = sum(1 for p in projects_data if p['code_changes_7d']['total_lines'] > 0)
    active_branches_15d = sum(1 for p in projects_data if p['code_changes_15d']['total_lines'] > 0)
    active_branches_30d = sum(1 for p in projects_data if p['code_changes_30d']['total_lines'] > 0)
    active_branches_60d = sum(1 for p in projects_data if p['code_changes_60d']['total_lines'] > 0)
    active_branches_90d = sum(1 for p in projects_data if p['code_changes_90d']['total_lines'] > 0)
    
    # Group data by group and project for display
    grouped_data = defaultdict(lambda: defaultdict(list))
    for project in projects_data:
        grouped_data[project['group_name']][project['project_name']].append(project)
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Changes Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: hsl(0 0% 98%);
            color: hsl(222.2 84% 4.9%);
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        
        .title {{
            font-size: 2.5rem;
            font-weight: 700;
            color: hsl(222.2 84% 4.9%);
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            font-size: 1.125rem;
            color: hsl(215.4 16.3% 46.9%);
            margin-bottom: 2rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 3rem;
        }}
        
        .stat-card {{
            background: white;
            border: 1px solid hsl(214.3 31.8% 91.4%);
            border-radius: 0.5rem;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: hsl(222.2 84% 4.9%);
            margin-bottom: 0.25rem;
        }}
        
        .stat-label {{
            font-size: 0.875rem;
            color: hsl(215.4 16.3% 46.9%);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .table-container {{
            background: white;
            border: 1px solid hsl(214.3 31.8% 91.4%);
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }}
        
        .table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .table th {{
            background: hsl(210 40% 98%);
            padding: 1rem 0.75rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.875rem;
            color: hsl(215.4 16.3% 46.9%);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid hsl(214.3 31.8% 91.4%);
        }}
        
        .table td {{
            padding: 0.75rem;
            border-bottom: 1px solid hsl(214.3 31.8% 91.4%);
            font-size: 0.875rem;
        }}
        
        .table tbody tr:hover {{
            background: hsl(210 40% 98%);
        }}
        
        .group-header {{
            background: hsl(210 40% 96%) !important;
            font-weight: 600;
            color: hsl(222.2 84% 4.9%);
        }}
        
        .group-header td {{
            padding: 1rem 0.75rem;
            font-size: 1rem;
            border-bottom: 2px solid hsl(214.3 31.8% 91.4%);
        }}
        
        .project-name {{
            font-weight: 500;
            color: hsl(222.2 84% 4.9%);
        }}
        
        .branch-name {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            background: hsl(210 40% 98%);
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.8125rem;
            color: hsl(222.2 84% 4.9%);
        }}
        
        .code-change {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.8125rem;
        }}
        
        .positive {{ color: hsl(142.1 76.2% 36.3%); }}
        .negative {{ color: hsl(0 84.2% 60.2%); }}
        .neutral {{ color: hsl(215.4 16.3% 46.9%); }}
        
        .contributors {{
            text-align: center;
            font-weight: 500;
        }}
        
        .activity-high {{ 
            background: hsl(142.1 76.2% 96%);
            color: hsl(142.1 76.2% 36.3%);
        }}
        
        .activity-medium {{ 
            background: hsl(47.9 95.8% 96%);
            color: hsl(47.9 95.8% 53.2%);
        }}
        
        .activity-low {{ 
            background: hsl(210 40% 98%);
            color: hsl(215.4 16.3% 46.9%);
        }}
        
        .no-changes {{
            color: hsl(215.4 16.3% 46.9%);
            font-style: italic;
        }}
        
        @media (max-width: 768px) {{
            .table-container {{
                overflow-x: auto;
            }}
            
            .table {{
                min-width: 800px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">📊 Code Changes Report</h1>
            <p class="subtitle">Analysis by Group, Project, and Branch • Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_branches:,}</div>
                <div class="stat-label">Total Branches</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{unique_projects:,}</div>
                <div class="stat-label">Unique Projects</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{active_branches_7d:,}</div>
                <div class="stat-label">Active (7d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{active_branches_30d:,}</div>
                <div class="stat-label">Active (30d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{active_branches_90d:,}</div>
                <div class="stat-label">Active (90d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{period_totals['7d']['net']:+,}</div>
                <div class="stat-label">Net Change (7d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{period_totals['15d']['net']:+,}</div>
                <div class="stat-label">Net Change (15d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{period_totals['30d']['net']:+,}</div>
                <div class="stat-label">Net Change (30d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{period_totals['60d']['net']:+,}</div>
                <div class="stat-label">Net Change (60d)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{period_totals['90d']['net']:+,}</div>
                <div class="stat-label">Net Change (90d)</div>
            </div>
        </div>
        
        <div class="table-container">
            <table class="table">
                <thead>
                    <tr>
                        <th>Group</th>
                        <th>Project</th>
                        <th>Branch</th>
                        <th>Contributors (90d)</th>
                        <th>7 Days</th>
                        <th>15 Days</th>
                        <th>30 Days</th>
                        <th>60 Days</th>
                        <th>90 Days</th>
                    </tr>
                </thead>
                <tbody>"""
    
    def format_change_html(change_data):
        additions = change_data['additions']
        deletions = change_data['deletions']
        net_change = change_data['net_change']
        
        if additions == 0 and deletions == 0:
            return '<span class="no-changes">No changes</span>'
        
        net_class = "positive" if net_change > 0 else "negative" if net_change < 0 else "neutral"
        net_sign = "+" if net_change >= 0 else ""
        
        return f'<span class="code-change">+{additions:,} -{deletions:,} <span class="{net_class}">({net_sign}{net_change:,})</span></span>'
    
    # Generate table rows grouped by group and project
    for group_name in sorted(grouped_data.keys(), key=str.lower):
        group_projects = grouped_data[group_name]
        
        # Add group header
        html_content += f"""
                    <tr class="group-header">
                        <td colspan="9">{group_name}</td>
                    </tr>"""
        
        for project_name in sorted(group_projects.keys(), key=str.lower):
            project_branches = group_projects[project_name]
            project_first_row = True
            
            for branch_data in project_branches:
                # Show project name only on first row of project
                project_cell = project_name if project_first_row else ""
                project_first_row = False
                
                # Determine activity level for styling
                total_7d = branch_data['code_changes_7d']['total_lines']
                if total_7d > 500:
                    activity_class = "activity-high"
                elif total_7d > 100:
                    activity_class = "activity-medium"
                elif total_7d > 0:
                    activity_class = "activity-low"
                else:
                    activity_class = ""
                
                html_content += f"""
                    <tr class="{activity_class}">
                        <td></td>
                        <td class="project-name">{project_cell}</td>
                        <td><span class="branch-name">{branch_data['branch_name']}</span></td>
                        <td class="contributors">{branch_data['contributors_90d']}</td>
                        <td>{format_change_html(branch_data['code_changes_7d'])}</td>
                        <td>{format_change_html(branch_data['code_changes_15d'])}</td>
                        <td>{format_change_html(branch_data['code_changes_30d'])}</td>
                        <td>{format_change_html(branch_data['code_changes_60d'])}</td>
                        <td>{format_change_html(branch_data['code_changes_90d'])}</td>
                    </tr>"""
    
    html_content += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
    
    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_summary_stats(projects_data: List[Dict[str, Any]]):
    """Generate and display summary statistics."""
    total_branches = len(projects_data)
    unique_projects = len(set(p['project_name'] for p in projects_data))
    
    # Calculate project-level totals for all time periods to avoid double-counting commits across branches
    # Group branches by project
    projects_grouped = defaultdict(list)
    for branch_data in projects_data:
        projects_grouped[branch_data['project_name']].append(branch_data)
    
    # Calculate totals for each time period
    periods = ['7d', '15d', '30d', '60d', '90d']
    period_totals = {}
    
    for period in periods:
        project_totals = defaultdict(lambda: {'additions': 0, 'deletions': 0})
        
        # For each project, sum all unique branch contributions for this period
        # Note: This is still an approximation since commits may appear in multiple branches
        for project_name, branches in projects_grouped.items():
            project_additions = sum(b[f'code_changes_{period}']['additions'] for b in branches)
            project_deletions = sum(b[f'code_changes_{period}']['deletions'] for b in branches)
            project_totals[project_name]['additions'] = project_additions
            project_totals[project_name]['deletions'] = project_deletions
        
        # Sum across all projects for this period
        total_additions = sum(p['additions'] for p in project_totals.values())
        total_deletions = sum(p['deletions'] for p in project_totals.values())
        period_totals[period] = {
            'additions': total_additions,
            'deletions': total_deletions,
            'net': total_additions - total_deletions
        }
    
    # Active branches (branches with changes in different periods)
    active_branches_7d = sum(1 for p in projects_data if p['code_changes_7d']['total_lines'] > 0)
    active_branches_15d = sum(1 for p in projects_data if p['code_changes_15d']['total_lines'] > 0)
    active_branches_30d = sum(1 for p in projects_data if p['code_changes_30d']['total_lines'] > 0)
    active_branches_60d = sum(1 for p in projects_data if p['code_changes_60d']['total_lines'] > 0)
    active_branches_90d = sum(1 for p in projects_data if p['code_changes_90d']['total_lines'] > 0)
    
    print(f"\n📈 SUMMARY STATISTICS")
    print(f"   Total Branches Analyzed: {total_branches}")
    print(f"   Unique Projects: {unique_projects}")
    print(f"   Active Branches (7d): {active_branches_7d}")
    print(f"   Active Branches (15d): {active_branches_15d}")
    print(f"   Active Branches (30d): {active_branches_30d}")
    print(f"   Active Branches (60d): {active_branches_60d}")
    print(f"   Active Branches (90d): {active_branches_90d}")
    print(f"")
    print(f"   📊 NET CODE CHANGES BY PERIOD:")
    print(f"   Net Code Change (7d):  {period_totals['7d']['net']:+,}")
    print(f"   Net Code Change (15d): {period_totals['15d']['net']:+,}")
    print(f"   Net Code Change (30d): {period_totals['30d']['net']:+,}")
    print(f"   Net Code Change (60d): {period_totals['60d']['net']:+,}")
    print(f"   Net Code Change (90d): {period_totals['90d']['net']:+,}")
    print(f"")
    print(f"   ⚠️  Note: Totals are approximations due to potential commit overlap across branches")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate code changes report for GitLab groups and projects",
        epilog="""
Examples:
  # Generate report for all known groups (default - includes all active branches)
  python scripts/generate_code_changes_report.py

  # Generate report for specific groups
  python scripts/generate_code_changes_report.py --groups 1721,1267,1269

  # Only count commits from default branch (faster, but may miss feature branch activity)
  python scripts/generate_code_changes_report.py --default-branch-only

  # Save output to file
  python scripts/generate_code_changes_report.py --output code_changes.txt

  # Generate beautiful HTML report
  python scripts/generate_code_changes_report.py --html report.html
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--groups', '-g',
        help='Comma-separated list of GitLab group IDs to analyze (default: all known groups)'
    )
    parser.add_argument(
        '--all-groups',
        action='store_true',
        help='Analyze all known groups (same as default behavior)'
    )
    parser.add_argument(
        '--default-branch-only',
        action='store_true',
        help='Only count commits from default branch (faster, but may miss feature branch activity)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (optional - prints to console if not specified)'
    )
    parser.add_argument(
        '--html',
        help='Generate HTML report file (e.g., --html report.html)'
    )
    
    args = parser.parse_args()
    
    # Parse group IDs
    if args.groups:
        try:
            group_ids = [int(gid.strip()) for gid in args.groups.split(',')]
        except ValueError:
            print("❌ Invalid group IDs. Please provide comma-separated integers.")
            return 1
    else:
        # Use all known groups by default
        group_ids = list(GROUP_NAMES.keys())
        print(f"📋 No groups specified, using all known groups: {', '.join(f'{gid} ({name})' for gid, name in GROUP_NAMES.items())}")
    
    if not group_ids:
        print("❌ No group IDs to analyze.")
        return 1
    
    # Get GitLab configuration
    gitlab_url = get_env_or_exit('GITLAB_URL', 'Your GitLab instance URL')
    gitlab_token = get_env_or_exit('GITLAB_TOKEN', 'Your GitLab API token')
    
    try:
        print(f"🚀 Starting code changes analysis...")
        
        if args.default_branch_only:
            print("📋 Mode: Default branch only (faster, but may miss feature branch activity)")
        else:
            print("🌿 Mode: All active branches (comprehensive analysis including feature branches)")
        
        # Analyze groups
        projects_data = analyze_groups_code_changes(group_ids, gitlab_url, gitlab_token, args.default_branch_only)
        
        if not projects_data:
            print("❌ No project data collected. Check your group IDs and permissions.")
            return 1
        
        # Redirect output to file if specified
        original_stdout = sys.stdout
        if args.output:
            output_file = open(args.output, 'w', encoding='utf-8')
            sys.stdout = output_file
        
        try:
            # Display results
            if RICH_AVAILABLE and not args.output:
                display_table_rich(projects_data)
            else:
                display_table_simple(projects_data)
            
            # Generate summary
            generate_summary_stats(projects_data)
            
        finally:
            # Restore stdout and close file if needed
            sys.stdout = original_stdout
            if args.output:
                output_file.close()
                print(f"✅ Report saved to: {args.output}")
        
        # Generate HTML report if requested
        if args.html:
            generate_html_report(projects_data, args.html)
            print(f"✅ HTML report saved to: {args.html}")
        
        print(f"✅ Analysis complete! Processed {len(projects_data)} branch entries.")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 