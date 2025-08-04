"""
Command Executor for GitLab Tools CLI.

Executes parsed commands by running the appropriate scripts.
"""

import subprocess
import sys
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .command_parser import ParsedCommand, DirectScriptCommand
from .logging_config import CLILogger


class ExecutionStatus(Enum):
    """Execution status constants."""
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of command execution."""
    
    status: ExecutionStatus
    return_code: int
    output: str
    error: str
    execution_time: float
    command: ParsedCommand
    
    def __str__(self):
        return f"Status: {self.status.value}, Code: {self.return_code}, Time: {self.execution_time:.2f}s"


class CommandExecutor:
    """Executes parsed commands by running appropriate scripts."""
    
    def __init__(self, logger: CLILogger, dry_run: bool = False):
        """
        Initialize the command executor.
        
        Args:
            logger: CLI logger instance
            dry_run: If True, don't actually execute commands
        """
        self.logger = logger
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent.parent
        self.execution_history: List[ExecutionResult] = []
        self.current_process: Optional[subprocess.Popen] = None
        self.cancelled = False
    
    def execute(self, parsed_command: ParsedCommand, 
                progress_callback: Optional[Callable[[str], None]] = None) -> ExecutionResult:
        """
        Execute a parsed command.
        
        Args:
            parsed_command: The parsed command to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = time.time()
        
        try:
            if self.dry_run:
                return self._dry_run_execute(parsed_command, start_time)
            
            # Build the command
            script_path, args = self._build_command(parsed_command)
            
            if not script_path.exists():
                self.logger.error(f"Script not found: {script_path}")
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    return_code=-1,
                    output="",
                    error=f"Script not found: {script_path}",
                    execution_time=time.time() - start_time,
                    command=parsed_command
                )
            
            self.logger.command(f"Executing: python {script_path} {' '.join(args)}")
            
            # Execute the command
            result = self._execute_subprocess(script_path, args, progress_callback)
            result.execution_time = time.time() - start_time
            result.command = parsed_command
            
            # Log the result
            if result.status == ExecutionStatus.SUCCESS:
                self.logger.success(f"Command completed successfully in {result.execution_time:.2f}s")
            else:
                self.logger.error(f"Command failed with code {result.return_code}")
            
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Unexpected error during execution: {e}")
            result = ExecutionResult(
                status=ExecutionStatus.FAILED,
                return_code=-1,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
                command=parsed_command
            )
            self.execution_history.append(result)
            return result
    
    def execute_direct_script(self, direct_command: DirectScriptCommand,
                            progress_callback: Optional[Callable[[str], None]] = None) -> ExecutionResult:
        """
        Execute a direct script command.
        
        Args:
            direct_command: The parsed direct script command to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = time.time()
        
        try:
            if self.dry_run:
                return self._dry_run_execute_direct(direct_command, start_time)
            
            # Build the command for direct script
            script_path, args = self._build_direct_command(direct_command)
            
            if not script_path.exists():
                self.logger.error(f"Script not found: {script_path}")
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    return_code=-1,
                    output="",
                    error=f"Script not found: {script_path}",
                    execution_time=time.time() - start_time,
                    command=None  # We don't have a ParsedCommand here
                )
            
            self.logger.command(f"Executing: python {script_path} {' '.join(args)}")
            
            # Execute the command
            result = self._execute_subprocess(script_path, args, progress_callback)
            result.execution_time = time.time() - start_time
            result.command = None  # Direct scripts don't use ParsedCommand
            
            # Log the result
            if result.status == ExecutionStatus.SUCCESS:
                self.logger.success(f"Direct script completed successfully in {result.execution_time:.2f}s")
            else:
                self.logger.error(f"Direct script failed with code {result.return_code}")
            
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Unexpected error during direct script execution: {e}")
            result = ExecutionResult(
                status=ExecutionStatus.FAILED,
                return_code=-1,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
                command=None
            )
            self.execution_history.append(result)
            return result
    
    def _dry_run_execute_direct(self, direct_command: DirectScriptCommand, start_time: float) -> ExecutionResult:
        """Execute direct script in dry-run mode."""
        script_path, args = self._build_direct_command(direct_command)
        
        self.logger.info(f"[DRY RUN] Would execute: python {script_path} {' '.join(args)}")
        
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            return_code=0,
            output="[DRY RUN] Direct script would be executed",
            error="",
            execution_time=time.time() - start_time,
            command=None
        )
    
    def _dry_run_execute(self, parsed_command: ParsedCommand, start_time: float) -> ExecutionResult:
        """Execute in dry-run mode (don't actually run the command)."""
        script_path, args = self._build_command(parsed_command)
        
        self.logger.info(f"[DRY RUN] Would execute: python {script_path} {' '.join(args)}")
        
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            return_code=0,
            output="[DRY RUN] Command would be executed",
            error="",
            execution_time=time.time() - start_time,
            command=parsed_command
        )
    
    def _build_command(self, parsed_command: ParsedCommand) -> tuple[Path, List[str]]:
        """
        Build the command arguments from parsed command.
        
        Args:
            parsed_command: The parsed command
            
        Returns:
            Tuple of (script_path, arguments_list)
        """
        script_path = self.project_root / parsed_command.command.script_path
        args = []
        
        # Map parameters to script arguments based on the script
        script_name = script_path.name
        
        # Add common parameters
        for param_name, param_value in parsed_command.parameters.items():
            if param_value:
                args.extend(self._map_parameter_to_args(param_name, param_value, script_name))
        
        return script_path, args
    
    def _build_direct_command(self, direct_command: DirectScriptCommand) -> tuple[Path, List[str]]:
        """
        Build the command arguments from direct script command.
        
        Args:
            direct_command: The parsed direct script command
            
        Returns:
            Tuple of (script_path, arguments_list)
        """
        script_path = self.project_root / direct_command.script.script_path
        args = []
        
        # Add parameters as script arguments using direct parameter mapping
        for param_name, param_value in direct_command.parameters.items():
            if param_value and param_value != 'true':  # Skip boolean flags with 'true' value
                mapped_args = self._map_direct_parameter_to_args(
                    param_name, param_value, direct_command.script.script_name)
                args.extend(mapped_args)
        
        # Add boolean flags
        for flag_name in direct_command.boolean_flags:
            args.append(f'--{flag_name}')
        
        # Add positional arguments (they go at the end typically)
        args.extend(direct_command.positional_args)
        
        return script_path, args
    
    def _map_direct_parameter_to_args(self, param_name: str, param_value: str, script_name: str) -> List[str]:
        """
        Map direct command parameters to script arguments with script-specific formatting.
        
        Args:
            param_name: Parameter name from the direct command
            param_value: Parameter value
            script_name: Name of the script being executed
            
        Returns:
            List of arguments for the script
        """
        # Apply script-specific parameter formatting
        formatted_value = self._format_parameter_value(param_name, param_value, script_name)
        
        # Handle special parameter name mappings for specific scripts
        if script_name == 'rename_branches':
            if param_name == 'groups':
                # rename_branches expects space-separated group names
                if ',' in formatted_value:
                    # Convert comma-separated to space-separated
                    groups = [g.strip() for g in formatted_value.split(',')]
                    formatted_value = ' '.join(groups)
                return [f'--{param_name}', formatted_value]
        
        elif script_name == 'generate_executive_dashboard':
            if param_name == 'groups':
                # executive dashboard expects comma-separated group IDs
                return [f'--{param_name}', formatted_value]
        
        elif script_name == 'sync_issues':
            if param_name == 'project_id':
                # Positional argument, handle separately
                return []  # Will be added as positional arg
        
        # Default mapping: preserve the parameter name and format value
        return [f'--{param_name}', formatted_value]
    
    def _format_parameter_value(self, param_name: str, param_value: str, script_name: str) -> str:
        """
        Format parameter values based on script requirements.
        
        Args:
            param_name: Parameter name
            param_value: Raw parameter value
            script_name: Script name
            
        Returns:
            Formatted parameter value
        """
        # Handle group formatting
        if param_name == 'groups':
            if script_name == 'rename_branches':
                # Rename branches expects space-separated group names
                if ',' in param_value:
                    groups = [g.strip().strip('"\'') for g in param_value.split(',')]
                    return ' '.join(f'"{g}"' if ' ' in g else g for g in groups)
                return param_value
            
            elif script_name == 'generate_executive_dashboard':
                # Executive dashboard expects comma-separated group IDs
                if ' ' in param_value:
                    # Convert space-separated to comma-separated
                    groups = param_value.split()
                    return ','.join(groups)
                return param_value
        
        # Remove quotes from quoted values
        if param_value.startswith('"') and param_value.endswith('"'):
            return param_value[1:-1]
        if param_value.startswith("'") and param_value.endswith("'"):
            return param_value[1:-1]
        
        return param_value
    
    def _map_parameter_to_args(self, param_name: str, param_value: str, script_name: str) -> List[str]:
        """
        Map parameter names to script-specific arguments.
        
        Args:
            param_name: Parameter name
            param_value: Parameter value
            script_name: Name of the script being executed
            
        Returns:
            List of arguments
        """
        # Common parameter mappings
        param_mappings = {
            'project_id': ['--project-id', param_value],
            'group_ids': ['--group-ids', param_value],
            'group': ['--group', param_value],
            'email': ['--email', param_value],
            'file': ['--file', param_value],
            'folder': ['--folder', param_value],
            'old_branch': ['--old-branch', param_value],
            'new_branch': ['--new-branch', param_value]
        }
        
        # Script-specific mappings
        if script_name == 'rename_branches.py':
            if param_name == 'group':
                return ['--group-name', param_value]
            elif param_name == 'old_branch':
                return ['--from-branch', param_value]
            elif param_name == 'new_branch':
                return ['--to-branch', param_value]
        
        elif script_name == 'create_issues.py':
            if param_name == 'project_id':
                return ['--project', param_value]
            elif param_name == 'folder':
                return ['--issues-dir', param_value]
        
        elif script_name == 'weekly_reports.py':
            if param_name == 'group_ids':
                return ['--groups', param_value]
            elif param_name == 'email':
                return ['--send-email', param_value]
        
        elif script_name == 'generate_executive_dashboard.py':
            if param_name == 'group_ids':
                return ['--group-ids', param_value]
        
        # Use default mapping if no specific mapping found
        return param_mappings.get(param_name, [f'--{param_name.replace("_", "-")}', param_value])
    
    def _execute_subprocess(self, script_path: Path, args: List[str], 
                          progress_callback: Optional[Callable[[str], None]] = None) -> ExecutionResult:
        """
        Execute the subprocess and capture output.
        
        Args:
            script_path: Path to the script
            args: Arguments to pass to the script
            progress_callback: Optional progress callback
            
        Returns:
            ExecutionResult
        """
        cmd = [sys.executable, str(script_path)] + args
        
        try:
            # Start the process
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.project_root
            )
            
            # Capture output in real-time
            output_lines = []
            error_lines = []
            
            # Use threads to read stdout and stderr simultaneously
            stdout_thread = threading.Thread(
                target=self._read_stream,
                args=(self.current_process.stdout, output_lines, progress_callback)
            )
            stderr_thread = threading.Thread(
                target=self._read_stream,
                args=(self.current_process.stderr, error_lines, None)
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process completion
            return_code = self.current_process.wait()
            
            # Wait for threads to finish
            stdout_thread.join()
            stderr_thread.join()
            
            output = '\n'.join(output_lines)
            error = '\n'.join(error_lines)
            
            status = ExecutionStatus.SUCCESS if return_code == 0 else ExecutionStatus.FAILED
            if self.cancelled:
                status = ExecutionStatus.CANCELLED
            
            return ExecutionResult(
                status=status,
                return_code=return_code,
                output=output,
                error=error,
                execution_time=0,  # Will be set by caller
                command=None  # Will be set by caller
            )
            
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                return_code=-1,
                output="",
                error=str(e),
                execution_time=0,
                command=None
            )
        finally:
            self.current_process = None
    
    def _read_stream(self, stream, lines_list: List[str], 
                    progress_callback: Optional[Callable[[str], None]] = None):
        """Read from a stream and collect lines."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    line = line.rstrip('\n\r')
                    lines_list.append(line)
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(line)
                    
                    # Also log to console
                    self.logger.info(line)
                    
                if self.cancelled:
                    break
        except Exception as e:
            self.logger.error(f"Error reading stream: {e}")
        finally:
            if stream:
                stream.close()
    
    def cancel_execution(self):
        """Cancel the currently running execution."""
        self.cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self.current_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self.current_process.kill()
                    self.current_process.wait()
                
                self.logger.warning("Command execution cancelled")
            except Exception as e:
                self.logger.error(f"Error cancelling execution: {e}")
    
    def get_execution_history(self) -> List[ExecutionResult]:
        """Get the execution history."""
        return self.execution_history.copy()
    
    def clear_history(self):
        """Clear the execution history."""
        self.execution_history.clear()
    
    def format_result(self, result: ExecutionResult) -> str:
        """
        Format an execution result for display.
        
        Args:
            result: The execution result
            
        Returns:
            Formatted string representation
        """
        lines = []
        
        # Status and timing
        status_emoji = {
            ExecutionStatus.SUCCESS: "✅",
            ExecutionStatus.FAILED: "❌",
            ExecutionStatus.RUNNING: "🔄",
            ExecutionStatus.CANCELLED: "⏹️"
        }
        
        emoji = status_emoji.get(result.status, "❓")
        lines.append(f"{emoji} {result.status.value.upper()} (took {result.execution_time:.2f}s)")
        
        # Command info
        if result.command:
            lines.append(f"Command: {result.command.original_input}")
            lines.append(f"Script: {result.command.command.script_path}")
        
        # Output
        if result.output:
            lines.append("\nOutput:")
            lines.append(result.output)
        
        # Errors
        if result.error:
            lines.append("\nErrors:")
            lines.append(result.error)
        
        return '\n'.join(lines) 