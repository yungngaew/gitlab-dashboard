"""
Integration tests for GitLab Tools CLI.

Tests complete workflows from command parsing to execution.
"""

import pytest
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.cli.command_parser import CommandParser
from src.cli.command_executor import CommandExecutor, ExecutionStatus
from src.cli.repl import GitLabREPL
from src.cli.help_system import HelpSystem
from src.cli.logging_config import create_cli_logger


class TestGitLabCLIIntegration:
    """Integration tests for the complete CLI workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = create_cli_logger(debug=True)
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.logger, dry_run=True)  # Use dry run for tests
        self.help_system = HelpSystem(self.parser)
    
    def test_complete_create_issues_workflow(self):
        """Test the complete workflow for creating issues."""
        # Parse command
        parsed = self.parser.parse("create issues for project 123")
        
        assert parsed is not None
        assert parsed.confidence == 1.0
        assert parsed.parameters["project_id"] == "123"
        
        # Validate parameters
        is_valid, errors = self.parser.validate_parameters(parsed)
        assert is_valid
        assert len(errors) == 0
        
        # Execute command (dry run)
        result = self.executor.execute(parsed)
        assert result.status == ExecutionStatus.SUCCESS
        assert "DRY RUN" in result.output
    
    def test_complete_weekly_report_workflow(self):
        """Test the complete workflow for weekly reports."""
        # Parse command with multiple parameters
        parsed = self.parser.parse("weekly report for groups 1,2,3 email to team@company.com")
        
        assert parsed is not None
        assert "group_ids" in parsed.parameters
        assert "email" in parsed.parameters
        assert parsed.parameters["group_ids"] == "1,2,3"
        assert parsed.parameters["email"] == "team@company.com"
        
        # Validate parameters
        is_valid, errors = self.parser.validate_parameters(parsed)
        assert is_valid
        
        # Execute command
        result = self.executor.execute(parsed)
        assert result.status == ExecutionStatus.SUCCESS
    
    def test_complete_rename_branches_workflow(self):
        """Test the complete workflow for renaming branches."""
        # Parse command
        parsed = self.parser.parse("rename branches in AI-ML-Services from trunk to main")
        
        assert parsed is not None
        assert parsed.parameters["group"] == "AI-ML-Services"
        assert parsed.parameters["old_branch"] == "trunk"
        assert parsed.parameters["new_branch"] == "main"
        
        # Execute command
        result = self.executor.execute(parsed)
        assert result.status == ExecutionStatus.SUCCESS
    
    def test_complete_help_workflow(self):
        """Test the complete help system workflow."""
        # Test general help
        with patch('builtins.print') as mock_print:
            self.help_system.show_general_help()
            mock_print.assert_called()
            
            # Check that help content was printed
            printed_content = ''.join(str(call) for call in mock_print.call_args_list)
            assert "GitLab Tools CLI Help" in printed_content
            assert "Available Commands" in printed_content
        
        # Test specific command help
        with patch('builtins.print') as mock_print:
            self.help_system.show_command_help("create")
            mock_print.assert_called()
            
            printed_content = ''.join(str(call) for call in mock_print.call_args_list)
            assert "create" in printed_content.lower()
    
    def test_fuzzy_matching_workflow(self):
        """Test fuzzy matching workflow."""
        # Test with typos
        parsed = self.parser.parse("creat issues for project 123")  # typo in 'create'
        
        # Should still find a match with lower confidence
        assert parsed is not None
        assert parsed.confidence < 1.0
        assert parsed.confidence > 0.5  # But still reasonable
        assert "project_id" in parsed.parameters
    
    def test_command_suggestions_workflow(self):
        """Test command suggestions workflow."""
        # Test suggestions for partial input
        suggestions = self.parser.get_suggestions("creat")
        assert len(suggestions) > 0
        assert any("create" in suggestion for suggestion in suggestions)
        
        # Test suggestions for empty input
        suggestions = self.parser.get_suggestions("")
        assert len(suggestions) > 0
        assert "create issues" in suggestions
    
    def test_parameter_validation_workflow(self):
        """Test parameter validation workflow."""
        # Test with invalid project ID
        parsed = self.parser.parse("create issues for project abc")
        
        if parsed and "project_id" in parsed.parameters:
            # Force invalid value
            parsed.parameters["project_id"] = "abc"
            is_valid, errors = self.parser.validate_parameters(parsed)
            assert not is_valid
            assert len(errors) > 0
    
    def test_execution_history_workflow(self):
        """Test execution history workflow."""
        # Initially empty
        assert len(self.executor.get_execution_history()) == 0
        
        # Execute some commands
        parsed1 = self.parser.parse("create issues for project 123")
        result1 = self.executor.execute(parsed1)
        
        parsed2 = self.parser.parse("generate dashboard")
        result2 = self.executor.execute(parsed2)
        
        # Check history
        history = self.executor.get_execution_history()
        assert len(history) == 2
        assert history[0].command.original_input == "create issues for project 123"
        assert history[1].command.original_input == "generate dashboard"
        
        # Clear history
        self.executor.clear_history()
        assert len(self.executor.get_execution_history()) == 0
    
    def test_all_command_patterns(self):
        """Test all registered command patterns can be parsed."""
        test_commands = [
            "create issues for project 123",
            "create issues from issues_folder",
            "rename branches from master to main",
            "rename branches in AI-ML-Services",
            "generate dashboard for groups 1,2,3",
            "weekly report for group 5",
            "productivity report email to team@company.com",
            "analyze project 123",
            "analyze projects 123,456",
            "export analytics for projects 123,456",
            "sync issues for project 123",
            "send report.pdf to team@company.com"
        ]
        
        for command in test_commands:
            parsed = self.parser.parse(command)
            assert parsed is not None, f"Failed to parse: {command}"
            assert parsed.confidence > 0.5, f"Low confidence for: {command}"
    
    def test_command_aliases(self):
        """Test that command aliases work correctly."""
        alias_pairs = [
            ("create issues for project 123", "add issues for project 123"),
            ("generate dashboard", "make dashboard"),
            ("weekly report", "team report"),
            ("analyze project 123", "analysis project 123")
        ]
        
        for original, alias in alias_pairs:
            parsed_original = self.parser.parse(original)
            parsed_alias = self.parser.parse(alias)
            
            assert parsed_original is not None
            assert parsed_alias is not None
            assert parsed_original.command.script_path == parsed_alias.command.script_path
    
    def test_error_handling_workflow(self):
        """Test error handling in the complete workflow."""
        # Test with completely invalid command
        parsed = self.parser.parse("this is not a valid command at all")
        assert parsed is None
        
        # Test with missing required parameters
        # (This would depend on specific command requirements)
        
        # Test execution with non-existent script
        if parsed:
            # Mock a non-existent script
            original_script_path = parsed.command.script_path
            parsed.command.script_path = "non_existent_script.py"
            
            result = self.executor.execute(parsed)
            assert result.status == ExecutionStatus.FAILED
    
    @patch('src.cli.repl.PromptSession')
    def test_repl_initialization(self, mock_prompt_session):
        """Test REPL initialization workflow."""
        # Mock the prompt session to avoid actual terminal interaction
        mock_session = Mock()
        mock_prompt_session.return_value = mock_session
        
        # Initialize REPL
        repl = GitLabREPL(debug=True)
        
        # Check that components are initialized
        assert repl.command_parser is not None
        assert repl.command_executor is not None
        assert repl.help_system is not None
        assert repl.logger is not None


class TestCLIMainEntry:
    """Test the main CLI entry point."""
    
    def test_cli_version_flag(self):
        """Test the --version flag."""
        # This would require running the actual CLI
        # For now, we'll test the argument parser setup
        from glt import create_parser
        
        parser = create_parser()
        
        # Test that version argument is recognized
        with pytest.raises(SystemExit):
            parser.parse_args(['--version'])
    
    def test_cli_help_flag(self):
        """Test the --help flag."""
        from glt import create_parser
        
        parser = create_parser()
        
        # Test that help argument is recognized
        with pytest.raises(SystemExit):
            parser.parse_args(['--help'])
    
    def test_cli_debug_flag(self):
        """Test the --debug flag."""
        from glt import create_parser
        
        parser = create_parser()
        args = parser.parse_args(['--debug'])
        
        assert args.debug is True
    
    def test_cli_non_interactive_flag(self):
        """Test the --non-interactive flag."""
        from glt import create_parser
        
        parser = create_parser()
        args = parser.parse_args(['--non-interactive'])
        
        assert args.non_interactive is True


class TestEndToEndScenarios:
    """Test realistic end-to-end scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = create_cli_logger(debug=True)
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.logger, dry_run=True)
    
    def test_daily_workflow_scenario(self):
        """Test a typical daily workflow scenario."""
        daily_commands = [
            "create issues for project 123",
            "sync issues for project 123", 
            "weekly report for groups 1,2,3",
            "analyze project 123"
        ]
        
        results = []
        for command in daily_commands:
            parsed = self.parser.parse(command)
            assert parsed is not None
            
            result = self.executor.execute(parsed)
            results.append(result)
            assert result.status == ExecutionStatus.SUCCESS
        
        # Check that all commands were executed
        history = self.executor.get_execution_history()
        assert len(history) == len(daily_commands)
    
    def test_project_management_scenario(self):
        """Test a project management scenario."""
        pm_commands = [
            "generate dashboard for groups 1,2,3",
            "weekly report for groups 1,2,3 email to manager@company.com",
            "export analytics for projects 123,456,789"
        ]
        
        for command in pm_commands:
            parsed = self.parser.parse(command)
            assert parsed is not None
            assert parsed.confidence > 0.8
            
            result = self.executor.execute(parsed)
            assert result.status == ExecutionStatus.SUCCESS
    
    def test_migration_scenario(self):
        """Test a repository migration scenario."""
        migration_commands = [
            "rename branches in legacy-project from master to main",
            "rename branches in legacy-project from develop to dev", 
            "analyze project 456"  # Check the migration results
        ]
        
        for command in migration_commands:
            parsed = self.parser.parse(command)
            assert parsed is not None
            
            result = self.executor.execute(parsed)
            assert result.status == ExecutionStatus.SUCCESS
    
    def test_help_discovery_scenario(self):
        """Test a new user help discovery scenario."""
        help_system = HelpSystem(self.parser)
        
        # Simulate new user workflow
        with patch('builtins.print'):
            # General help
            help_system.show_general_help()
            
            # Specific command help
            help_system.show_command_help("create")
            help_system.show_command_help("generate")
            
            # Interactive tutorial
            help_system.show_interactive_tutorial()
            
            # Command reference
            help_system.show_command_reference()
        
        # Test command suggestions
        suggestions = self.parser.get_suggestions("creat")
        assert len(suggestions) > 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 