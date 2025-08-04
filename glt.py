#!/usr/bin/env python3
"""
GitLab Tools CLI (glt) - Unified interface for GitLab management operations.

A Claude Code-inspired CLI that allows natural language commands to execute
GitLab operations through existing scripts.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.cli import __version__
from src.utils import get_logger

logger = get_logger(__name__)


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog='glt',
        description='GitLab Tools CLI - Unified interface for GitLab operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  glt                                    # Start interactive mode
  glt --version                          # Show version
  glt --help                            # Show this help

Interactive Commands (Direct Script Commands):
  > rename_branches --groups "AI-ML-Services" --old-branch trunk --new-branch main
  > generate_executive_dashboard --groups 1721,1267,1269,119 --output dashboard.html
  > generate_executive_dashboard --groups 1721,1267 --days 60 --team-name "AI Team"
  > send_report_email dashboard.html manager@company.com "Weekly Report"
  > sync_issues my-project --use-api --dry-run
  > analyze_projects --project my-project --format json
  > export_analytics my-project --output data.xlsx

Interactive Commands (Natural Language):
  > rename branches in AI-ML-Services from trunk to main
  > create issues for project 123
  > generate weekly report for groups 1,2,3
  > generate executive dashboard for all groups
  > create dashboard for AI team

Executive Dashboard Commands:
  Available Group IDs:
    1721 = AI-ML-Services       (AI/ML projects and services)
    1267 = Research Repos       (Research and experimental projects)
    1269 = Internal Services    (Core platform and infrastructure)
    119  = iland               (iland-specific projects)

  Common Dashboard Commands:
  > generate_executive_dashboard --groups 1721,1267,1269,119
  > generate_executive_dashboard --groups 1721 --days 30 --output ai_dashboard.html
  > generate_executive_dashboard --groups 1721,1267 --team-name "Development Team"
  > python scripts/generate_executive_dashboard.py --groups 1721,1267,1269,119

Special Commands:
  > help                                # Show available commands
  > list-commands                       # List all direct script commands
  > exit                                # Exit the CLI
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'glt {__version__}'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode (for testing)'
    )
    
    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    try:
        if args.non_interactive:
            print("GitLab Tools CLI - Non-interactive mode")
            print("Use 'glt' without --non-interactive for full functionality")
            return 0
        
        # Import REPL here to avoid import errors during setup
        from src.cli.repl import GitLabREPL
        
        repl = GitLabREPL()
        return repl.run()
        
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            raise
        return 1


if __name__ == '__main__':
    sys.exit(main())