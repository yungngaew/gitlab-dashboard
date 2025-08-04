#!/usr/bin/env python3
"""Enhanced GitLab issue creation script with templates and bulk import."""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import GitLabClient
from src.services import IssueService
from src.models import IssueCreate, IssueType
from src.utils import Config, setup_logging, get_logger, ProgressTracker
from src.utils.logger import Colors
from src.utils.validators import ValidationError


logger = get_logger(__name__)


class IssueCreator:
    """Handles issue creation operations."""
    
    def __init__(self, client: GitLabClient, config: Config):
        """Initialize issue creator.
        
        Args:
            client: GitLab API client
            config: Configuration instance
        """
        self.client = client
        self.config = config
        self.service = IssueService(client)
        self.service.config = config
    
    def load_custom_templates(self):
        """Load custom templates from templates directory."""
        template_dir = Path(self.config.get('issue_operations.template_dir', 'templates/issues'))
        
        if not template_dir.exists():
            logger.debug(f"Template directory not found: {template_dir}")
            return
        
        for template_file in template_dir.glob('*.yaml'):
            try:
                self.service.load_template_from_file(template_file)
                logger.info(f"Loaded template: {template_file.stem}")
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")
    
    def list_templates(self):
        """List available templates."""
        print(f"\n{Colors.BOLD}Available Templates:{Colors.RESET}")
        print("=" * 60)
        
        for name, template in sorted(self.service.templates.items()):
            print(f"\n{Colors.CYAN}{name}{Colors.RESET}")
            print(f"  Title: {template.title_template}")
            
            if template.default_labels:
                print(f"  Labels: {', '.join(template.default_labels)}")
            
            if template.required_variables:
                print(f"  Required vars: {', '.join(template.required_variables)}")
            
            if template.optional_variables:
                print(f"  Optional vars: {', '.join(template.optional_variables)}")
    
    def interactive_mode(self, project_id: Union[int, str], dry_run: bool = False):
        """Interactive mode for creating issues."""
        print(f"\n{Colors.BOLD}Interactive Issue Creation{Colors.RESET}")
        print("=" * 60)
        
        # Choose template or manual
        print("\nOptions:")
        print("1. Create from template")
        print("2. Create manually")
        print("3. Import from file")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            self._create_from_template_interactive(project_id, dry_run)
        elif choice == '2':
            self._create_manual_interactive(project_id, dry_run)
        elif choice == '3':
            self._import_interactive(project_id, dry_run)
        else:
            print(f"{Colors.RED}Invalid choice{Colors.RESET}")
    
    def _create_from_template_interactive(self, project_id: Union[int, str], dry_run: bool):
        """Interactive template-based creation."""
        # List templates
        self.list_templates()
        
        template_name = input("\nSelect template name: ").strip()
        
        if template_name not in self.service.templates:
            print(f"{Colors.RED}Template '{template_name}' not found{Colors.RESET}")
            return
        
        template = self.service.templates[template_name]
        
        # Collect variables
        variables = {}
        
        print(f"\n{Colors.BOLD}Enter template variables:{Colors.RESET}")
        
        # Required variables
        for var in template.required_variables:
            value = input(f"  {var} (required): ").strip()
            if not value:
                print(f"{Colors.RED}Required variable cannot be empty{Colors.RESET}")
                return
            variables[var] = value
        
        # Optional variables
        for var in template.optional_variables:
            value = input(f"  {var} (optional): ").strip()
            if value:
                variables[var] = value
        
        # Additional options
        labels_input = input("\nAdditional labels (comma-separated): ").strip()
        additional_labels = [l.strip() for l in labels_input.split(',') if l.strip()]
        
        # Create issue
        issue_data = IssueCreate(
            title="",  # Will be set by template
            template_variables=variables,
            labels=additional_labels
        )
        
        try:
            issue = self.service.create_issue(
                project_id,
                issue_data,
                template_name,
                dry_run
            )
            
            if issue:
                print(f"\n{Colors.GREEN}✓ Created issue #{issue.iid}: {issue.title}{Colors.RESET}")
                print(f"  URL: {issue.web_url}")
            elif dry_run:
                print(f"\n{Colors.YELLOW}[DRY RUN] Would create issue from template '{template_name}'{Colors.RESET}")
        
        except Exception as e:
            print(f"\n{Colors.RED}✗ Failed to create issue: {e}{Colors.RESET}")
    
    def _create_manual_interactive(self, project_id: Union[int, str], dry_run: bool):
        """Interactive manual creation."""
        print(f"\n{Colors.BOLD}Manual Issue Creation{Colors.RESET}")
        
        # Collect issue data
        title = input("Title: ").strip()
        if not title:
            print(f"{Colors.RED}Title is required{Colors.RESET}")
            return
        
        description = input("Description (optional): ").strip()
        
        labels_input = input("Labels (comma-separated): ").strip()
        labels = [l.strip() for l in labels_input.split(',') if l.strip()]
        
        due_date = input("Due date (YYYY-MM-DD, optional): ").strip()
        
        weight = input("Weight (0-200, optional): ").strip()
        
        # Create issue data
        issue_data = {
            'title': title,
            'labels': labels
        }
        
        if description:
            issue_data['description'] = description
        
        if due_date:
            issue_data['due_date'] = due_date
        
        if weight:
            issue_data['weight'] = int(weight)
        
        try:
            issue = self.service.create_issue(
                project_id,
                issue_data,
                dry_run=dry_run
            )
            
            if issue:
                print(f"\n{Colors.GREEN}✓ Created issue #{issue.iid}: {issue.title}{Colors.RESET}")
                print(f"  URL: {issue.web_url}")
            elif dry_run:
                print(f"\n{Colors.YELLOW}[DRY RUN] Would create issue: {title}{Colors.RESET}")
        
        except Exception as e:
            print(f"\n{Colors.RED}✗ Failed to create issue: {e}{Colors.RESET}")
    
    def _import_interactive(self, project_id: Union[int, str], dry_run: bool):
        """Interactive file import."""
        print(f"\n{Colors.BOLD}Import Issues from File{Colors.RESET}")
        
        file_path = input("File path (CSV/JSON/TXT): ").strip()
        
        if not Path(file_path).exists():
            print(f"{Colors.RED}File not found: {file_path}{Colors.RESET}")
            return
        
        template_name = input("Template to apply (optional): ").strip() or None
        
        self.import_from_file(project_id, file_path, template_name, dry_run)
    
    def import_from_file(
        self,
        project_id: Union[int, str],
        file_path: str,
        template_name: Optional[str] = None,
        dry_run: bool = False
    ):
        """Import issues from file."""
        path = Path(file_path)
        
        try:
            if path.suffix.lower() == '.csv':
                results = self.service.import_from_csv(
                    project_id, path, template_name, dry_run
                )
            elif path.suffix.lower() == '.json':
                results = self.service.import_from_json(
                    project_id, path, template_name, dry_run
                )
            elif path.suffix.lower() == '.txt':
                # Legacy text format
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                issues_data = self.service.parse_text_format(content)
                results = self.service.create_issues_bulk(
                    project_id, issues_data, template_name, dry_run
                )
            else:
                print(f"{Colors.RED}Unsupported file format: {path.suffix}{Colors.RESET}")
                return
            
            # Print results
            print(f"\n{Colors.BOLD}Import Summary:{Colors.RESET}")
            print(f"Total issues: {results['total']}")
            print(f"{Colors.GREEN}Created: {results['created']}{Colors.RESET}")
            print(f"{Colors.RED}Failed: {results['failed']}{Colors.RESET}")
            
            if results['errors']:
                print(f"\n{Colors.RED}Errors:{Colors.RESET}")
                for error in results['errors']:
                    print(f"  - {error}")
        
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            print(f"{Colors.RED}Import failed: {e}{Colors.RESET}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Enhanced GitLab issue creation with templates and bulk import"
    )
    
    # Project selection
    parser.add_argument(
        'project',
        nargs='?',
        help='GitLab project name or ID'
    )
    
    # Operation modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode'
    )
    mode_group.add_argument(
        '--import', '-I',
        dest='import_file',
        help='Import issues from file (CSV/JSON/TXT)'
    )
    mode_group.add_argument(
        '--template', '-t',
        help='Create issue from template'
    )
    mode_group.add_argument(
        '--list-templates',
        action='store_true',
        help='List available templates'
    )
    
    # Issue data (for non-interactive mode)
    parser.add_argument(
        '--title',
        help='Issue title'
    )
    parser.add_argument(
        '--description', '-d',
        help='Issue description'
    )
    parser.add_argument(
        '--labels', '-l',
        nargs='+',
        help='Issue labels'
    )
    parser.add_argument(
        '--due-date',
        help='Due date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--weight', '-w',
        type=int,
        help='Issue weight (0-200)'
    )
    
    # Template variables
    parser.add_argument(
        '--vars', '-v',
        action='append',
        help='Template variables (format: key=value)'
    )
    
    # Options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview without creating issues'
    )
    parser.add_argument(
        '--config', '-c',
        help='Configuration file path'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    # Parse arguments
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
        
        # Create GitLab client
        gitlab_config = config.get_gitlab_config()
        client = GitLabClient(
            url=gitlab_config['url'],
            token=gitlab_config['token'],
            config=gitlab_config
        )
        
        # Create issue creator
        creator = IssueCreator(client, config)
        creator.load_custom_templates()
        
        # Handle list templates
        if args.list_templates:
            creator.list_templates()
            return 0
        
        # Get project
        if not args.project:
            # List available projects
            print("Fetching available projects...")
            projects = list(client.get_projects(membership=True))
            
            if not projects:
                logger.error("No projects found")
                return 1
            
            print(f"\n{Colors.BOLD}Available Projects:{Colors.RESET}")
            for i, project in enumerate(projects[:20], 1):
                print(f"{i}. {project['name']} ({project['path_with_namespace']})")
            
            if len(projects) > 20:
                print(f"... and {len(projects) - 20} more")
            
            choice = input("\nSelect project number or enter project name/ID: ").strip()
            
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                project_id = projects[int(choice) - 1]['id']
            else:
                project_id = choice
        else:
            project_id = args.project
        
        # Verify project exists
        try:
            project = client.get_project(project_id)
            print(f"\nUsing project: {project['name']} ({project['path_with_namespace']})")
        except Exception as e:
            logger.error(f"Failed to access project: {e}")
            return 1
        
        # Handle different modes
        if args.interactive or (not args.import_file and not args.title):
            creator.interactive_mode(project['id'], args.dry_run)
        
        elif args.import_file:
            creator.import_from_file(
                project['id'],
                args.import_file,
                args.template,
                args.dry_run
            )
        
        else:
            # Create single issue from command line
            issue_data = {
                'title': args.title
            }
            
            if args.description:
                issue_data['description'] = args.description
            
            if args.labels:
                issue_data['labels'] = args.labels
            
            if args.due_date:
                issue_data['due_date'] = args.due_date
            
            if args.weight is not None:
                issue_data['weight'] = args.weight
            
            # Parse template variables
            if args.vars:
                template_vars = {}
                for var in args.vars:
                    if '=' in var:
                        key, value = var.split('=', 1)
                        template_vars[key] = value
                issue_data['template_variables'] = template_vars
            
            try:
                issue = creator.service.create_issue(
                    project['id'],
                    issue_data,
                    args.template,
                    args.dry_run
                )
                
                if issue:
                    print(f"\n{Colors.GREEN}✓ Created issue #{issue.iid}: {issue.title}{Colors.RESET}")
                    print(f"  URL: {issue.web_url}")
                elif args.dry_run:
                    print(f"\n{Colors.YELLOW}[DRY RUN] Would create issue{Colors.RESET}")
            
            except Exception as e:
                logger.error(f"Failed to create issue: {e}")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())