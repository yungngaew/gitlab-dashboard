#!/usr/bin/env python3
"""
Sync markdown files from issues folder to GitLab issues.

This script reads markdown files from the 'issues' folder and creates
GitLab issues using curl commands or the GitLab API.
"""

import os
import sys
import re
import subprocess
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import Config, get_logger

logger = get_logger(__name__)


class IssueFile:
    """Represents an issue file with metadata and content."""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.title = ""
        self.description = ""
        self.labels = []
        self.assignee = None
        self.milestone = None
        self.due_date = None
        self.weight = None
        self.priority = None
        
        self._parse_file()
    
    def _parse_file(self):
        """Parse markdown file for issue content and metadata."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                self._parse_frontmatter(parts[1])
                body = parts[2].strip()
            else:
                body = content
        else:
            body = content
        
        # If no title in frontmatter, use first heading or filename
        if not self.title:
            # Try to find first heading
            heading_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
            if heading_match:
                self.title = heading_match.group(1).strip()
                # Remove the heading from body
                body = body.replace(heading_match.group(0), '', 1).strip()
            else:
                # Use filename without extension
                self.title = self.filepath.stem.replace('-', ' ').replace('_', ' ').title()
        
        self.description = body.strip()
        
        # Extract labels from hashtags in content
        hashtags = re.findall(r'#(\w+)', body)
        self.labels.extend(hashtags)
        
        # Remove duplicate labels
        self.labels = list(set(self.labels))
    
    def _parse_frontmatter(self, frontmatter: str):
        """Parse YAML frontmatter for metadata."""
        import yaml
        try:
            data = yaml.safe_load(frontmatter)
            if data:
                self.title = data.get('title', '')
                self.labels = data.get('labels', [])
                if isinstance(self.labels, str):
                    self.labels = [l.strip() for l in self.labels.split(',')]
                self.assignee = data.get('assignee')
                self.milestone = data.get('milestone')
                self.due_date = data.get('due_date')
                self.weight = data.get('weight')
                self.priority = data.get('priority')
        except:
            # If YAML parsing fails, continue without frontmatter
            pass
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API/curl."""
        data = {
            'title': self.title,
            'description': self.description
        }
        
        if self.labels:
            data['labels'] = ','.join(self.labels)
        
        if self.assignee:
            data['assignee'] = self.assignee
            
        if self.milestone:
            data['milestone'] = self.milestone
            
        if self.due_date:
            data['due_date'] = self.due_date
            
        if self.weight:
            data['weight'] = self.weight
            
        return data


def get_issue_files(issues_dir: Path) -> List[IssueFile]:
    """Get all issue files from the issues directory."""
    issue_files = []
    
    # Support .md and .txt files
    for pattern in ['*.md', '*.txt', '*.markdown']:
        for filepath in issues_dir.glob(pattern):
            if filepath.is_file():
                try:
                    issue_file = IssueFile(filepath)
                    issue_files.append(issue_file)
                    logger.info(f"Loaded issue: {issue_file.title}")
                except Exception as e:
                    logger.error(f"Failed to parse {filepath}: {e}")
    
    return issue_files


def generate_curl_command(
    issue: IssueFile,
    gitlab_url: str,
    project_id: str,
    token: str
) -> str:
    """Generate curl command for creating an issue."""
    api_url = f"{gitlab_url}/api/v4/projects/{project_id}/issues"
    
    # Build curl command
    cmd_parts = [
        'curl',
        '--request', 'POST',
        f'"{api_url}"',
        '--header', f'"PRIVATE-TOKEN: {token}"'
    ]
    
    # Add form data
    data = issue.to_dict()
    for key, value in data.items():
        # Escape quotes in value
        escaped_value = str(value).replace('"', '\\"')
        cmd_parts.extend(['--form', f'"{key}={escaped_value}"'])
    
    return ' \\\n     '.join(cmd_parts)


def create_issue_with_curl(
    issue: IssueFile,
    gitlab_url: str,
    project_id: str,
    token: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Create issue using curl command."""
    api_url = f"{gitlab_url}/api/v4/projects/{project_id}/issues"
    
    # Build curl command as list for subprocess
    cmd = [
        'curl',
        '--request', 'POST',
        api_url,
        '--header', f'PRIVATE-TOKEN: {token}',
        '--silent',
        '--show-error'
    ]
    
    # Add form data
    data = issue.to_dict()
    for key, value in data.items():
        cmd.extend(['--form', f'{key}={value}'])
    
    if dry_run:
        # Just return the command that would be executed
        return True, ' '.join(cmd)
    
    try:
        # Execute curl command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse response
        response = json.loads(result.stdout)
        issue_url = response.get('web_url', '')
        issue_id = response.get('iid', '')
        
        return True, f"Created issue #{issue_id}: {issue_url}"
        
    except subprocess.CalledProcessError as e:
        return False, f"Curl failed: {e.stderr}"
    except json.JSONDecodeError:
        return False, f"Invalid response: {result.stdout}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def create_issue_with_api(
    issue: IssueFile,
    gitlab_url: str,
    project_id: str,
    token: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Create issue using GitLab API directly."""
    if dry_run:
        return True, f"Would create issue: {issue.title}"
    
    try:
        from src.api import GitLabClient
        
        client = GitLabClient(url=gitlab_url, token=token)
        
        # Create issue
        response = client.create_issue(
            project_id,
            **issue.to_dict()
        )
        
        issue_url = response.get('web_url', '')
        issue_id = response.get('iid', '')
        
        return True, f"Created issue #{issue_id}: {issue_url}"
        
    except Exception as e:
        return False, f"API Error: {str(e)}"


def sync_issues(
    issues_dir: Path,
    gitlab_url: str,
    project_id: str,
    token: str,
    use_curl: bool = True,
    dry_run: bool = False,
    generate_script: bool = False
) -> Dict[str, any]:
    """Sync all issues from directory to GitLab."""
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    # Get all issue files
    issue_files = get_issue_files(issues_dir)
    results['total'] = len(issue_files)
    
    if not issue_files:
        logger.warning(f"No issue files found in {issues_dir}")
        return results
    
    print(f"\nFound {len(issue_files)} issue files to process\n")
    
    # Generate shell script if requested
    if generate_script:
        script_path = issues_dir / 'create_issues.sh'
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# GitLab Issue Creation Script\n")
            f.write(f"# Generated from markdown files in {issues_dir}\n\n")
            
            for issue in issue_files:
                f.write(f"echo 'Creating issue: {issue.title}'\n")
                f.write(generate_curl_command(issue, gitlab_url, project_id, token))
                f.write("\n\n")
        
        os.chmod(script_path, 0o755)
        print(f"Generated script: {script_path}")
        return results
    
    # Process each issue
    for i, issue_file in enumerate(issue_files, 1):
        print(f"[{i}/{len(issue_files)}] Processing: {issue_file.filename}")
        print(f"  Title: {issue_file.title}")
        
        if issue_file.labels:
            print(f"  Labels: {', '.join(issue_file.labels)}")
        
        # Create issue
        if use_curl:
            success, message = create_issue_with_curl(
                issue_file, gitlab_url, project_id, token, dry_run
            )
        else:
            success, message = create_issue_with_api(
                issue_file, gitlab_url, project_id, token, dry_run
            )
        
        if success:
            results['success'] += 1
            print(f"  ✓ {message}")
        else:
            results['failed'] += 1
            results['errors'].append(f"{issue_file.filename}: {message}")
            print(f"  ✗ {message}")
        
        print()
    
    return results


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Sync markdown files from issues folder to GitLab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example issue file (issues/user-authentication.md):
---
title: Implement User Authentication
labels: [feature, security, high-priority]
assignee: john.doe
milestone: v1.0
due_date: 2024-02-01
weight: 8
---

## Description
Implement a secure user authentication system with the following features:

- User registration with email verification
- Login/logout functionality  
- Password reset via email
- Session management
- OAuth integration (Google, Facebook)

## Acceptance Criteria
- Users can register with email/password
- Email verification is required
- Passwords are securely hashed
- Sessions expire after 24 hours

#backend #api #authentication
"""
    )
    
    parser.add_argument(
        'project',
        help='GitLab project ID or path'
    )
    
    parser.add_argument(
        '--issues-dir',
        default='issues',
        help='Directory containing issue files (default: issues)'
    )
    
    parser.add_argument(
        '--use-api',
        action='store_true',
        help='Use GitLab API directly instead of curl'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview without creating issues'
    )
    
    parser.add_argument(
        '--generate-script',
        action='store_true',
        help='Generate a shell script with curl commands'
    )
    
    parser.add_argument(
        '--config',
        help='Configuration file path'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config(args.config)
    
    try:
        # Get GitLab settings
        gitlab_config = config.get_gitlab_config()
        gitlab_url = gitlab_config['url'].rstrip('/')
        token = gitlab_config['token']
        
        # Get issues directory
        issues_dir = Path(args.issues_dir)
        if not issues_dir.exists():
            print(f"Error: Issues directory not found: {issues_dir}")
            return 1
        
        print(f"GitLab URL: {gitlab_url}")
        print(f"Project: {args.project}")
        print(f"Issues directory: {issues_dir}")
        print(f"Mode: {'API' if args.use_api else 'curl'}")
        
        if args.dry_run:
            print("\n🔍 DRY RUN MODE - No issues will be created\n")
        
        # Sync issues
        results = sync_issues(
            issues_dir=issues_dir,
            gitlab_url=gitlab_url,
            project_id=args.project,
            token=token,
            use_curl=not args.use_api,
            dry_run=args.dry_run,
            generate_script=args.generate_script
        )
        
        # Print summary
        if not args.generate_script:
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            print(f"Total files: {results['total']}")
            print(f"✓ Success: {results['success']}")
            print(f"✗ Failed: {results['failed']}")
            
            if results['errors']:
                print("\nErrors:")
                for error in results['errors']:
                    print(f"  - {error}")
        
        return 0 if results['failed'] == 0 else 1
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())