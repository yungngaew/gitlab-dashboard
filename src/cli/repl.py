"""
Interactive REPL for GitLab Tools CLI.

Provides an interactive command-line interface with history, completion, and syntax highlighting.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import signal

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.shortcuts import confirm
    from prompt_toolkit.patch_stdout import patch_stdout
except ImportError:
    print("❌ prompt_toolkit not installed. Install with: pip install prompt_toolkit")
    sys.exit(1)

from .command_parser import CommandParser, ParsedCommand, DirectScriptCommand
from .command_executor import CommandExecutor, ExecutionResult, ExecutionStatus
from .logging_config import create_cli_logger, CLILogger
from .help_system import HelpSystem
from .. import __version__


class GitLabCompleter(Completer):
    """Custom completer for GitLab CLI commands."""
    
    def __init__(self, command_parser: CommandParser):
        self.command_parser = command_parser
    
    def get_completions(self, document, complete_event):
        """Get completions for the current document."""
        text = document.text_before_cursor
        words = text.split()
        
        if not words:
            # Show all available commands when no input
            self._yield_all_commands()
            return
        
        current_word = words[-1] if text.endswith(' ') else (words[-1] if words else '')
        
        # If we're at the start of a command, suggest command names
        if len(words) == 1 and not text.endswith(' '):
            self._yield_command_completions(current_word)
        
        # If we're in a direct script command, suggest parameters
        elif len(words) >= 1:
            first_word = words[0]
            if self.command_parser.registry.is_direct_script_command(first_word):
                self._yield_parameter_completions(first_word, current_word, words)
        
        # Get natural language suggestions from command parser
        suggestions = self.command_parser.get_suggestions(text)
        
        for suggestion in suggestions:
            # Only suggest if it starts with the current text
            if suggestion.lower().startswith(text.lower()):
                yield Completion(
                    suggestion,
                    start_position=-len(text),
                    display=suggestion
                )
    
    def _yield_all_commands(self):
        """Yield all available commands."""
        # Direct script commands
        direct_scripts = self.command_parser.registry.get_direct_script_commands()
        for script in direct_scripts:
            yield Completion(
                script.script_name,
                start_position=0,
                display=f"{script.script_name} - {script.description}"
            )
        
        # Natural language command examples
        commands = self.command_parser.get_all_commands()
        for command in commands:
            if command.examples:
                yield Completion(
                    command.examples[0],
                    start_position=0,
                    display=f"{command.examples[0]} - {command.description}"
                )
    
    def _yield_command_completions(self, current_word: str):
        """Yield command name completions."""
        # Direct script commands
        direct_scripts = self.command_parser.registry.get_direct_script_commands()
        for script in direct_scripts:
            if script.script_name.startswith(current_word):
                yield Completion(
                    script.script_name,
                    start_position=-len(current_word),
                    display=f"{script.script_name} - {script.description}"
                )
        
        # Natural language command keywords
        commands = self.command_parser.get_all_commands()
        keywords = set()
        for command in commands:
            for example in command.examples:
                first_word = example.split()[0]
                keywords.add(first_word)
        
        for keyword in keywords:
            if keyword.startswith(current_word):
                yield Completion(
                    keyword,
                    start_position=-len(current_word),
                    display=keyword
                )
    
    def _yield_parameter_completions(self, script_name: str, current_word: str, words: List[str]):
        """Yield parameter completions for direct script commands."""
        script_pattern = self.command_parser.registry.find_direct_script(script_name)
        if not script_pattern:
            return
        
        # If current word starts with --, suggest parameters
        if current_word.startswith('--'):
            param_name = current_word[2:]
            all_params = (script_pattern.required_params + 
                         script_pattern.optional_params + 
                         script_pattern.boolean_flags)
            
            for param in all_params:
                if param.startswith(param_name):
                    yield Completion(
                        f"--{param}",
                        start_position=-len(current_word),
                        display=f"--{param}"
                    )
        
        # If current word is empty and previous word was a parameter, suggest values
        elif len(words) >= 2 and words[-2].startswith('--'):
            param_name = words[-2][2:]
            self._yield_parameter_value_completions(param_name, current_word)
        
        # If no current word and we're not after a parameter, suggest available parameters
        elif not current_word or not current_word.startswith('--'):
            used_params = set()
            for word in words[1:]:  # Skip script name
                if word.startswith('--'):
                    used_params.add(word[2:])
            
            all_params = (script_pattern.required_params + 
                         script_pattern.optional_params + 
                         script_pattern.boolean_flags)
            
            for param in all_params:
                if param not in used_params:
                    yield Completion(
                        f"--{param}",
                        start_position=0,
                        display=f"--{param}"
                    )
    
    def _yield_parameter_value_completions(self, param_name: str, current_value: str):
        """Yield parameter value completions."""
        # Common parameter value suggestions
        value_suggestions = {
            'format': ['json', 'html', 'csv', 'xlsx'],
            'log-level': ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            'output': ['report.html', 'dashboard.html', 'analytics.json', 'data.xlsx']
        }
        
        if param_name in value_suggestions:
            for value in value_suggestions[param_name]:
                if value.startswith(current_value):
                    yield Completion(
                        value,
                        start_position=-len(current_value),
                        display=value
                    )


class GitLabREPL:
    """Interactive REPL for GitLab Tools CLI."""
    
    def __init__(self, debug: bool = False):
        """Initialize the REPL."""
        self.debug = debug
        self.logger = create_cli_logger(debug=debug)
        self.command_parser = CommandParser()
        self.command_executor = CommandExecutor(self.logger)
        self.help_system = HelpSystem(self.command_parser)
        self.running = True
        self.dry_run = False
        
        # Set up prompt session
        self.setup_prompt_session()
        
        # Set up signal handlers
        self.setup_signal_handlers()
    
    def setup_prompt_session(self):
        """Set up the prompt session with history and completion."""
        # Create history file
        history_file = Path.home() / '.glt_history'
        history_file.parent.mkdir(exist_ok=True)
        
        # Create completer
        completer = GitLabCompleter(self.command_parser)
        
        # Create style
        style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'command': '#0000aa',
            'parameter': '#aa0000',
            'success': '#00aa00',
            'error': '#aa0000',
            'warning': '#aa5500',
        })
        
        # Create key bindings
        bindings = KeyBindings()
        
        @bindings.add('c-c')
        def _(event):
            """Handle Ctrl+C."""
            if self.command_executor.current_process:
                self.command_executor.cancel_execution()
            else:
                event.app.exit(exception=KeyboardInterrupt)
        
        @bindings.add('c-d')
        def _(event):
            """Handle Ctrl+D (EOF)."""
            if len(event.app.current_buffer.text) == 0:
                event.app.exit()
        
        # Create prompt session
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            completer=completer,
            style=style,
            key_bindings=bindings,
            complete_while_typing=True,
            enable_history_search=True
        )
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info("\n🛑 Interrupted by user")
            if self.command_executor.current_process:
                self.command_executor.cancel_execution()
            self.running = False
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def show_welcome(self):
        """Show welcome message."""
        welcome_text = f"""
🚀 GitLab Tools CLI v{__version__}
Type 'help' for available commands or 'exit' to quit.

Command Types:
  💬 Natural Language: "create issues for project 123"
  🔧 Direct Scripts: "rename_branches --groups AI-ML-Services --dry-run"

Examples:
  > create issues for project 123
  > generate_executive_dashboard --groups 1721,1267,1269
  > weekly report for group 5
  > rename_branches --groups "AI-ML-Services" --old-branch trunk --new-branch main
  > sync_issues --help

💡 Use Tab for auto-completion and ↑/↓ for command history.
💡 Add '--help' to any direct script command for usage info.
"""
        print(welcome_text)
    
    def get_prompt_text(self) -> FormattedText:
        """Get the formatted prompt text."""
        if self.dry_run:
            return FormattedText([
                ('class:prompt', 'glt'),
                ('class:warning', ' [DRY-RUN]'),
                ('class:prompt', '> ')
            ])
        else:
            return FormattedText([
                ('class:prompt', 'glt> ')
            ])
    
    def run(self) -> int:
        """Run the REPL."""
        try:
            self.show_welcome()
            
            while self.running:
                try:
                    # Get user input
                    with patch_stdout():
                        user_input = self.session.prompt(self.get_prompt_text())
                    
                    if not user_input.strip():
                        continue
                    
                    # Handle special commands
                    if self.handle_special_commands(user_input.strip()):
                        continue
                    
                    # Parse and execute command
                    self.execute_command(user_input.strip())
                    
                except KeyboardInterrupt:
                    self.logger.info("\n🛑 Use 'exit' to quit or Ctrl+D")
                    continue
                except EOFError:
                    self.logger.info("\n👋 Goodbye!")
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error: {e}")
                    if self.debug:
                        raise
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            if self.debug:
                raise
            return 1
    
    def handle_special_commands(self, user_input: str) -> bool:
        """
        Handle special REPL commands.
        
        Args:
            user_input: The user input
            
        Returns:
            True if command was handled, False otherwise
        """
        command = user_input.lower().strip()
        
        # Exit commands
        if command in ['exit', 'quit', 'q']:
            self.logger.info("👋 Goodbye!")
            self.running = False
            return True
        
        # Clear screen
        if command in ['clear', 'cls']:
            os.system('cls' if os.name == 'nt' else 'clear')
            return True
        
        # Help commands
        if command == 'help' or command == '?':
            self.help_system.show_general_help()
            return True
        
        if command.startswith('help '):
            command_name = command[5:].strip()
            self.help_system.show_command_help(command_name)
            return True
        
        # History commands
        if command in ['history', 'hist']:
            self.show_command_history()
            return True
        
        # Dry run toggle
        if command in ['dry-run', 'dryrun', 'dry']:
            self.dry_run = not self.dry_run
            status = "enabled" if self.dry_run else "disabled"
            self.logger.info(f"🔧 Dry-run mode {status}")
            self.command_executor.dry_run = self.dry_run
            return True
        
        # Debug toggle
        if command in ['debug']:
            self.debug = not self.debug
            status = "enabled" if self.debug else "disabled"
            self.logger.info(f"🐛 Debug mode {status}")
            return True
        
        # Show version
        if command in ['version', 'ver']:
            self.logger.info(f"GitLab Tools CLI v{__version__}")
            return True
        
        # Show status
        if command in ['status', 'info']:
            self.show_status()
            return True
        
        # List commands
        if command in ['list-commands', 'list', 'commands']:
            self.show_all_commands()
            return True
        
        return False
    
    def show_all_commands(self):
        """Show all available commands (both natural language and direct scripts)."""
        print("\n📋 All Available Commands\n")
        
        # Direct script commands
        print("🔧 Direct Script Commands:")
        direct_scripts = self.command_parser.registry.get_direct_script_commands()
        for script in direct_scripts:
            print(f"  {script.script_name:<25} - {script.description}")
        
        print("\n💬 Natural Language Commands:")
        commands = self.command_parser.get_all_commands()
        seen_scripts = set()
        
        for command in commands:
            if command.script_path not in seen_scripts:
                seen_scripts.add(command.script_path)
                script_name = command.script_path.split('/')[-1].replace('.py', '')
                print(f"  {script_name:<25} - {command.description}")
        
        print("\n💡 Type 'help <command>' for detailed help on any command")
        print("💡 Add '--help' to any direct script command for usage info")
    
    def execute_command(self, user_input: str):
        """
        Parse and execute a user command.
        
        Args:
            user_input: The user input to execute
        """
        self.logger.debug(f"Parsing command: {user_input}")
        
        # Parse the command
        parsed_command = self.command_parser.parse(user_input)
        
        if not parsed_command:
            self.logger.error("❌ Command not recognized. Type 'help' for available commands.")
            # Show suggestions
            suggestions = self.command_parser.get_suggestions(user_input)
            if suggestions:
                self.logger.info("💡 Did you mean:")
                for suggestion in suggestions[:5]:  # Show top 5 suggestions
                    self.logger.info(f"  • {suggestion}")
            return
        
        # Show what we parsed (in debug mode)
        if self.debug:
            self.logger.debug(f"Parsed: {parsed_command}")
        
        # Handle direct script commands
        if isinstance(parsed_command, DirectScriptCommand):
            self._execute_direct_script_command(parsed_command)
            return
        
        # Handle natural language commands (ParsedCommand)
        self._execute_natural_language_command(parsed_command)
    
    def _execute_direct_script_command(self, direct_command: DirectScriptCommand):
        """Execute a direct script command."""
        # Handle help requests
        if 'help' in direct_command.parameters:
            self.help_system.show_script_usage(direct_command.script.script_name)
            return
        
        # Validate parameters
        is_valid, errors = self.command_parser.validate_direct_script_parameters(direct_command)
        if not is_valid:
            self.logger.error("❌ Invalid parameters:")
            for error in errors:
                self.logger.error(f"  • {error}")
            return
        
        # Execute the direct script command
        self.logger.progress(f"Executing: {direct_command.original_input}")
        
        def progress_callback(line: str):
            """Callback for progress updates."""
            # Progress updates are handled by the executor's stream reading
            pass
        
        try:
            result = self.command_executor.execute_direct_script(direct_command, progress_callback)
            
            # Format and display result
            if result.status == ExecutionStatus.SUCCESS:
                self.logger.success("✅ Direct script completed successfully!")
                if result.output and not self.dry_run:
                    self.logger.result("Output summary available in execution history")
            elif result.status == ExecutionStatus.CANCELLED:
                self.logger.warning("⏹️ Script cancelled")
            else:
                self.logger.error(f"❌ Script failed (exit code: {result.return_code})")
                if result.error:
                    self.logger.error(f"Error: {result.error}")
        
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            if self.debug:
                raise
    
    def _execute_natural_language_command(self, parsed_command: ParsedCommand):
        """Execute a natural language command."""
        # Validate parameters
        is_valid, errors = self.command_parser.validate_parameters(parsed_command)
        if not is_valid:
            self.logger.error("❌ Invalid parameters:")
            for error in errors:
                self.logger.error(f"  • {error}")
            return
        
        # Show confidence warning for fuzzy matches
        if parsed_command.confidence < 1.0:
            self.logger.warning(f"⚠️ Fuzzy match (confidence: {parsed_command.confidence:.2f})")
            self.logger.info(f"Executing: {parsed_command.command.description}")
            
            # Ask for confirmation for low confidence matches
            if parsed_command.confidence < 0.8:
                try:
                    if not confirm("Continue with this command?"):
                        self.logger.info("Command cancelled")
                        return
                except KeyboardInterrupt:
                    self.logger.info("Command cancelled")
                    return
        
        # Execute the command
        self.logger.progress(f"Executing: {parsed_command.original_input}")
        
        def progress_callback(line: str):
            """Callback for progress updates."""
            # Progress updates are handled by the executor's stream reading
            pass
        
        try:
            result = self.command_executor.execute(parsed_command, progress_callback)
            
            # Format and display result
            if result.status == ExecutionStatus.SUCCESS:
                self.logger.success("✅ Command completed successfully!")
                if result.output and not self.dry_run:
                    self.logger.result("Output summary available in execution history")
            elif result.status == ExecutionStatus.CANCELLED:
                self.logger.warning("⏹️ Command cancelled")
            else:
                self.logger.error(f"❌ Command failed (exit code: {result.return_code})")
                if result.error:
                    self.logger.error(f"Error: {result.error}")
            
        except Exception as e:
            self.logger.error(f"❌ Execution error: {e}")
            if self.debug:
                raise
    
    def show_command_history(self):
        """Show command execution history."""
        history = self.command_executor.get_execution_history()
        
        if not history:
            self.logger.info("📜 No command history")
            return
        
        self.logger.info("📜 Command History:")
        for i, result in enumerate(history[-10:], 1):  # Show last 10
            status_emoji = {
                ExecutionStatus.SUCCESS: "✅",
                ExecutionStatus.FAILED: "❌",
                ExecutionStatus.CANCELLED: "⏹️"
            }.get(result.status, "❓")
            
            self.logger.info(f"{i:2d}. {status_emoji} {result.command.original_input} "
                           f"({result.execution_time:.1f}s)")
    
    def show_status(self):
        """Show current REPL status."""
        self.logger.info("📊 Status:")
        self.logger.info(f"  • Version: {__version__}")
        self.logger.info(f"  • Debug mode: {'enabled' if self.debug else 'disabled'}")
        self.logger.info(f"  • Dry-run mode: {'enabled' if self.dry_run else 'disabled'}")
        
        # Show execution stats
        history = self.command_executor.get_execution_history()
        if history:
            successful = sum(1 for r in history if r.status == ExecutionStatus.SUCCESS)
            failed = sum(1 for r in history if r.status == ExecutionStatus.FAILED)
            self.logger.info(f"  • Commands executed: {len(history)} (✅ {successful}, ❌ {failed})")
        
        # Show available commands
        commands = self.command_parser.get_all_commands()
        self.logger.info(f"  • Available commands: {len(commands)}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.command_executor.current_process:
            self.command_executor.cancel_execution()
        
        # Save any pending history
        if hasattr(self.session, 'history'):
            try:
                self.session.history.save()
            except Exception:
                pass  # Ignore errors saving history 