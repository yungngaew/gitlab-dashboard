"""Tests for create_issues script."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import csv
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestIssueCreation:
    """Test issue creation functionality."""
    
    @patch('scripts.create_issues.GitLabClient')
    @patch('scripts.create_issues.IssueService')
    def test_create_single_issue(self, mock_service_class, mock_client_class):
        """Test creating a single issue."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock successful issue creation
        mock_issue = Mock()
        mock_issue.iid = 123
        mock_issue.title = "Test Issue"
        mock_issue.web_url = "https://gitlab.example.com/issues/123"
        mock_service.create_issue.return_value = mock_issue
        
        from scripts.create_issues import IssueCreator
        
        creator = IssueCreator(mock_client, Mock())
        creator.service = mock_service
        
        # Create issue
        issue_data = {
            'title': 'Test Issue',
            'description': 'Test description',
            'labels': ['bug', 'urgent']
        }
        
        result = creator.service.create_issue(
            project_id='test-project',
            issue_data=issue_data,
            dry_run=False
        )
        
        assert result is not None
        assert result.iid == 123
        assert result.title == "Test Issue"
        
        # Verify service was called correctly
        mock_service.create_issue.assert_called_once()
    
    @patch('scripts.create_issues.GitLabClient')
    @patch('scripts.create_issues.IssueService')
    def test_create_from_template(self, mock_service_class, mock_client_class):
        """Test creating issue from template."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock template
        mock_template = Mock()
        mock_template.name = 'bug'
        mock_template.required_variables = ['bug_title', 'description']
        mock_template.optional_variables = ['steps_to_reproduce']
        mock_service.templates = {'bug': mock_template}
        
        from scripts.create_issues import IssueCreator
        
        creator = IssueCreator(mock_client, Mock())
        creator.service = mock_service
        
        # Test template listing
        creator.list_templates()
        # Should not raise any exceptions
    
    def test_parse_csv_import(self):
        """Test parsing CSV file for import."""
        csv_content = """title,description,labels,due_date,weight
"Fix login bug","Users cannot login","bug,critical","2024-12-31",5
"Add new feature","Implement user dashboard","feature,enhancement","2024-12-15",8
"""
        
        with patch('builtins.open', mock_open(read_data=csv_content)):
            from scripts.create_issues import parse_csv_file
            
            issues = parse_csv_file('test.csv')
            
            assert len(issues) == 2
            assert issues[0]['title'] == 'Fix login bug'
            assert issues[0]['labels'] == ['bug', 'critical']
            assert issues[0]['weight'] == 5
            assert issues[1]['title'] == 'Add new feature'
    
    def test_parse_json_import(self):
        """Test parsing JSON file for import."""
        json_content = json.dumps({
            'issues': [
                {
                    'title': 'Test Issue 1',
                    'description': 'Description 1',
                    'labels': ['bug']
                },
                {
                    'title': 'Test Issue 2',
                    'description': 'Description 2',
                    'labels': ['feature']
                }
            ]
        })
        
        with patch('builtins.open', mock_open(read_data=json_content)):
            from scripts.create_issues import parse_json_file
            
            issues = parse_json_file('test.json')
            
            assert len(issues) == 2
            assert issues[0]['title'] == 'Test Issue 1'
            assert issues[1]['title'] == 'Test Issue 2'
    
    def test_parse_legacy_text_format(self):
        """Test parsing legacy text format."""
        text_content = """
[Feature] User Authentication
Description: Implement secure user authentication
Acceptance: Users can login with email/password
Labels: feature, security, high-priority

________________________________________

[Bug] Fix Memory Leak
Description: Memory usage increases over time
Labels: bug, critical
"""
        
        from scripts.create_issues import parse_text_format
        
        issues = parse_text_format(text_content)
        
        assert len(issues) == 2
        assert issues[0]['title'] == 'User Authentication'
        assert 'feature' in issues[0]['labels']
        assert issues[1]['title'] == 'Fix Memory Leak'
        assert 'bug' in issues[1]['labels']
    
    @patch('scripts.create_issues.IssueService')
    def test_bulk_create_with_failures(self, mock_service_class):
        """Test bulk creation with some failures."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock mixed results
        mock_service.create_issues_bulk.return_value = {
            'total': 3,
            'created': 2,
            'failed': 1,
            'errors': ['Issue 2: Invalid data'],
            'issues': [Mock(iid=1), Mock(iid=3)]
        }
        
        issues_data = [
            {'title': 'Issue 1'},
            {'title': 'Issue 2'},  # This one fails
            {'title': 'Issue 3'}
        ]
        
        result = mock_service.create_issues_bulk(
            project_id='test-project',
            issues_data=issues_data
        )
        
        assert result['total'] == 3
        assert result['created'] == 2
        assert result['failed'] == 1
        assert len(result['errors']) == 1
    
    def test_template_variable_substitution(self):
        """Test template variable substitution."""
        from scripts.create_issues import substitute_template_variables
        
        template = """
Title: [Feature] {feature_name}
Description: Implement {feature_name} with the following:
- {requirement_1}
- {requirement_2}
Due date: {due_date}
"""
        
        variables = {
            'feature_name': 'User Dashboard',
            'requirement_1': 'Real-time updates',
            'requirement_2': 'Responsive design',
            'due_date': '2024-12-31'
        }
        
        result = substitute_template_variables(template, variables)
        
        assert '[Feature] User Dashboard' in result
        assert 'Real-time updates' in result
        assert 'Responsive design' in result
        assert '2024-12-31' in result
    
    @patch('scripts.create_issues.GitLabClient')
    def test_interactive_mode(self, mock_client_class):
        """Test interactive mode input handling."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock user inputs
        inputs = [
            '2',  # Create manually
            'Test Issue Title',  # Title
            'Test description',  # Description
            'bug, urgent',  # Labels
            '2024-12-31',  # Due date
            '5'  # Weight
        ]
        
        with patch('builtins.input', side_effect=inputs):
            from scripts.create_issues import interactive_create_issue
            
            issue_data = interactive_create_issue()
            
            assert issue_data['title'] == 'Test Issue Title'
            assert issue_data['description'] == 'Test description'
            assert issue_data['labels'] == ['bug', 'urgent']
            assert issue_data['due_date'] == '2024-12-31'
            assert issue_data['weight'] == 5
    
    def test_validate_issue_data(self):
        """Test issue data validation."""
        from scripts.create_issues import validate_issue_data
        
        # Valid data
        valid_data = {
            'title': 'Valid Issue',
            'description': 'Valid description'
        }
        assert validate_issue_data(valid_data) is True
        
        # Missing title
        invalid_data = {
            'description': 'No title'
        }
        assert validate_issue_data(invalid_data) is False
        
        # Empty title
        empty_title = {
            'title': '',
            'description': 'Empty title'
        }
        assert validate_issue_data(empty_title) is False
    
    @patch('scripts.create_issues.GitLabClient')
    def test_get_project_metadata(self, mock_client_class):
        """Test fetching project metadata."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock project data
        mock_project = {
            'id': 123,
            'name': 'Test Project',
            'default_branch': 'main'
        }
        mock_client.get_project.return_value = mock_project
        
        # Mock milestones
        mock_milestones = [
            {'id': 1, 'title': 'v1.0'},
            {'id': 2, 'title': 'v2.0'}
        ]
        mock_client._paginated_get.return_value = iter(mock_milestones)
        
        from scripts.create_issues import get_project_metadata
        
        metadata = get_project_metadata(mock_client, 'test-project')
        
        assert metadata['project']['name'] == 'Test Project'
        assert len(metadata['milestones']) == 2
        assert metadata['milestones'][0]['title'] == 'v1.0'