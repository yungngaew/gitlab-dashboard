#!/usr/bin/env python3
"""Generate markdown table of issue assignments by member."""

import argparse
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.api import GitLabClient
from src.models.issue import Issue
from src.utils import Config, setup_logging, get_logger
from src.utils.progress import progress_context
from src.services.board_service import BoardService


def main():
    """Main function to generate issue assignment report."""
    parser = argparse.ArgumentParser(
        description="Generate markdown table of issue assignments by member"
    )
    parser.add_argument(
        "project_id",
        help="GitLab project ID or path (e.g., 12345 or group/project)"
    )
    parser.add_argument(
        "-o", "--output",
        default="issue_assignments.md",
        help="Output markdown file (default: issue_assignments.md)"
    )
    parser.add_argument(
        "-g", "--group",
        action="store_true",
        help="Treat ID as group ID and get issues from all projects in group"
    )
    parser.add_argument(
        "--include-unassigned",
        action="store_true",
        help="Include unassigned issues in the report"
    )
    parser.add_argument(
        "--use-board-labels",
        action="store_true",
        default=True,
        help="Use GitLab board labels to determine issue states (default: True)"
    )
    parser.add_argument(
        "--no-board-labels",
        action="store_true",
        help="Disable board label usage and use simple assignee-based logic"
    )
    parser.add_argument(
        "--board-id",
        type=int,
        help="Specific board ID to use for label mappings (uses default board if not specified)"
    )
    
    args = parser.parse_args()
    
    # Setup
    config = Config()
    setup_logging(config.get_log_config())
    logger = get_logger(__name__)
    
    try:
        # Validate configuration
        config.validate()
        
        # Create GitLab client
        gitlab_config = config.get_gitlab_config()
        client = GitLabClient(
            url=gitlab_config['url'],
            token=gitlab_config['token'],
            config=gitlab_config
        )
        
        # Determine if we should use board labels
        use_board_labels = args.use_board_labels and not args.no_board_labels
        
        # Create board service if using board labels
        board_service = None
        board_info = None
        if use_board_labels:
            board_service = BoardService(client, config.to_dict())
        
        # Fetch issues
        logger.info(f"Fetching issues from {'group' if args.group else 'project'} {args.project_id}")
        
        issues = []
        if args.group:
            # Get all projects in group
            with progress_context("Fetching projects from group"):
                projects = list(client.get_projects(group_id=args.project_id))
            
            total_projects = len(projects)
            logger.info(f"Found {total_projects} projects in group")
            
            for idx, project in enumerate(projects):
                logger.info(f"Fetching issues from project {idx + 1}/{total_projects}: {project['name']}")
                project_issues = list(client.get_issues(
                    project_id=project['id'],
                    state='opened'
                ))
                issues.extend(project_issues)
        else:
            # Get issues from single project
            with progress_context("Fetching issues"):
                issues = list(client.get_issues(
                    project_id=args.project_id,
                    state='opened'
                ))
        
        logger.info(f"Found {len(issues)} open issues")
        
        # Process issues
        issue_models = [Issue.from_gitlab_response(issue_data) for issue_data in issues]
        
        # Count by assignee and state
        assignee_stats = defaultdict(lambda: defaultdict(int))
        workflow_stats = defaultdict(int)
        
        # Get board info and workflow labels if using board labels
        workflow_labels = {}
        if use_board_labels and board_service and not args.group:
            # For single project, get board info
            if args.board_id:
                board_info = {'id': args.board_id, 'name': 'Specified Board'}
            else:
                board_info = board_service.get_default_board(args.project_id)
            
            if board_info:
                logger.info(f"Using board: {board_info.get('name', 'Unknown')} (ID: {board_info['id']})")
                workflow_labels = board_service.get_board_workflow_labels(args.project_id, board_info['id'])
        
        for idx, issue in enumerate(issue_models):
            # Determine workflow state
            if use_board_labels and board_service:
                # Use the raw issue data for label checking
                workflow_state = board_service.get_issue_workflow_state(issues[idx], workflow_labels)
            else:
                # Legacy behavior: assignee = in_progress, no assignee = open
                workflow_state = 'in_progress' if issue.assignee else 'to_do'
            
            # Only count issues that are in active workflow states (not completed)
            if workflow_state not in ['to_do', 'in_progress']:
                continue
            
            workflow_stats[workflow_state] += 1
            
            # Track by assignee
            if issue.assignee:
                assignee_name = issue.assignee.get('name', issue.assignee.get('username', 'Unknown'))
                assignee_id = issue.assignee.get('id', 0)
                assignee_stats[(assignee_id, assignee_name)][workflow_state] += 1
            elif args.include_unassigned:
                assignee_stats[(0, 'Unassigned')][workflow_state] += 1
        
        # Generate markdown table
        generate_markdown_report(
            assignee_stats, 
            args.output, 
            args.project_id, 
            args.group,
            workflow_stats,
            board_info,
            use_board_labels
        )
        
        logger.info(f"Report saved to {args.output}")
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        sys.exit(1)


def generate_markdown_report(
    assignee_stats: Dict[Tuple[int, str], Dict[str, int]], 
    output_file: str,
    project_id: str,
    is_group: bool,
    workflow_stats: Dict[str, int],
    board_info: Optional[Dict] = None,
    use_board_labels: bool = False
) -> None:
    """Generate markdown file with issue assignment table."""
    with open(output_file, 'w') as f:
        # Header
        f.write("# Issue Assignment Report\n\n")
        f.write(f"**{'Group' if is_group else 'Project'}**: {project_id}\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if use_board_labels and board_info:
            f.write(f"**Board**: {board_info.get('name', 'Unknown')} (ID: {board_info['id']})\n")
        f.write("\n")
        
        # Summary stats
        total_issues = sum(workflow_stats.values())
        
        f.write("## Summary\n\n")
        f.write(f"- **Total Open Issues**: {total_issues}\n")
        
        if use_board_labels:
            # Show workflow state breakdown (only active states)
            f.write("\n### Workflow State Breakdown:\n")
            state_order = ['to_do', 'in_progress']
            for state in state_order:
                if state in workflow_stats and workflow_stats[state] > 0:
                    # Map 'to_do' to 'Open' for display
                    state_display = 'Open' if state == 'to_do' else state.replace('_', ' ').title()
                    f.write(f"- **{state_display}**: {workflow_stats[state]}\n")
        else:
            # Legacy stats
            total_assigned = sum(sum(stats.values()) for (_, _), stats in assignee_stats.items() if _ != 0)
            total_unassigned = assignee_stats.get((0, 'Unassigned'), {}).get('to_do', 0)
            f.write(f"- **Assigned Issues**: {total_assigned}\n")
            f.write(f"- **Unassigned Issues**: {total_unassigned}\n")
        
        f.write("\n")
        
        # Table
        f.write("## Issue Assignments by Member\n\n")
        
        if use_board_labels:
            # Only show active workflow states in table
            states_with_issues = [s for s in ['to_do', 'in_progress'] 
                                if any(s in stats for stats in assignee_stats.values())]
            
            # Table header
            f.write("| ID | Assignee |")
            for state in states_with_issues:
                # Map 'to_do' to 'Open' for display
                state_display = 'Open' if state == 'to_do' else state.replace('_', ' ').title()
                f.write(f" {state_display} |")
            f.write(" Total |\n")
            
            # Separator
            f.write("|:---|:---------|")
            for _ in states_with_issues:
                f.write("------:|")
            f.write("------:|\n")
            
            # Sort by total issues (descending)
            sorted_assignees = sorted(
                assignee_stats.items(),
                key=lambda x: sum(x[1].values()),
                reverse=True
            )
            
            # Data rows
            for (assignee_id, assignee_name), stats in sorted_assignees:
                f.write(f"| {assignee_id} | {assignee_name} |")
                for state in states_with_issues:
                    f.write(f" {stats.get(state, 0)} |")
                f.write(f" {sum(stats.values())} |\n")
        else:
            # Legacy table format
            f.write("| ID | Assignee | Open Issues | In-Progress Issues |\n")
            f.write("|:---|:---------|------------:|-------------------:|\n")
            
            sorted_assignees = sorted(
                assignee_stats.items(),
                key=lambda x: sum(x[1].values()),
                reverse=True
            )
            
            for (assignee_id, assignee_name), stats in sorted_assignees:
                open_count = stats.get('to_do', 0)
                in_progress_count = stats.get('in_progress', 0)
                f.write(f"| {assignee_id} | {assignee_name} | {open_count} | {in_progress_count} |\n")
        
        # Footer
        f.write("\n---\n")
        if use_board_labels:
            f.write("*Note: Issue states are determined by GitLab board labels.*\n")
        else:
            f.write("*Note: Issues with assignees are considered \"In-Progress\", ")
            f.write("while issues without assignees are considered \"Open\".*\n")


if __name__ == "__main__":
    main()