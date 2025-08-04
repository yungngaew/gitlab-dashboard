"""
Unit tests for command parser functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.cli.command_parser import CommandParser, ParsedCommand
from src.cli.command_registry import CommandPattern


class TestCommandParser:
    """Test cases for CommandParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()
    
    def test_parse_exact_command_match(self):
        """Test parsing exact command matches."""
        result = self.parser.parse("create issues for project 123")
        
        assert result is not None
        assert result.confidence == 1.0
        assert result.original_input == "create issues for project 123"
        assert "project_id" in result.parameters
        assert result.parameters["project_id"] == "123"
    
    def test_parse_empty_input(self):
        """Test parsing empty or whitespace-only input."""
        assert self.parser.parse("") is None
        assert self.parser.parse("   ") is None
        assert self.parser.parse(None) is None
    
    def test_parse_rename_branches_command(self):
        """Test parsing branch rename commands."""
        test_cases = [
            ("rename branches from master to main", {"old_branch": "master", "new_branch": "main"}),
            ("rename branches in AI-ML-Services from trunk to main", 
             {"group": "AI-ML-Services", "old_branch": "trunk", "new_branch": "main"}),
            ("rename branches in project-group", {"group": "project-group"})
        ]
        
        for command, expected_params in test_cases:
            result = self.parser.parse(command)
            
            assert result is not None
            assert result.command.script_path == "scripts/rename_branches.py"
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value
    
    def test_parse_create_issues_command(self):
        """Test parsing create issues commands."""
        test_cases = [
            ("create issues for project 123", {"project_id": "123"}),
            ("create issues from issues_folder", {"folder": "issues_folder"}),
            ("create issues", {})
        ]
        
        for command, expected_params in test_cases:
            result = self.parser.parse(command)
            
            assert result is not None
            assert result.command.script_path == "scripts/create_issues.py"
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value
    
    def test_parse_generate_dashboard_command(self):
        """Test parsing dashboard generation commands."""
        test_cases = [
            ("generate dashboard for groups 1,2,3", {"group_ids": "1,2,3"}),
            ("generate executive dashboard", {}),
            ("generate dashboard for group 5", {"group_ids": "5"})
        ]
        
        for command, expected_params in test_cases:
            result = self.parser.parse(command)
            
            assert result is not None
            assert result.command.script_path == "scripts/generate_executive_dashboard.py"
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value
    
    def test_parse_weekly_report_command(self):
        """Test parsing weekly report commands."""
        test_cases = [
            ("weekly report for groups 1,2,3", {"group_ids": "1,2,3"}),
            ("productivity report email to team@company.com", {"email": "team@company.com"}),
            ("weekly report for group 5 send to manager@company.com", 
             {"group_ids": "5", "email": "manager@company.com"})
        ]
        
        for command, expected_params in test_cases:
            result = self.parser.parse(command)
            
            assert result is not None
            assert result.command.script_path == "scripts/weekly_reports.py"
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value
    
    def test_parse_send_email_command(self):
        """Test parsing send email commands."""
        test_cases = [
            ("send report.pdf to team@company.com", {"file": "report.pdf", "email": "team@company.com"}),
            ("send weekly_report.html to manager@company.com", 
             {"file": "weekly_report.html", "email": "manager@company.com"})
        ]
        
        for command, expected_params in test_cases:
            result = self.parser.parse(command)
            
            assert result is not None
            assert result.command.script_path == "scripts/send_report_email.py"
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value
    
    def test_parse_command_aliases(self):
        """Test parsing command aliases."""
        aliases_tests = [
            ("add issues for project 123", "scripts/create_issues.py"),
            ("make dashboard for groups 1,2", "scripts/generate_executive_dashboard.py"),
            ("team report for group 5", "scripts/weekly_reports.py"),
            ("analysis project 123", "scripts/analyze_projects.py")
        ]
        
        for command, expected_script in aliases_tests:
            result = self.parser.parse(command)
            
            assert result is not None
            assert result.command.script_path == expected_script
    
    def test_fuzzy_matching(self):
        """Test fuzzy matching for partially matching commands."""
        # Test with minor typos or variations
        fuzzy_tests = [
            "creat issues for project 123",  # typo in 'create'
            "generat dashboard",  # typo in 'generate'
            "weeky report",  # typo in 'weekly'
        ]
        
        for command in fuzzy_tests:
            result = self.parser.parse(command)
            # Should still find a match but with lower confidence
            assert result is not None
            assert result.confidence < 1.0
    
    def test_parameter_extraction_edge_cases(self):
        """Test parameter extraction edge cases."""
        edge_cases = [
            ("create issues for project   123   ", {"project_id": "123"}),  # Extra whitespace
            ("weekly report for groups 1, 2, 3", {"group_ids": "1, 2, 3"}),  # Spaces in list
            ("send report.pdf to user@domain.co.uk", {"file": "report.pdf", "email": "user@domain.co.uk"}),  # Complex email
        ]
        
        for command, expected_params in edge_cases:
            result = self.parser.parse(command)
            
            assert result is not None
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value
    
    def test_no_command_match(self):
        """Test when no command matches."""
        no_match_tests = [
            "this is not a valid command",
            "xyz abc def",
            "help me with something random"
        ]
        
        for command in no_match_tests:
            result = self.parser.parse(command)
            # Should return None or have very low confidence
            assert result is None or result.confidence < 0.5
    
    def test_parameter_validation(self):
        """Test parameter validation functionality."""
        # Test valid parameters
        result = self.parser.parse("create issues for project 123")
        is_valid, errors = self.parser.validate_parameters(result)
        assert is_valid
        assert len(errors) == 0
        
        # Test with invalid project ID
        result = self.parser.parse("create issues for project abc")
        result.parameters["project_id"] = "abc"  # Force invalid value
        is_valid, errors = self.parser.validate_parameters(result)
        assert not is_valid
        assert len(errors) > 0
        assert "project_id" in errors[0]
        
        # Test with invalid email
        result = self.parser.parse("send report.pdf to invalid-email")
        result.parameters["email"] = "invalid-email"  # Force invalid value
        is_valid, errors = self.parser.validate_parameters(result)
        assert not is_valid
        assert len(errors) > 0
        assert "email" in errors[0]
    
    def test_command_suggestions(self):
        """Test command suggestions functionality."""
        # Test with partial input
        suggestions = self.parser.get_suggestions("creat")
        assert len(suggestions) > 0
        assert any("create" in suggestion for suggestion in suggestions)
        
        # Test with empty input
        suggestions = self.parser.get_suggestions("")
        assert len(suggestions) > 0
        assert "create issues" in suggestions
        
        # Test with no match
        suggestions = self.parser.get_suggestions("xyz")
        assert isinstance(suggestions, list)  # Should return empty list or default suggestions
    
    def test_command_help(self):
        """Test command help functionality."""
        # Test getting help for a specific command
        help_info = self.parser.get_command_help("create")
        assert help_info is not None
        assert "create" in help_info.pattern.lower()
        
        # Test with alias
        help_info = self.parser.get_command_help("add")
        assert help_info is not None
        
        # Test with non-existent command
        help_info = self.parser.get_command_help("nonexistent")
        assert help_info is None
    
    def test_command_history(self):
        """Test command history functionality."""
        # Initially empty
        assert len(self.parser.get_command_history()) == 0
        
        # Parse some commands
        self.parser.parse("create issues for project 123")
        self.parser.parse("generate dashboard")
        
        history = self.parser.get_command_history()
        assert len(history) == 2
        assert history[0].original_input == "create issues for project 123"
        assert history[1].original_input == "generate dashboard"
        
        # Clear history
        self.parser.clear_history()
        assert len(self.parser.get_command_history()) == 0
    
    def test_similarity_calculation(self):
        """Test similarity calculation method."""
        # Test exact match
        similarity = self.parser._calculate_similarity("create issues", "create issues")
        assert similarity == 1.0
        
        # Test partial match
        similarity = self.parser._calculate_similarity("create issues", "create")
        assert 0.0 < similarity < 1.0
        
        # Test no match
        similarity = self.parser._calculate_similarity("create issues", "xyz abc")
        assert similarity < 0.5
    
    def test_extract_common_parameters(self):
        """Test common parameter extraction."""
        test_cases = [
            ("project 123", {"project_id": "123"}),
            ("groups 1,2,3", {"group_ids": "1,2,3"}),
            ("email user@domain.com", {"email": "user@domain.com"}),
            ("file report.pdf", {"file": "report.pdf"}),
            ("from master to main", {"old_branch": "master", "new_branch": "main"})
        ]
        
        for input_text, expected_params in test_cases:
            extracted = self.parser._extract_common_parameters(input_text)
            for key, value in expected_params.items():
                assert extracted.get(key) == value
    
    def test_parsed_command_str_representation(self):
        """Test string representation of ParsedCommand."""
        result = self.parser.parse("create issues for project 123")
        str_repr = str(result)
        
        assert "Command:" in str_repr
        assert "Params:" in str_repr
        assert "Confidence:" in str_repr
        assert "123" in str_repr
    
    def test_complex_command_parsing(self):
        """Test parsing complex commands with multiple parameters."""
        complex_commands = [
            "weekly report for groups 1,2,3 and email to team@company.com",
            "rename branches in AI-ML-Services from trunk to main",
            "generate dashboard for groups 1,5,10 and send to manager@company.com"
        ]
        
        for command in complex_commands:
            result = self.parser.parse(command)
            assert result is not None
            assert len(result.parameters) > 0
    
    def test_case_insensitive_parsing(self):
        """Test that parsing is case insensitive."""
        case_variants = [
            "CREATE ISSUES FOR PROJECT 123",
            "Create Issues For Project 123",
            "create issues for project 123",
            "CrEaTe IsSuEs FoR pRoJeCt 123"
        ]
        
        results = [self.parser.parse(command) for command in case_variants]
        
        # All should parse successfully
        for result in results:
            assert result is not None
            assert result.parameters.get("project_id") == "123" 