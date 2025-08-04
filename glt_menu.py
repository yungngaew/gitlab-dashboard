#!/usr/bin/env python3
"""
GitLab Tools Menu Interface - Simple numbered menu for GitLab operations.

This provides an alternative to the command-line interface with a simple
numbered menu system.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class Colors:
    """ANSI color codes matching Claude Code's theme."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Primary colors
    WHITE = '\033[97m'
    BLACK = '\033[30m'
    
    # Status colors
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    
    # Muted colors
    GRAY = '\033[90m'
    DARK_GRAY = '\033[37m'
    
    @classmethod
    def disable_if_no_color(cls):
        """Disable colors if stdout is not a TTY."""
        if not sys.stdout.isatty():
            for attr in dir(cls):
                if not attr.startswith('_') and attr != 'disable_if_no_color':
                    setattr(cls, attr, '')


class BoxChars:
    """Unicode box-drawing characters for professional borders."""
    TOP_LEFT = '╭'
    TOP_RIGHT = '╮'
    BOTTOM_LEFT = '╰'
    BOTTOM_RIGHT = '╯'
    HORIZONTAL = '─'
    VERTICAL = '│'
    CROSS = '┼'
    T_DOWN = '┬'
    T_UP = '┴'
    T_RIGHT = '├'
    T_LEFT = '┤'


class GitLabMenu:
    """Simple menu interface for GitLab tools."""
    
    def __init__(self):
        """Initialize the menu system."""
        self.config = Config()
        self.dry_run = False
        self.box_width = 70  # Default box width
        
        # Initialize colors
        Colors.disable_if_no_color()
        
        # Define menu options with emojis, descriptions, and handlers
        self.menu_options = [
            ("🔄", "Rename Branches", "Rename branches across multiple projects in groups", self.rename_branches),
            ("📊", "Generate Executive Dashboard", "Create HTML dashboards with analytics and metrics", self.generate_dashboard),
            ("📅", "Generate Weekly Report", "Create team productivity reports for weekly syncs", self.weekly_report),
            ("📧", "Send Report Email", "Email HTML reports to team members", self.send_email),
            ("🎯", "Create Issues", "Create GitLab issues interactively or from templates", self.create_issues),
            ("📋", "List Project Issues", "Generate markdown table of issue assignments by member", self.list_project_issues),
            ("📈", "Analyze Projects", "Deep analysis of projects and groups with insights", self.analyze_projects),
            ("💾", "Export Analytics", "Export project data to Excel or JSON formats", self.export_analytics),
            ("📋", "Generate Code Changes Report", "Analyze code changes with lines added/removed metrics", self.code_changes_report),
            ("👋", "Exit", "Exit the program", self.exit_program)
        ]
    
    def draw_box(self, lines: List[str], width: Optional[int] = None, color: str = Colors.GRAY) -> None:
        """Draw a box around the given lines of text."""
        if width is None:
            width = self.box_width
        
        # Print top border
        print(f"{color}{BoxChars.TOP_LEFT}{BoxChars.HORIZONTAL * (width - 2)}{BoxChars.TOP_RIGHT}{Colors.RESET}")
        
        # Print content lines
        for line in lines:
            # Strip ANSI codes to calculate actual length
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line)
            
            padding = width - len(clean_line) - 4  # 4 for "│ " and " │"
            print(f"{color}{BoxChars.VERTICAL}{Colors.RESET} {line}{' ' * padding} {color}{BoxChars.VERTICAL}{Colors.RESET}")
        
        # Print bottom border
        print(f"{color}{BoxChars.BOTTOM_LEFT}{BoxChars.HORIZONTAL * (width - 2)}{BoxChars.BOTTOM_RIGHT}{Colors.RESET}")
    
    def center_text(self, text: str, width: int) -> str:
        """Center text within the given width."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', text)
        padding = (width - len(clean_text)) // 2
        return f"{' ' * padding}{text}"
    
    def pad_text(self, text: str, width: int, align: str = 'left') -> str:
        """Pad text to the given width."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', text)
        padding_needed = width - len(clean_text)
        
        if align == 'center':
            left_pad = padding_needed // 2
            right_pad = padding_needed - left_pad
            return f"{' ' * left_pad}{text}{' ' * right_pad}"
        elif align == 'right':
            return f"{' ' * padding_needed}{text}"
        else:  # left
            return f"{text}{' ' * padding_needed}"
    
    def clear_screen(self):
        """Clear the terminal screen."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_header(self):
        """Display the menu header."""
        import os
        cwd = os.getcwd()
        
        # Welcome box content
        lines = [
            f"{Colors.BOLD}{Colors.WHITE}✻ Welcome to GitLab Tools!{Colors.RESET}",
            "",
            f"{Colors.GRAY}Type a number to select an option{Colors.RESET}",
            "",
            f"{Colors.DIM}{Colors.GRAY}cwd: {cwd}{Colors.RESET}"
        ]
        
        print()  # Add spacing
        self.draw_box(lines, color=Colors.GRAY)
        
        # Show dry-run warning if enabled
        if self.dry_run:
            print()
            warning_lines = [
                f"{Colors.YELLOW}{Colors.BOLD}⚠️  DRY-RUN MODE ENABLED{Colors.RESET}",
                f"{Colors.GRAY}No changes will be made to your GitLab instance{Colors.RESET}"
            ]
            self.draw_box(warning_lines, color=Colors.YELLOW)
    
    def show_menu(self):
        """Display the menu options."""
        print()
        
        # Build menu lines
        menu_lines = []
        menu_lines.append(f"{Colors.BOLD}{Colors.WHITE}Available Options:{Colors.RESET}")
        menu_lines.append("")
        
        for idx, (emoji, name, desc, _) in enumerate(self.menu_options, 1):
            menu_lines.append(f"  {Colors.BLUE}{Colors.BOLD}{idx:2d}.{Colors.RESET} {emoji} {Colors.WHITE}{name}{Colors.RESET}")
            menu_lines.append(f"      {Colors.DIM}{Colors.GRAY}{desc}{Colors.RESET}")
            if idx < len(self.menu_options):
                menu_lines.append("")
        
        self.draw_box(menu_lines, color=Colors.DIM + Colors.GRAY)
        
        # Add tip section
        print()
        print(f"{Colors.DIM}{Colors.GRAY}※ Tip: Most operations support --dry-run flag for safe testing without making actual changes{Colors.RESET}")
    
    def get_choice(self) -> Optional[int]:
        """Get user's menu choice."""
        try:
            print()
            prompt = f"{Colors.CYAN}➤ Enter your choice (1-{len(self.menu_options)}): {Colors.RESET}"
            choice = input(prompt)
            choice_num = int(choice)
            if 1 <= choice_num <= len(self.menu_options):
                return choice_num
            else:
                print(f"\n{Colors.RED}❌ Invalid choice. Please enter a number between 1 and {len(self.menu_options)}.{Colors.RESET}")
                return None
        except ValueError:
            print(f"\n{Colors.RED}❌ Invalid input. Please enter a number.{Colors.RESET}")
            return None
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}👋 Goodbye!{Colors.RESET}")
            sys.exit(0)
    
    def run_script(self, script_path: str, args: List[str]):
        """Run a Python script with arguments."""
        cmd = [sys.executable, script_path] + args
        
        if self.dry_run and '--dry-run' not in args:
            cmd.append('--dry-run')
        
        print()
        execution_lines = [
            f"{Colors.CYAN}🔧 Executing Command{Colors.RESET}",
            "",
            f"{Colors.GRAY}{' '.join(cmd)}{Colors.RESET}"
        ]
        self.draw_box(execution_lines, color=Colors.CYAN)
        print()
        
        try:
            result = subprocess.run(cmd, check=False)
            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✅ Command completed successfully!{Colors.RESET}")
            else:
                print(f"\n{Colors.RED}❌ Command failed with exit code: {result.returncode}{Colors.RESET}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⏹️  Command cancelled by user{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.RED}❌ Error running command: {e}{Colors.RESET}")
        
        input(f"\n{Colors.DIM}{Colors.GRAY}Press Enter to continue...{Colors.RESET}")
    
    def get_input(self, prompt: str, required: bool = True) -> Optional[str]:
        """Get input from user with optional requirement."""
        try:
            formatted_prompt = f"{Colors.CYAN}➤ {prompt}{Colors.RESET}"
            value = input(formatted_prompt).strip()
            if required and not value:
                print(f"{Colors.RED}❌ This field is required.{Colors.RESET}")
                return None
            return value if value else None
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⏹️  Cancelled{Colors.RESET}")
            return None
    
    def rename_branches(self):
        """Handle branch renaming."""
        print()
        header_lines = [
            f"{Colors.BOLD}{Colors.WHITE}🔄 Rename Branches{Colors.RESET}",
            "",
            f"{Colors.GRAY}Rename branches across multiple projects in groups{Colors.RESET}"
        ]
        self.draw_box(header_lines)
        print()
        
        groups = self.get_input("Enter group names (comma-separated, or press Enter for all): ", required=False)
        old_branch = self.get_input("Enter old branch name (default: trunk): ", required=False) or "trunk"
        new_branch = self.get_input("Enter new branch name (default: main): ", required=False) or "main"
        
        args = []
        if groups:
            args.extend(['--groups'] + groups.split(','))
        args.extend(['--old-branch', old_branch, '--new-branch', new_branch])
        
        self.run_script('scripts/rename_branches.py', args)
    
    def generate_dashboard(self):
        """Generate executive dashboard."""
        print()
        header_lines = [
            f"{Colors.BOLD}{Colors.WHITE}📊 Generate Executive Dashboard{Colors.RESET}",
            "",
            f"{Colors.GRAY}Create HTML dashboards with analytics and metrics{Colors.RESET}"
        ]
        self.draw_box(header_lines)
        print()
        
        # Group IDs reference box
        group_lines = [
            f"{Colors.WHITE}Available Group IDs:{Colors.RESET}",
            "",
            f"  {Colors.BLUE}1721{Colors.RESET} = AI-ML-Services",
            f"  {Colors.BLUE}1267{Colors.RESET} = Research Repos",
            f"  {Colors.BLUE}1269{Colors.RESET} = Internal Services"
        ]
        self.draw_box(group_lines, color=Colors.DIM + Colors.GRAY)
        print()
        
        groups = self.get_input("Enter group IDs (comma-separated): ")
        if not groups:
            return
        
        output = self.get_input("Enter output filename (default: dashboard.html): ", required=False) or "dashboard.html"
        days = self.get_input("Enter number of days to analyze (default: 30): ", required=False) or "30"
        team_name = self.get_input("Enter team name (optional): ", required=False)
        
        args = ['--groups', groups, '--output', output, '--days', days]
        if team_name:
            args.extend(['--team-name', team_name])
        
        self.run_script('scripts/generate_executive_dashboard.py', args)
    
    def weekly_report(self):
        """Generate weekly report."""
        print()
        header_lines = [
            f"{Colors.BOLD}{Colors.WHITE}📅 Generate Weekly Report{Colors.RESET}",
            "",
            f"{Colors.GRAY}Create team productivity reports for weekly syncs{Colors.RESET}"
        ]
        self.draw_box(header_lines)
        print()
        
        # Group IDs reference box
        group_lines = [
            f"{Colors.WHITE}Available Group IDs:{Colors.RESET}",
            "",
            f"  {Colors.BLUE}1721{Colors.RESET} = AI-ML-Services",
            f"  {Colors.BLUE}1267{Colors.RESET} = Research Repos",
            f"  {Colors.BLUE}1269{Colors.RESET} = Internal Services"
        ]
        self.draw_box(group_lines, color=Colors.DIM + Colors.GRAY)
        print()
        
        groups = self.get_input("Enter group IDs (comma-separated): ")
        if not groups:
            return
        
        output = self.get_input("Enter output filename (optional): ", required=False)
        email = self.get_input("Enter email recipients (comma-separated, default: totrakool.k@thaibev.com): ", required=False) or "totrakool.k@thaibev.com"
        weeks = self.get_input("Enter number of weeks (default: 1): ", required=False) or "1"
        team = self.get_input("Enter team members (comma-separated, optional): ", required=False)
        
        args = ['--groups', groups, '--weeks', weeks]
        if output:
            args.extend(['--output', output])
        if email:
            args.extend(['--email', email])
        if team:
            args.extend(['--team', team])
        
        self.run_script('scripts/weekly_reports.py', args)
    
    def send_email(self):
        """Send report via email."""
        print("\n📧 Send Report Email")
        print("-" * 40)
        
        report_file = self.get_input("Enter report file path: ")
        if not report_file:
            return
        
        recipients = self.get_input("Enter email recipients (comma-separated): ")
        if not recipients:
            return
        
        subject = self.get_input("Enter email subject: ")
        if not subject:
            return
        
        args = [report_file, recipients, subject]
        self.run_script('scripts/send_report_email.py', args)
    
    def sync_issues(self):
        """Sync issues from markdown files."""
        print("\n📝 Sync Issues from Markdown")
        print("-" * 40)
        
        project_id = self.get_input("Enter project ID: ")
        if not project_id:
            return
        
        use_api = input("Use API instead of curl? (y/N): ").lower() == 'y'
        
        args = [project_id]
        if use_api:
            args.append('--use-api')
        
        self.run_script('scripts/sync_issues.py', args)
    
    def create_issues(self):
        """Create GitLab issues."""
        print("\n🎯 Create Issues")
        print("-" * 40)
        
        project = self.get_input("Enter project name or ID: ")
        if not project:
            return
        
        print("\nOptions:")
        print("1. Interactive mode (default)")
        print("2. Create from template")
        print("3. Import from CSV")
        
        mode = self.get_input("\nSelect mode (1-3, default: 1): ", required=False) or "1"
        
        args = [project]
        
        if mode == "2":
            template = self.get_input("Enter template name (e.g., feature, bug, epic): ")
            if template:
                args.extend(['--template', template])
        elif mode == "3":
            csv_file = self.get_input("Enter CSV file path: ")
            if csv_file:
                args.extend(['--import', csv_file])
        
        self.run_script('scripts/create_issues.py', args)
    
    def list_project_issues(self):
        """List project issues with assignee statistics."""
        print("\n📋 List Project Issues")
        print("-" * 40)
        
        print("\nScope:")
        print("1. Single project")
        print("2. Entire group")
        
        scope = self.get_input("\nSelect scope (1-2, default: 2): ", required=False) or "2"
        
        if scope == "1":
            project_id = self.get_input("Enter project ID or path: ")
            if not project_id:
                return
            args = [project_id]
        else:
            group_id = self.get_input("Enter group ID (default: 1266): ", required=False) or "1266"
            args = [group_id, '--group']
        
        output_file = self.get_input("Enter output filename (default: issue_assignments.md): ", required=False)
        if output_file:
            args.extend(['--output', output_file])
        
        include_unassigned = self.get_input("Include unassigned issues? (y/N): ", required=False)
        if include_unassigned and include_unassigned.lower() == 'y':
            args.append('--include-unassigned')
        
        use_board_labels = self.get_input("Use board labels for state tracking? (Y/n): ", required=False)
        if use_board_labels and use_board_labels.lower() == 'n':
            args.append('--no-board-labels')
        
        self.run_script('scripts/list_project_issues.py', args)
    
    def analyze_projects(self):
        """Analyze projects."""
        print("\n📈 Analyze Projects")
        print("-" * 40)
        
        print("\nAnalysis types:")
        print("1. Single project")
        print("2. Entire group")
        print("3. Compare multiple projects")
        
        analysis_type = self.get_input("\nSelect type (1-3): ")
        if not analysis_type or analysis_type not in ['1', '2', '3']:
            return
        
        if analysis_type == "1":
            project_id = self.get_input("Enter project ID: ")
            if not project_id:
                return
            args = ['project', project_id]
        elif analysis_type == "2":
            group_id = self.get_input("Enter group ID: ")
            if not group_id:
                return
            args = ['group', group_id]
        else:
            project_ids = self.get_input("Enter project IDs (comma-separated): ")
            if not project_ids:
                return
            args = ['compare', project_ids]
        
        output = self.get_input("Enter output filename (optional): ", required=False)
        if output:
            args.extend(['--output', output])
        
        self.run_script('scripts/analyze_projects.py', args)
    
    def export_analytics(self):
        """Export analytics to Excel."""
        print("\n📊 Export Analytics")
        print("-" * 40)
        
        projects = self.get_input("Enter project IDs (comma-separated): ")
        if not projects:
            return
        
        output = self.get_input("Enter output filename (default: analytics.xlsx): ", required=False) or "analytics.xlsx"
        
        args = ['projects', projects, '--output', output]
        self.run_script('scripts/export_analytics.py', args)
    
    def code_changes_report(self):
        """Generate code changes report."""
        print("\n📝 Generate Code Changes Report")
        print("-" * 40)
        
        groups = self.get_input("Enter group IDs (comma-separated): ")
        if not groups:
            return
        
        output = self.get_input("Enter output filename (default: code_changes.html): ", required=False) or "code_changes.html"
        days = self.get_input("Enter number of days (default: 30): ", required=False) or "30"
        
        args = ['--groups', groups, '--output', output, '--days', days]
        self.run_script('scripts/generate_code_changes_report.py', args)
    
    
    def exit_program(self):
        """Exit the program."""
        print()
        goodbye_lines = [
            f"{Colors.BOLD}{Colors.WHITE}👋 Thanks for using GitLab Tools!{Colors.RESET}",
            "",
            f"{Colors.GRAY}Have a great day!{Colors.RESET}"
        ]
        self.draw_box(goodbye_lines, color=Colors.YELLOW)
        sys.exit(0)
    
    def run(self):
        """Run the menu interface."""
        while True:
            self.clear_screen()
            self.show_header()
            self.show_menu()
            
            choice = self.get_choice()
            if choice is not None:
                _, _, _, handler = self.menu_options[choice - 1]
                handler()


def main():
    """Main entry point."""
    try:
        menu = GitLabMenu()
        menu.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())