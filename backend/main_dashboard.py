#!/usr/bin/env python3
"""Main script for generating executive dashboard using modularized functions."""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

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

# Import our modularized functions
from gitlab_api import get_all_group_ids
from group_analytics import analyze_groups
from database import DatabaseManager
from data_transformer import DataTransformer

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

def get_env_or_exit(key: str, description: str) -> str:
    """Get environment variable or exit with helpful message."""
    value = os.getenv(key)
    if not value:
        safe_print(f"[ERROR] Missing required environment variable: {key}")
        safe_print(f"   {description}")
        sys.exit(1)
    return value

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate executive dashboard for GitLab analytics using modularized functions",
        epilog="""
Examples:
  # Generate dashboard for specific groups
  python scripts/main_dashboard.py --groups 1721,1267,1269 --output dashboard.html

  # Generate 60-day analysis
  python scripts/main_dashboard.py --groups 1721,1267,1269 --days 60 --output dashboard.html

  # Save to database
  python scripts/main_dashboard.py --groups 1721 --save-to-db

  # Custom team name
  python scripts/main_dashboard.py --groups 1721,1267,1269 --team-name "AI Development Team"
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
        default=90,
        help='Number of days to analyze (default: 90)'
    )
    parser.add_argument(
        '--team-name',
        default='Development Team',
        help='Name of the team for the report'
    )
    parser.add_argument(
        '--save-to-db',
        action='store_true',
        help='Save data to PostgreSQL database'
    )
    parser.add_argument(
        '--db-config',
        help='Database configuration file (JSON)'
    )
    
    args = parser.parse_args()

    # Get GitLab configuration
    gitlab_url = get_env_or_exit('GITLAB_URL', 'Your GitLab instance URL')
    gitlab_token = get_env_or_exit('GITLAB_TOKEN', 'Your GitLab API token')

    # Parse group IDs
    if args.all_gitlab_groups:
        safe_print("[INFO] Fetching all group IDs from GitLab...")
        group_ids = get_all_group_ids(gitlab_url, gitlab_token)
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
        group_ids = get_all_group_ids(gitlab_url, gitlab_token)
        if not group_ids:
            safe_print("[ERROR] No groups found in GitLab.")
            return 1
        safe_print(f"[INFO] Using all {len(group_ids)} groups from GitLab.")
    
    if not group_ids:
        safe_print("[ERROR] No group IDs to analyze.")
        return 1
    
    # Initialize database if needed
    db_manager = None
    data_transformer = None
    
    if args.save_to_db:
        safe_print("[INFO] Initializing database connection...")
        
        # Load database configuration
        db_config = None
        if args.db_config:
            try:
                with open(args.db_config, 'r') as f:
                    db_config = json.load(f)
            except Exception as e:
                safe_print(f"[ERROR] Failed to load database config: {e}")
                return 1
        
        db_manager = DatabaseManager(db_config)
        if not db_manager.connect():
            safe_print("[ERROR] Failed to connect to database. Check your database configuration.")
            return 1
        
        data_transformer = DataTransformer(db_manager)
    
    try:
        safe_print(">> Starting executive dashboard generation...")
        safe_print(f"   Analyzing {len(group_ids)} groups over {args.days} days")
        
        # Analyze groups using modularized function
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, args.days)
        # เพิ่ม log debug ก่อน save_all_data
        safe_print(f"[DEBUG] main_dashboard: all_issues count: {len(report_data.get('all_issues', []))}")
        safe_print(f"[DEBUG] main_dashboard: all_commits count: {len(report_data.get('all_commits', []))}")
        safe_print(f"[DEBUG] main_dashboard: all_merge_requests count: {len(report_data.get('all_merge_requests', []))}")
        # Save to database if requested
        if args.save_to_db and data_transformer:
            safe_print(f"[INFO] Saving data to database for period {args.days} days...")
            if not data_transformer.save_all_data(report_data):
                safe_print(f"[ERROR] Failed to save data to database for period {args.days} days")
                return 1
            safe_print(f"[SUCCESS] Data saved to database successfully for period {args.days} days!")
        # Save to file (only for the last period or for all periods if needed)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Save JSON data for further analysis
        json_output_path = output_path.with_suffix('.json')
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        safe_print(f"[SUCCESS] Dashboard data saved to: {json_output_path}")
        
        # Print summary
        summary = report_data['summary']
        safe_print(f"\n[SUMMARY] Analysis Summary:")
        safe_print(f"   Total Projects: {summary['total_projects']}")
        safe_print(f"   Active Projects: {summary['active_projects']}")
        safe_print(f"   Total Commits: {summary['total_commits']}")
        safe_print(f"   Unique Contributors: {summary['unique_contributors']}")
        safe_print(f"   Health Distribution: A+({summary['health_distribution']['A+']}) A({summary['health_distribution']['A']}) B({summary['health_distribution']['B']}) C({summary['health_distribution']['C']}) D({summary['health_distribution']['D']})")
        
        # Show contributor-level code churn summary (add/del/change)
        contributors_detail = report_data.get('contributors_detail', [])
        if contributors_detail:
            safe_print(f"\n[CONTRIBUTOR CODE CHURN]")
            for c in contributors_detail:
                safe_print(f"- {c['name']}: +{c['total_additions']} / -{c['total_deletions']} (Δ {c['total_changes']}) across {len(c['projects'])} projects")
        
        # Show multi-period analysis if available
        if 'cross_period_comparison' in report_data:
            safe_print(f"\n[MULTI-PERIOD] Multi-period analysis completed")
            safe_print(f"   Periods analyzed: 7, 15, 30, 60 days")
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
    finally:
        # Clean up database connection
        if db_manager:
            db_manager.disconnect()

if __name__ == "__main__":
    sys.exit(main()) 