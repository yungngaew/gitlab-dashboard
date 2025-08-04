#!/usr/bin/env python3
"""Check all groups available on GitLab instance."""

import os
import sys
import argparse
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Import our modules
from gitlab_api import get_all_group_ids, simple_gitlab_request

def get_env_or_exit(key: str, description: str) -> str:
    """Get environment variable or exit with helpful message."""
    value = os.getenv(key)
    if not value:
        print(f"[ERROR] Missing required environment variable: {key}")
        print(f"   {description}")
        sys.exit(1)
    return value

def get_detailed_group_info(gitlab_url: str, gitlab_token: str, group_ids: list) -> list:
    """Get detailed information for each group."""
    detailed_groups = []
    
    print(f"[INFO] Fetching detailed information for {len(group_ids)} groups...")
    
    for i, group_id in enumerate(group_ids, 1):
        try:
            # Get detailed group information
            group_info = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"groups/{group_id}",
                {}
            )
            
            if group_info and len(group_info) > 0:
                group = group_info[0]  # API returns list with single item
                
                # Get projects in this group
                projects = simple_gitlab_request(
                    gitlab_url, gitlab_token,
                    f"groups/{group_id}/projects",
                    {"include_subgroups": "true", "archived": "false"}
                )
                
                # Get subgroups
                subgroups = simple_gitlab_request(
                    gitlab_url, gitlab_token,
                    f"groups/{group_id}/subgroups",
                    {}
                )
                
                detailed_group = {
                    'id': group['id'],
                    'name': group['name'],
                    'path': group['path'],
                    'full_path': group.get('full_path', group['path']),
                    'description': group.get('description', ''),
                    'visibility': group.get('visibility', 'private'),
                    'created_at': group.get('created_at', ''),
                    'projects_count': len(projects) if projects else 0,
                    'subgroups_count': len(subgroups) if subgroups else 0,
                    'projects': projects[:5] if projects else [],  # Show first 5 projects
                    'subgroups': subgroups[:5] if subgroups else []  # Show first 5 subgroups
                }
                
                detailed_groups.append(detailed_group)
                print(f"  [{i}/{len(group_ids)}] {group['name']} (ID: {group_id}) - {len(projects)} projects, {len(subgroups)} subgroups")
            
        except Exception as e:
            print(f"  [{i}/{len(group_ids)}] Error fetching group {group_id}: {e}")
            continue
    
    return detailed_groups

def print_group_summary(groups: list):
    """Print summary of all groups."""
    print("\n" + "="*80)
    print("GITLAB GROUPS SUMMARY")
    print("="*80)
    
    total_projects = sum(g['projects_count'] for g in groups)
    total_subgroups = sum(g['subgroups_count'] for g in groups)
    
    print(f"Total Groups: {len(groups)}")
    print(f"Total Projects: {total_projects}")
    print(f"Total Subgroups: {total_subgroups}")
    
    # Group by visibility
    visibility_counts = {}
    for group in groups:
        visibility = group['visibility']
        visibility_counts[visibility] = visibility_counts.get(visibility, 0) + 1
    
    print(f"\nVisibility Distribution:")
    for visibility, count in visibility_counts.items():
        print(f"  {visibility}: {count} groups")
    
    # Top groups by project count
    print(f"\nTop 10 Groups by Project Count:")
    sorted_groups = sorted(groups, key=lambda x: x['projects_count'], reverse=True)
    for i, group in enumerate(sorted_groups[:10], 1):
        print(f"  {i:2d}. {group['name']} (ID: {group['id']}): {group['projects_count']} projects")
    
    # Groups with most subgroups
    print(f"\nTop 10 Groups by Subgroup Count:")
    sorted_by_subgroups = sorted(groups, key=lambda x: x['subgroups_count'], reverse=True)
    for i, group in enumerate(sorted_by_subgroups[:10], 1):
        print(f"  {i:2d}. {group['name']} (ID: {group['id']}): {group['subgroups_count']} subgroups")

def print_detailed_groups(groups: list, show_projects: bool = False, show_subgroups: bool = False):
    """Print detailed information for each group."""
    print("\n" + "="*80)
    print("DETAILED GROUP INFORMATION")
    print("="*80)
    
    for group in groups:
        print(f"\n📁 Group: {group['name']}")
        print(f"   ID: {group['id']}")
        print(f"   Path: {group['full_path']}")
        print(f"   Visibility: {group['visibility']}")
        print(f"   Created: {group['created_at']}")
        print(f"   Projects: {group['projects_count']}")
        print(f"   Subgroups: {group['subgroups_count']}")
        
        if group['description']:
            print(f"   Description: {group['description']}")
        
        if show_projects and group['projects']:
            print(f"   📋 Projects:")
            for project in group['projects']:
                print(f"      - {project['name']} (ID: {project['id']})")
        
        if show_subgroups and group['subgroups']:
            print(f"   📂 Subgroups:")
            for subgroup in group['subgroups']:
                print(f"      - {subgroup['name']} (ID: {subgroup['id']})")

def save_to_file(groups: list, output_file: str):
    """Save group information to file."""
    import json
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(groups, f, indent=2, default=str)
        print(f"\n[SUCCESS] Group information saved to: {output_file}")
    except Exception as e:
        print(f"[ERROR] Failed to save to file: {e}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Check all groups available on GitLab instance",
        epilog="""
Examples:
  # Check all groups
  python scripts/check_groups.py

  # Check with detailed output
  python scripts/check_groups.py --detailed

  # Show projects and subgroups
  python scripts/check_groups.py --show-projects --show-subgroups

  # Save to file
  python scripts/check_groups.py --output groups.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed information for each group'
    )
    parser.add_argument(
        '--show-projects',
        action='store_true',
        help='Show projects in each group'
    )
    parser.add_argument(
        '--show-subgroups',
        action='store_true',
        help='Show subgroups in each group'
    )
    parser.add_argument(
        '--output', '-o',
        help='Save group information to file (JSON format)'
    )
    
    args = parser.parse_args()

    # Get GitLab configuration
    gitlab_url = get_env_or_exit('GITLAB_URL', 'Your GitLab instance URL')
    gitlab_token = get_env_or_exit('GITLAB_TOKEN', 'Your GitLab API token')

    print(f"[INFO] Checking groups on GitLab: {gitlab_url}")
    
    try:
        # Get all group IDs
        print("[INFO] Fetching all group IDs...")
        group_ids = get_all_group_ids(gitlab_url, gitlab_token)
        
        if not group_ids:
            print("[WARNING] No groups found on GitLab instance")
            return 0
        
        print(f"[INFO] Found {len(group_ids)} groups")
        
        # Get detailed information
        detailed_groups = get_detailed_group_info(gitlab_url, gitlab_token, group_ids)
        
        # Print summary
        print_group_summary(detailed_groups)
        
        # Print detailed information if requested
        if args.detailed:
            print_detailed_groups(
                detailed_groups, 
                show_projects=args.show_projects,
                show_subgroups=args.show_subgroups
            )
        
        # Save to file if requested
        if args.output:
            save_to_file(detailed_groups, args.output)
        
        print(f"\n[SUCCESS] Group check completed!")
        print(f"Found {len(detailed_groups)} groups with {sum(g['projects_count'] for g in detailed_groups)} total projects")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n[CANCELLED] Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 