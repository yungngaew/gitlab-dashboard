"""
Command Registry for GitLab Tools CLI.

Defines command patterns, aliases, and mappings to script files.
"""

import re
from typing import Dict, List, Optional, Pattern, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass 
class DirectScriptPattern:
    """Represents a direct script command with its metadata."""
    
    script_name: str
    script_path: str
    description: str
    required_params: List[str] = None
    optional_params: List[str] = None
    positional_params: List[str] = None
    boolean_flags: List[str] = None
    examples: List[str] = None
    
    def __post_init__(self):
        if self.required_params is None:
            self.required_params = []
        if self.optional_params is None:
            self.optional_params = []
        if self.positional_params is None:
            self.positional_params = []
        if self.boolean_flags is None:
            self.boolean_flags = []
        if self.examples is None:
            self.examples = []


@dataclass
class CommandPattern:
    """Represents a command pattern with its metadata."""
    
    pattern: str
    script_path: str
    description: str
    examples: List[str]
    aliases: List[str] = None
    required_params: List[str] = None
    optional_params: List[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.required_params is None:
            self.required_params = []
        if self.optional_params is None:
            self.optional_params = []


class CommandRegistry:
    """Registry of all available CLI commands with pattern matching."""
    
    def __init__(self):
        self.commands: Dict[str, CommandPattern] = {}
        self.compiled_patterns: Dict[str, Pattern] = {}
        self.direct_scripts: Dict[str, DirectScriptPattern] = {}
        self._initialize_commands()
        self._discover_scripts()
    
    def _initialize_commands(self):
        """Initialize all command patterns."""
        
        # Rename branches command
        self.register_command(CommandPattern(
            pattern=r'rename\s+branches?(?:\s+in\s+(?P<group>\S+))?(?:\s+from\s+(?P<old_branch>\S+)\s+to\s+(?P<new_branch>\S+))?',
            script_path='scripts/rename_branches.py',
            description='Rename branches in GitLab groups or projects',
            examples=[
                'rename branches in AI-ML-Services from trunk to main',
                'rename branches from master to main',
                'rename branches in project-group'
            ],
            aliases=['rename branch', 'change branch name', 'update branch'],
            optional_params=['group', 'old_branch', 'new_branch']
        ))
        
        # Create issues command
        self.register_command(CommandPattern(
            pattern=r'create\s+issues?(?:\s+(?:for\s+project\s+(?P<project_id>\d+)|from\s+(?P<folder>\S+)))?',
            script_path='scripts/create_issues.py',
            description='Create GitLab issues from markdown files',
            examples=[
                'create issues for project 123',
                'create issues from issues_folder',
                'create issues'
            ],
            aliases=['add issues', 'make issues', 'new issues'],
            optional_params=['project_id', 'folder']
        ))
        
        # Generate dashboard command
        self.register_command(CommandPattern(
            pattern=r'generate\s+(?:dashboard|executive\s+dashboard)(?:\s+for\s+groups?\s+(?P<group_ids>[\d,\s]+))?',
            script_path='scripts/generate_executive_dashboard.py',
            description='Generate executive dashboard for groups',
            examples=[
                'generate dashboard for groups 1,2,3',
                'generate executive dashboard',
                'generate dashboard for group 5'
            ],
            aliases=['create dashboard', 'make dashboard', 'exec dashboard'],
            optional_params=['group_ids']
        ))
        
        # Weekly reports command
        self.register_command(CommandPattern(
            pattern=r'(?:weekly|productivity)\s+reports?(?:\s+for\s+groups?\s+(?P<group_ids>[\d,\s]+))?(?:\s+(?:email|send)\s+to\s+(?P<email>[\w@.,\s]+))?',
            script_path='scripts/weekly_reports.py',
            description='Generate weekly productivity reports',
            examples=[
                'weekly report for groups 1,2,3',
                'productivity report email to team@company.com',
                'weekly report for group 5 send to manager@company.com'
            ],
            aliases=['team report', 'productivity report', 'weekly summary'],
            optional_params=['group_ids', 'email']
        ))
        
        # Analyze project command
        self.register_command(CommandPattern(
            pattern=r'analyze\s+projects?(?:\s+(?P<project_ids>[\d,\s]+))?',
            script_path='scripts/analyze_projects.py',
            description='Analyze GitLab projects and generate insights',
            examples=[
                'analyze project 123',
                'analyze projects 123,456,789',
                'analyze project'
            ],
            aliases=['analysis', 'project analysis', 'show analytics'],
            optional_params=['project_ids']
        ))
        
        # Export analytics command
        self.register_command(CommandPattern(
            pattern=r'export\s+analytics(?:\s+for\s+projects?\s+(?P<project_ids>[\d,\s]+))?',
            script_path='scripts/export_analytics.py',
            description='Export analytics data for projects',
            examples=[
                'export analytics for projects 123,456',
                'export analytics for project 789',
                'export analytics'
            ],
            aliases=['export data', 'analytics export', 'download analytics'],
            optional_params=['project_ids']
        ))
        
        # Sync issues command
        self.register_command(CommandPattern(
            pattern=r'sync\s+issues(?:\s+(?:for\s+project\s+(?P<project_id>\d+)|from\s+(?P<folder>\S+)))?',
            script_path='scripts/sync_issues.py',
            description='Sync issues between local files and GitLab',
            examples=[
                'sync issues for project 123',
                'sync issues from issues_folder',
                'sync issues'
            ],
            aliases=['synchronize issues', 'update issues'],
            optional_params=['project_id', 'folder']
        ))
        
        # Send report email command
        self.register_command(CommandPattern(
            pattern=r'send\s+(?:report\s+)?(?P<file>\S+)\s+to\s+(?P<email>[\w@.,\s]+)',
            script_path='scripts/send_report_email.py',
            description='Send report files via email',
            examples=[
                'send report.pdf to team@company.com',
                'send weekly_report.html to manager@company.com'
            ],
            aliases=['email report', 'mail report'],
            required_params=['file', 'email']
        ))
    
    def register_command(self, command: CommandPattern):
        """Register a new command pattern."""
        # Use the first word as the command key
        key = command.pattern.split('\\s+')[0].replace('(?:', '').replace(')', '')
        self.commands[key] = command
        
        # Compile the regex pattern for efficient matching
        self.compiled_patterns[key] = re.compile(command.pattern, re.IGNORECASE)
        
        # Also register aliases
        for alias in command.aliases:
            alias_key = alias.split()[0].lower()
            if alias_key not in self.commands:
                self.commands[alias_key] = command
    
    def find_command(self, user_input: str) -> Optional[Tuple[CommandPattern, Dict[str, str]]]:
        """
        Find a matching command pattern for user input.
        
        Args:
            user_input: The user's command string
            
        Returns:
            Tuple of (CommandPattern, extracted_params) or None if no match
        """
        user_input = user_input.strip()
        
        # Check direct script commands first (highest priority)
        if self.is_direct_script_command(user_input):
            first_word = user_input.split()[0]
            direct_script = self.find_direct_script(first_word)
            if direct_script:
                # Create a temporary CommandPattern for compatibility
                command_pattern = CommandPattern(
                    pattern=f"^{first_word}",
                    script_path=direct_script.script_path,
                    description=direct_script.description,
                    examples=direct_script.examples,
                    aliases=[],
                    required_params=direct_script.required_params,
                    optional_params=direct_script.optional_params
                )
                # For direct scripts, we'll parse parameters later in the parser
                return command_pattern, {'is_direct_script': 'true'}
        
        # Try exact pattern matching for natural language commands
        for key, pattern in self.compiled_patterns.items():
            match = pattern.match(user_input)
            if match:
                command = self.commands[key]
                params = match.groupdict()
                # Clean up parameter values
                cleaned_params = {}
                for param_key, param_value in params.items():
                    if param_value is not None:
                        cleaned_params[param_key] = param_value.strip()
                return command, cleaned_params
        
        # Try fuzzy matching based on keywords
        return self._fuzzy_match(user_input)
    
    def _fuzzy_match(self, user_input: str) -> Optional[Tuple[CommandPattern, Dict[str, str]]]:
        """
        Attempt fuzzy matching when exact pattern matching fails.
        
        Args:
            user_input: The user's command string
            
        Returns:
            Tuple of (CommandPattern, extracted_params) or None
        """
        words = user_input.lower().split()
        best_match = None
        best_score = 0
        
        for key, command in self.commands.items():
            score = 0
            
            # Check main command keywords
            if key in words:
                score += 10
            
            # Check aliases
            for alias in command.aliases:
                alias_words = alias.lower().split()
                if any(word in words for word in alias_words):
                    score += 5
            
            # Partial keyword matching
            for word in words:
                if word in key or key in word:
                    score += 2
            
            if score > best_score and score >= 5:  # Minimum threshold
                best_score = score
                best_match = command
        
        if best_match:
            # Try to extract basic parameters for fuzzy matches
            params = self._extract_basic_params(user_input)
            return best_match, params
        
        return None
    
    def _extract_basic_params(self, user_input: str) -> Dict[str, str]:
        """Extract basic parameters from user input for fuzzy matches."""
        params = {}
        
        # Extract project IDs
        project_match = re.search(r'project\s+(\d+)', user_input, re.IGNORECASE)
        if project_match:
            params['project_id'] = project_match.group(1)
        
        # Extract group IDs
        group_match = re.search(r'group\s+([\d,\s]+)', user_input, re.IGNORECASE)
        if group_match:
            params['group_ids'] = group_match.group(1)
        
        # Extract email addresses
        email_match = re.search(r'(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)', user_input)
        if email_match:
            params['email'] = email_match.group(1)
        
        # Extract file paths
        file_match = re.search(r'(\S+\.\w+)', user_input)
        if file_match:
            params['file'] = file_match.group(1)
        
        return params
    
    def get_all_commands(self) -> List[CommandPattern]:
        """Get all registered commands."""
        seen = set()
        unique_commands = []
        
        for command in self.commands.values():
            if id(command) not in seen:
                unique_commands.append(command)
                seen.add(id(command))
        
        return unique_commands
    
    def get_command_suggestions(self, partial_input: str) -> List[str]:
        """Get command suggestions based on partial input."""
        suggestions = []
        partial_lower = partial_input.lower()
        
        for key, command in self.commands.items():
            if key.startswith(partial_lower):
                suggestions.extend(command.examples[:2])  # Add first 2 examples
            
            # Check aliases
            for alias in command.aliases:
                if alias.lower().startswith(partial_lower):
                    suggestions.extend(command.examples[:1])  # Add first example
        
        return list(set(suggestions))[:10]  # Return unique suggestions, max 10
    
    def _discover_scripts(self):
        """Discover and register all scripts in the scripts/ directory."""
        scripts_dir = Path('scripts')
        if not scripts_dir.exists():
            return
            
        script_definitions = {
            'rename_branches.py': DirectScriptPattern(
                script_name='rename_branches',
                script_path='scripts/rename_branches.py',
                description='Rename branches in GitLab groups or projects',
                required_params=[],
                optional_params=['groups', 'old-branch', 'new-branch', 'dry-run', 'config', 'report', 'log-level', 'no-color'],
                boolean_flags=['dry-run', 'no-color'],
                examples=[
                    'rename_branches --groups "AI-ML-Services" --dry-run',
                    'rename_branches --groups "AI-ML-Services" --old-branch trunk --new-branch main'
                ]
            ),
            'generate_executive_dashboard.py': DirectScriptPattern(
                script_name='generate_executive_dashboard',
                script_path='scripts/generate_executive_dashboard.py',
                description='Generate executive dashboard for groups',
                required_params=['groups'],
                optional_params=['output', 'days', 'team-name'],
                examples=[
                    'generate_executive_dashboard --groups 1721,1267,1269',
                    'generate_executive_dashboard --groups 1721 --days 60 --output monthly-report.html'
                ]
            ),
            'sync_issues.py': DirectScriptPattern(
                script_name='sync_issues',
                script_path='scripts/sync_issues.py',
                description='Sync issues between local files and GitLab',
                required_params=[],
                positional_params=['project_id'],
                optional_params=['issues-dir', 'use-api', 'dry-run', 'generate-script', 'config'],
                boolean_flags=['use-api', 'dry-run', 'generate-script'],
                examples=[
                    'sync_issues my-project --dry-run',
                    'sync_issues 123 --issues-dir sprint-planning --use-api'
                ]
            ),
            'send_report_email.py': DirectScriptPattern(
                script_name='send_report_email',
                script_path='scripts/send_report_email.py',
                description='Send report files via email',
                required_params=[],
                positional_params=['html_file', 'recipient', 'subject'],
                examples=[
                    'send_report_email dashboard.html manager@company.com "Weekly Report"',
                    'send_report_email report.html "team@company.com" "Monthly Analytics"'
                ]
            ),
            'analyze_projects.py': DirectScriptPattern(
                script_name='analyze_projects',
                script_path='scripts/analyze_projects.py',
                description='Analyze GitLab projects and generate insights',
                required_params=[],
                optional_params=['project', 'group', 'format', 'output', 'trends', 'days', 'clear-cache'],
                boolean_flags=['trends', 'clear-cache'],
                examples=[
                    'analyze_projects --project my-project',
                    'analyze_projects --group "AI-ML-Services" --format json'
                ]
            ),
            'export_analytics.py': DirectScriptPattern(
                script_name='export_analytics',
                script_path='scripts/export_analytics.py',
                description='Export analytics data for projects',
                required_params=[],
                positional_params=['project'],
                optional_params=['output', 'trends', 'days'],
                boolean_flags=['trends'],
                examples=[
                    'export_analytics my-project --output project_report.xlsx',
                    'export_analytics my-project --trends --days 60'
                ]
            )
        }
        
        # Register discovered scripts
        for script_file, script_pattern in script_definitions.items():
            if (scripts_dir / script_file).exists():
                self.register_direct_script(script_pattern)
    
    def register_direct_script(self, script_pattern: DirectScriptPattern):
        """Register a new direct script command."""
        self.direct_scripts[script_pattern.script_name] = script_pattern
    
    def find_direct_script(self, script_name: str) -> Optional[DirectScriptPattern]:
        """Find a direct script by exact name match."""
        return self.direct_scripts.get(script_name)
    
    def is_direct_script_command(self, user_input: str) -> bool:
        """Check if the user input starts with a direct script command name."""
        first_word = user_input.strip().split()[0] if user_input.strip() else ""
        return first_word in self.direct_scripts
    
    def get_direct_script_commands(self) -> List[DirectScriptPattern]:
        """Get all available direct script commands."""
        return list(self.direct_scripts.values()) 