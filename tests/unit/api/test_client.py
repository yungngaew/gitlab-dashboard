"""Unit tests for GitLab API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from src.api.client import GitLabClient
from src.api.exceptions import (
    GitLabAPIError, 
    AuthenticationError, 
    RateLimitError,
    ProjectNotFoundError
)


class TestGitLabClient:
    """Test GitLab API client functionality."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = GitLabClient(
            url="https://gitlab.example.com",
            token="test-token"
        )
        
        assert client.base_url == "https://gitlab.example.com/api/v4"
        assert client.session.headers['PRIVATE-TOKEN'] == "test-token"
        assert client.session.headers['Accept'] == "application/json"
    
    def test_client_with_trailing_slash(self):
        """Test client initialization with trailing slash in URL."""
        client = GitLabClient(
            url="https://gitlab.example.com/",
            token="test-token"
        )
        
        assert client.base_url == "https://gitlab.example.com/api/v4"
    
    @patch('requests.Session.get')
    def test_get_projects_pagination(self, mock_get, mock_response):
        """Test project listing with pagination."""
        # Mock paginated responses
        page1_response = mock_response(
            status_code=200,
            json_data=[{'id': 1}, {'id': 2}],
            headers={'X-Next-Page': '2'}
        )
        page2_response = mock_response(
            status_code=200,
            json_data=[{'id': 3}],
            headers={'X-Next-Page': ''}
        )
        
        mock_get.side_effect = [page1_response, page2_response]
        
        client = GitLabClient("https://gitlab.example.com", "token")
        projects = list(client.get_projects())
        
        assert len(projects) == 3
        assert projects[0]['id'] == 1
        assert projects[2]['id'] == 3
        assert mock_get.call_count == 2
    
    @patch('requests.Session.get')
    def test_get_project_by_id(self, mock_get, mock_response):
        """Test getting a project by ID."""
        project_data = {
            'id': 123,
            'name': 'test-project',
            'default_branch': 'main'
        }
        mock_get.return_value = mock_response(
            status_code=200,
            json_data=project_data
        )
        
        client = GitLabClient("https://gitlab.example.com", "token")
        project = client.get_project(123)
        
        assert project['id'] == 123
        assert project['name'] == 'test-project'
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_search_group_by_name(self, mock_get, mock_response):
        """Test searching for a group by name."""
        groups_data = [
            {'id': 1, 'name': 'other-group'},
            {'id': 2, 'name': 'target-group', 'full_path': 'org/target-group'}
        ]
        mock_get.return_value = mock_response(
            status_code=200,
            json_data=groups_data
        )
        
        client = GitLabClient("https://gitlab.example.com", "token")
        group = client.search_group_by_name('target-group')
        
        assert group is not None
        assert group['id'] == 2
        assert group['name'] == 'target-group'
    
    @patch('requests.Session.get')
    def test_branch_exists_true(self, mock_get, mock_response):
        """Test checking if a branch exists (exists case)."""
        mock_get.return_value = mock_response(
            status_code=200,
            json_data={'name': 'main'}
        )
        
        client = GitLabClient("https://gitlab.example.com", "token")
        exists = client.branch_exists(123, 'main')
        
        assert exists is True
    
    @patch('requests.Session.get')
    def test_branch_exists_false(self, mock_get, mock_response):
        """Test checking if a branch exists (not exists case)."""
        mock_get.return_value = mock_response(status_code=404)
        
        client = GitLabClient("https://gitlab.example.com", "token")
        exists = client.branch_exists(123, 'nonexistent')
        
        assert exists is False
    
    @patch('requests.Session.post')
    def test_create_issue(self, mock_post, mock_response):
        """Test creating an issue."""
        issue_data = {
            'id': 1,
            'iid': 1,
            'title': 'Test Issue',
            'web_url': 'https://gitlab.example.com/project/issues/1'
        }
        mock_post.return_value = mock_response(
            status_code=201,
            json_data=issue_data
        )
        
        client = GitLabClient("https://gitlab.example.com", "token")
        issue = client.create_issue(
            project_id=123,
            title="Test Issue",
            description="Test description"
        )
        
        assert issue['id'] == 1
        assert issue['title'] == 'Test Issue'
        mock_post.assert_called_once()
    
    @patch('requests.Session.get')
    def test_authentication_error(self, mock_get, mock_response):
        """Test authentication error handling."""
        mock_get.return_value = mock_response(status_code=401)
        
        client = GitLabClient("https://gitlab.example.com", "token")
        
        with pytest.raises(AuthenticationError):
            client.get_projects()
    
    @patch('requests.Session.get')
    def test_rate_limit_error(self, mock_get, mock_response):
        """Test rate limit error handling."""
        mock_get.return_value = mock_response(
            status_code=429,
            headers={'Retry-After': '60'}
        )
        
        client = GitLabClient("https://gitlab.example.com", "token")
        
        with pytest.raises(RateLimitError) as exc_info:
            client.get_projects()
        
        assert exc_info.value.retry_after == 60
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    @patch('requests.Session.delete')
    def test_rename_branch(self, mock_delete, mock_get, mock_post, mock_response):
        """Test renaming a branch."""
        # Mock getting the old branch
        mock_get.return_value = mock_response(
            status_code=200,
            json_data={'name': 'old-branch', 'commit': {'id': 'abc123'}}
        )
        
        # Mock creating new branch
        mock_post.return_value = mock_response(status_code=201)
        
        # Mock deleting old branch
        mock_delete.return_value = mock_response(status_code=204)
        
        client = GitLabClient("https://gitlab.example.com", "token")
        result = client.rename_branch(123, 'old-branch', 'new-branch')
        
        assert result is True
        assert mock_get.call_count == 1
        assert mock_post.call_count == 1
        assert mock_delete.call_count == 1
    
    @patch('requests.Session.get')
    def test_retry_on_server_error(self, mock_get, mock_response):
        """Test retry logic on server errors."""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            mock_response(status_code=500),
            mock_response(status_code=502),
            mock_response(status_code=200, json_data=[{'id': 1}])
        ]
        
        client = GitLabClient(
            "https://gitlab.example.com", 
            "token",
            config={'retry_count': 3}
        )
        
        projects = list(client.get_projects())
        
        assert len(projects) == 1
        assert mock_get.call_count == 3
    
    def test_session_configuration(self):
        """Test session configuration options."""
        client = GitLabClient(
            "https://gitlab.example.com",
            "token",
            config={
                'timeout': 60,
                'verify_ssl': False
            }
        )
        
        # Check timeout is set (this is implementation specific)
        # In real implementation, you'd check session.timeout or similar
        assert client.config['timeout'] == 60
    
    @patch('src.api.client.GitLabClient._paginated_get')
    def test_get_boards(self, mock_paginated_get):
        """Test getting project boards."""
        # Mock response
        mock_paginated_get.return_value = iter([
            {'id': 1, 'name': 'Development'},
            {'id': 2, 'name': 'Release'}
        ])
        
        client = GitLabClient("https://gitlab.example.com", "token")
        boards = list(client.get_boards('123'))
        
        assert len(boards) == 2
        assert boards[0]['name'] == 'Development'
        mock_paginated_get.assert_called_once_with('projects/123/boards')
    
    @patch('src.api.client.GitLabClient._paginated_get') 
    def test_get_board_lists(self, mock_paginated_get):
        """Test getting board lists."""
        # Mock response
        mock_paginated_get.return_value = iter([
            {'id': 1, 'label': {'name': 'To Do'}},
            {'id': 2, 'label': {'name': 'In Progress'}}
        ])
        
        client = GitLabClient("https://gitlab.example.com", "token")
        lists = list(client.get_board_lists('123', 456))
        
        assert len(lists) == 2
        assert lists[0]['label']['name'] == 'To Do'
        mock_paginated_get.assert_called_once_with('projects/123/boards/456/lists')
    
    @patch('src.api.client.GitLabClient._paginated_get')
    def test_get_board_issues(self, mock_paginated_get):
        """Test getting board issues."""
        # Mock response
        mock_paginated_get.return_value = iter([
            {'id': 1, 'title': 'Test Issue 1'},
            {'id': 2, 'title': 'Test Issue 2'}
        ])
        
        client = GitLabClient("https://gitlab.example.com", "token")
        issues = list(client.get_board_issues('123', 456))
        
        assert len(issues) == 2
        assert issues[0]['title'] == 'Test Issue 1'
        mock_paginated_get.assert_called_once_with('projects/123/boards/456/issues')
    
    @patch('src.api.client.GitLabClient._paginated_get')
    def test_get_board_issues_with_list(self, mock_paginated_get):
        """Test getting issues from specific board list."""
        mock_paginated_get.return_value = iter([
            {'id': 1, 'title': 'List Issue'}
        ])
        
        client = GitLabClient("https://gitlab.example.com", "token")
        issues = list(client.get_board_issues('123', 456, list_id=789))
        
        assert len(issues) == 1
        mock_paginated_get.assert_called_once_with('projects/123/boards/456/lists/789/issues')
        assert client.config['verify_ssl'] is False