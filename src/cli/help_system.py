"""
Help System for GitLab Tools CLI.

Provides contextual help and command documentation.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Optional, Dict
from .command_parser import CommandParser
from .command_registry import CommandPattern, DirectScriptPattern


class ScriptHelpExtractor:
    """Extracts help information from existing scripts."""
    
    def __init__(self):
        """Initialize the script help extractor."""
        self.project_root = Path(__file__).parent.parent.parent
        self._help_cache: Dict[str, str] = {}
    
    def get_script_help(self, script_path: str) -> Optional[str]:
        """
        Get help output from a script.
        
        Args:
            script_path: Path to the script relative to project root
            
        Returns:
            Help text from the script or None if not available
        """
        if script_path in self._help_cache:
            return self._help_cache[script_path]
        
        full_path = self.project_root / script_path
        if not full_path.exists():
            return None
        
        try:
            # Try to get help from the script
            result = subprocess.run(
                ['python', str(full_path), '--help'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root
            )
            
            if result.returncode == 0 and result.stdout.strip():
                help_text = result.stdout.strip()
                self._help_cache[script_path] = help_text
                return help_text
            
            # If --help doesn't work, try -h
            result = subprocess.run(
                ['python', str(full_path), '-h'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root
            )
            
            if result.returncode == 0 and result.stdout.strip():
                help_text = result.stdout.strip()
                self._help_cache[script_path] = help_text
                return help_text
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return None
    
    def extract_usage_from_help(self, help_text: str) -> Optional[str]:
        """Extract usage line from help text."""
        if not help_text:
            return None
        
        lines = help_text.split('\n')
        for line in lines:
            if line.strip().lower().startswith('usage:'):
                return line.strip()
        
        return None
    
    def extract_parameters_from_help(self, help_text: str) -> Dict[str, str]:
        """
        Extract parameter descriptions from help text.
        
        Args:
            help_text: Raw help text from script
            
        Returns:
            Dictionary mapping parameter names to descriptions
        """
        if not help_text:
            return {}
        
        parameters = {}
        lines = help_text.split('\n')
        in_options_section = False
        
        for line in lines:
            line = line.strip()
            
            # Detect options section
            if re.match(r'^(options|arguments|parameters):', line, re.IGNORECASE):
                in_options_section = True
                continue
            
            # Stop at next section
            if in_options_section and line and not line.startswith(' ') and not line.startswith('-'):
                if ':' in line and not line.startswith('-'):
                    break
            
            # Extract parameter info
            if in_options_section and line.startswith('-'):
                # Match patterns like "-h, --help", "--project PROJECT", etc.
                match = re.match(r'^(-\w,?\s*)?--(\w[\w-]*)\s*(\w+)?\s*(.*)', line)
                if match:
                    param_name = match.group(2)
                    description = match.group(4).strip()
                    parameters[param_name] = description
        
        return parameters


class HelpSystem:
    """Provides help and documentation for CLI commands."""
    
    def __init__(self, command_parser: CommandParser):
        """Initialize the help system."""
        self.command_parser = command_parser
        self.script_help_extractor = ScriptHelpExtractor()
    
    def show_general_help(self):
        """Show general help information."""
        help_text = """
📚 GitLab Tools CLI Help

Natural Language Commands:
"""
        print(help_text)
        
        # Get all unique commands
        commands = self.command_parser.get_all_commands()
        seen_scripts = set()
        
        for command in commands:
            if command.script_path not in seen_scripts:
                seen_scripts.add(command.script_path)
                print(f"  🔹 {command.description}")
                
                # Show first example
                if command.examples:
                    print(f"     Example: {command.examples[0]}")
                print()
        
        # Add direct script commands section
        print("Direct Script Commands:")
        direct_scripts = self.command_parser.registry.get_direct_script_commands()
        
        for script in direct_scripts:
            print(f"  🔧 {script.script_name} - {script.description}")
            if script.examples:
                print(f"     Example: {script.examples[0]}")
            print()
        
        # Add Executive Dashboard section
        print("""
📊 Executive Dashboard Commands:
  Available Group IDs:
    1721 = AI-ML-Services       (AI/ML projects and services)
    1267 = Research Repos       (Research and experimental projects)  
    1269 = Internal Services    (Core platform and infrastructure)
    119  = iland               (iland-specific projects)

  Common Dashboard Commands:
    🔧 generate_executive_dashboard --groups 1721,1267,1269,119
    🔧 generate_executive_dashboard --groups 1721 --days 30 --output ai_dashboard.html
    🔧 generate_executive_dashboard --groups 1721,1267 --team-name "Development Team"
    💬 generate executive dashboard for all groups
    💬 create dashboard for AI team

  Direct Python Usage:
    python scripts/generate_executive_dashboard.py --groups 1721,1267,1269,119
    python scripts/generate_executive_dashboard.py --groups 1721,1267 --days 60
""")
        
        print("""
Special Commands:
  🔹 help [command]     - Show help for a specific command
  🔹 history           - Show command execution history
  🔹 dry-run          - Toggle dry-run mode
  🔹 status           - Show current status
  🔹 clear            - Clear screen
  🔹 exit             - Exit the CLI

Command Types:
  💬 Natural Language: "create issues for project 123"
  🔧 Direct Scripts: "rename_branches --groups AI-ML-Services --dry-run"

Tips:
  💡 Use Tab for auto-completion
  💡 Use ↑/↓ arrows for command history
  💡 Use Ctrl+C to cancel running commands
  💡 Type 'help <command>' for detailed help on specific commands
  💡 Add '--help' to any direct script command for usage info

Examples:
  > create issues for project 123
  > generate_executive_dashboard --groups 1721,1267,1269
  > weekly report for group 5 email to team@company.com
  > rename_branches --groups "AI-ML-Services" --old-branch trunk --new-branch main
  > help create
  > sync_issues --help
""")
    
    def show_command_help(self, command_name: str):
        """
        Show help for a specific command.
        
        Args:
            command_name: Name of the command to show help for
        """
        # Check for special dashboard help
        if command_name.lower() in ['dashboard', 'executive_dashboard', 'generate_executive_dashboard']:
            self.show_executive_dashboard_help()
            return
        
        # Find the command
        command_info = self.command_parser.get_command_help(command_name)
        
        if not command_info:
            print(f"❌ No help found for '{command_name}'")
            
            # Show suggestions
            suggestions = self.command_parser.get_suggestions(command_name)
            if suggestions:
                print("\n💡 Did you mean:")
                for suggestion in suggestions[:5]:
                    print(f"  • {suggestion}")
            
            print("\nType 'help' to see all available commands.")
            return
        
        # Show detailed help
        self._show_detailed_command_help(command_info)
    
    def _show_detailed_command_help(self, command: CommandPattern):
        """Show detailed help for a specific command."""
        print(f"\n📖 Help for: {command.description}")
        print("=" * 60)
        
        # Script information
        print(f"Script: {command.script_path}")
        
        # Aliases
        if command.aliases:
            print(f"Aliases: {', '.join(command.aliases)}")
        
        # Parameters
        if command.required_params or command.optional_params:
            print("\nParameters:")
            
            if command.required_params:
                print("  Required:")
                for param in command.required_params:
                    print(f"    • {param}")
            
            if command.optional_params:
                print("  Optional:")
                for param in command.optional_params:
                    print(f"    • {param}")
        
        # Examples
        if command.examples:
            print("\nExamples:")
            for i, example in enumerate(command.examples, 1):
                print(f"  {i}. {example}")
        
        # Usage tips
        self._show_usage_tips(command)
        
        print()
    
    def generate_direct_command_help(self, script_pattern: DirectScriptPattern) -> str:
        """
        Generate standardized help for a direct script command.
        
        Args:
            script_pattern: The direct script pattern
            
        Returns:
            Formatted help text
        """
        help_lines = []
        
        # Header
        help_lines.append(f"📖 {script_pattern.script_name}")
        help_lines.append("=" * 60)
        help_lines.append(f"Description: {script_pattern.description}")
        help_lines.append("")
        
        # Usage
        usage_parts = [script_pattern.script_name]
        
        # Add required parameters
        for param in script_pattern.required_params:
            usage_parts.append(f"--{param} <value>")
        
        # Add positional parameters
        for param in script_pattern.positional_params:
            usage_parts.append(f"<{param}>")
        
        # Add optional indicators
        optional_parts = []
        for param in script_pattern.optional_params:
            optional_parts.append(f"[--{param} <value>]")
        
        for param in script_pattern.boolean_flags:
            optional_parts.append(f"[--{param}]")
        
        help_lines.append(f"Usage: {' '.join(usage_parts)} {' '.join(optional_parts)}")
        help_lines.append("")
        
        # Parameters
        if script_pattern.required_params:
            help_lines.append("Required Parameters:")
            for param in script_pattern.required_params:
                help_lines.append(f"  --{param}     {self._get_parameter_description(param, script_pattern.script_name)}")
            help_lines.append("")
        
        if script_pattern.positional_params:
            help_lines.append("Positional Arguments:")
            for param in script_pattern.positional_params:
                help_lines.append(f"  {param}       {self._get_parameter_description(param, script_pattern.script_name)}")
            help_lines.append("")
        
        if script_pattern.optional_params:
            help_lines.append("Optional Parameters:")
            for param in script_pattern.optional_params:
                help_lines.append(f"  --{param}     {self._get_parameter_description(param, script_pattern.script_name)}")
            help_lines.append("")
        
        if script_pattern.boolean_flags:
            help_lines.append("Flags:")
            for param in script_pattern.boolean_flags:
                help_lines.append(f"  --{param}     {self._get_parameter_description(param, script_pattern.script_name)}")
            help_lines.append("")
        
        # Examples
        if script_pattern.examples:
            help_lines.append("Examples:")
            for i, example in enumerate(script_pattern.examples, 1):
                help_lines.append(f"  {i}. {example}")
            help_lines.append("")
        
        # Try to get additional help from the script itself
        script_help = self.script_help_extractor.get_script_help(script_pattern.script_path)
        if script_help:
            help_lines.append("Additional Information:")
            help_lines.append(script_help)
        
        return "\n".join(help_lines)
    
    def _get_parameter_description(self, param_name: str, script_name: str) -> str:
        """Get a description for a parameter."""
        descriptions = {
            'groups': 'Group names or IDs (comma or space separated)',
            'project': 'Project name or ID',
            'project_id': 'Project ID number',
            'old-branch': 'Name of the branch to rename from',
            'new-branch': 'Name of the branch to rename to',
            'output': 'Output file path',
            'days': 'Number of days for analysis period',
            'team-name': 'Team name for the report',
            'issues-dir': 'Directory containing issue files',
            'use-api': 'Use GitLab API instead of git commands',
            'dry-run': 'Preview changes without executing',
            'generate-script': 'Generate a script file instead of executing',
            'config': 'Configuration file path',
            'report': 'Report output file path',
            'log-level': 'Logging level (DEBUG, INFO, WARNING, ERROR)',
            'no-color': 'Disable colored output',
            'format': 'Output format (json, html, etc.)',
            'trends': 'Include trend analysis',
            'clear-cache': 'Clear cached data'
        }
        
        return descriptions.get(param_name, 'Parameter value')
    
    def show_script_usage(self, script_name: str):
        """Show usage information for a direct script command."""
        # Get script pattern from registry
        direct_scripts = self.command_parser.registry.get_direct_script_commands()
        script_pattern = None
        
        for script in direct_scripts:
            if script.script_name == script_name:
                script_pattern = script
                break
        
        if not script_pattern:
            print(f"❌ Script '{script_name}' not found")
            return
        
        help_text = self.generate_direct_command_help(script_pattern)
        print(help_text)
    
    def _show_usage_tips(self, command: CommandPattern):
        """Show usage tips for a command."""
        script_name = command.script_path.split('/')[-1]
        
        tips = {
            'create_issues.py': [
                "💡 Issues are created from markdown files in the 'issues' folder by default",
                "💡 Use project ID for specific project, or omit to use default from config",
                "💡 Each .md file becomes a separate issue with title from filename"
            ],
            'rename_branches.py': [
                "💡 Specify group name to rename branches across all projects in group",
                "💡 Use 'from X to Y' to specify exact branch names",
                "💡 Common usage: 'rename branches from master to main'"
            ],
            'generate_executive_dashboard.py': [
                "💡 Generates HTML dashboard with project metrics and analytics",
                "💡 Use group IDs to focus on specific teams or departments",
                "💡 Dashboard includes commit activity, merge requests, and issue stats"
            ],
            'weekly_reports.py': [
                "💡 Generates productivity reports for specified time period",
                "💡 Add 'email to <address>' to automatically send the report",
                "💡 Group IDs help focus the report on specific teams"
            ],
            'analyze_projects.py': [
                "💡 Provides detailed analysis of project health and activity",
                "💡 Use multiple project IDs separated by commas",
                "💡 Analysis includes code quality metrics and team productivity"
            ],
            'export_analytics.py': [
                "💡 Exports raw analytics data for external processing",
                "💡 Data includes commits, issues, merge requests, and user activity",
                "💡 Export format is JSON by default"
            ],
            'sync_issues.py': [
                "💡 Synchronizes local issue files with GitLab issues",
                "💡 Updates existing issues and creates new ones as needed",
                "💡 Maintains bidirectional sync between local files and GitLab"
            ],
            'send_report_email.py': [
                "💡 Sends generated reports via email",
                "💡 Supports multiple recipients separated by commas",
                "💡 Automatically detects report format based on file extension"
            ]
        }
        
        if script_name in tips:
            print("\nUsage Tips:")
            for tip in tips[script_name]:
                print(f"  {tip}")
    
    def show_interactive_tutorial(self):
        """Show an interactive tutorial for new users."""
        print("""
🎓 GitLab Tools CLI Tutorial

Welcome to the GitLab Tools CLI! This tutorial will show you the basics.

Step 1: Basic Commands
Try typing: help
This shows all available commands.

Step 2: Create Issues
Try typing: create issues for project 123
This creates GitLab issues from markdown files.

Step 3: Generate Reports  
Try typing: weekly report for groups 1,2,3
This generates a productivity report.

Step 4: Get Command Help
Try typing: help create
This shows detailed help for the create command.

Step 5: Use Tab Completion
Start typing 'creat' and press Tab - it will auto-complete!

Step 6: Command History
Use ↑ and ↓ arrows to navigate through previous commands.

Step 7: Dry Run Mode
Type: dry-run
This toggles dry-run mode to test commands without executing them.

🎉 You're ready to use the GitLab Tools CLI!
Type 'exit' when you're done.
""")
    
    def show_command_reference(self):
        """Show a comprehensive command reference."""
        print("\n📚 Command Reference")
        print("=" * 60)
        
        commands = self.command_parser.get_all_commands()
        seen_scripts = set()
        
        for command in commands:
            if command.script_path not in seen_scripts:
                seen_scripts.add(command.script_path)
                print(f"\n{command.description}")
                print("-" * len(command.description))
                
                # Pattern
                print(f"Pattern: {command.pattern}")
                
                # Examples
                if command.examples:
                    print("Examples:")
                    for example in command.examples:
                        print(f"  • {example}")
                
                # Aliases
                if command.aliases:
                    print(f"Aliases: {', '.join(command.aliases)}")
    
    def get_command_documentation(self, command_name: str) -> Optional[str]:
        """
        Get formatted documentation for a command.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Formatted documentation string or None
        """
        command_info = self.command_parser.get_command_help(command_name)
        
        if not command_info:
            return None
        
        lines = []
        lines.append(f"Command: {command_info.description}")
        lines.append(f"Script: {command_info.script_path}")
        
        if command_info.aliases:
            lines.append(f"Aliases: {', '.join(command_info.aliases)}")
        
        if command_info.examples:
            lines.append("Examples:")
            for example in command_info.examples:
                lines.append(f"  {example}")
        
        return '\n'.join(lines)
    
    def show_executive_dashboard_help(self):
        """Show detailed help for executive dashboard generation."""
        print("""
📊 Executive Dashboard - Detailed Help
=====================================

The Executive Dashboard generates comprehensive analytics reports for GitLab groups,
providing insights into project health, team performance, and development metrics.

🎯 Purpose:
  • Track project activity and health across multiple groups
  • Monitor team productivity and workload distribution  
  • Identify issues requiring attention with AI-powered recommendations
  • Generate executive-level reports for stakeholders

📋 Available Group IDs:
  1721 = AI-ML-Services       (AI/ML projects and RAG pipelines)
  1267 = Research Repos       (Experimental and research projects)
  1269 = Internal Services    (Core platform and infrastructure)
  119  = iland               (iland-specific llama-index projects)

🔧 Command Syntax:
  generate_executive_dashboard --groups <group_ids> [options]

📝 Required Parameters:
  --groups <ids>              Comma-separated group IDs (e.g., 1721,1267,1269,119)

⚙️ Optional Parameters:
  --output <file>             Output HTML file (default: executive_dashboard.html)
  --days <number>             Analysis period in days (default: 30)
  --team-name <name>          Team name for the report (default: "Development Team")

🚀 Common Usage Examples:

  1. All Groups Dashboard:
     > generate_executive_dashboard --groups 1721,1267,1269,119

  2. AI Team Dashboard (30 days):
     > generate_executive_dashboard --groups 1721 --team-name "AI Team"

  3. Extended Analysis (60 days):
     > generate_executive_dashboard --groups 1721,1267 --days 60

  4. Custom Output File:
     > generate_executive_dashboard --groups 1721,1267,1269,119 --output weekly_report.html

  5. Research Team Focus:
     > generate_executive_dashboard --groups 1267 --team-name "Research Team" --days 90

💬 Natural Language Alternatives:
  > generate executive dashboard for all groups
  > create dashboard for AI team
  > weekly dashboard for groups 1721,1267

🐍 Direct Python Usage:
  python scripts/generate_executive_dashboard.py --groups 1721,1267,1269,119
  python scripts/generate_executive_dashboard.py --groups 1721 --days 60 --output ai_report.html

📊 Generated Report Includes:
  • Key Performance Indicators (commits, MRs, issues)
  • Project health scores and grades
  • Team performance analytics
  • Issue management insights
  • AI-powered recommendations
  • Technology stack analysis
  • 30-day activity trends

⚠️ Prerequisites:
  • GITLAB_URL environment variable set
  • GITLAB_TOKEN environment variable set
  • Valid GitLab API access to specified groups

💡 Pro Tips:
  • Use --days 7 for weekly reports
  • Use --days 90 for quarterly reviews
  • Combine multiple groups for organization-wide insights
  • Save different outputs for different stakeholder groups
""") 