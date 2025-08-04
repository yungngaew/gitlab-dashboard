"""Unit tests for board service."""

import pytest
from unittest.mock import Mock, patch

from src.services.board_service import BoardService
from src.api.client import GitLabClient


class TestBoardService:
    """Test board service functionality."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock GitLab client."""
        return Mock(spec=GitLabClient)
    
    @pytest.fixture
    def board_service(self, mock_client):
        """Board service instance with mock client."""
        return BoardService(mock_client)
    
    def test_determine_workflow_state_exact_match(self, board_service):
        """Test exact label matching for workflow states."""
        # Test exact matches
        assert board_service.determine_workflow_state("To Do") == "to_do"
        assert board_service.determine_workflow_state("In Progress") == "in_progress"
        assert board_service.determine_workflow_state("Blocked") == "blocked"
        assert board_service.determine_workflow_state("Done") == "done"
    
    def test_determine_workflow_state_case_insensitive(self, board_service):
        """Test case-insensitive label matching."""
        assert board_service.determine_workflow_state("TODO") == "to_do"
        assert board_service.determine_workflow_state("doing") == "in_progress"
        assert board_service.determine_workflow_state("BLOCKED") == "blocked"
    
    def test_determine_workflow_state_partial_match(self, board_service):
        """Test partial label matching."""
        assert board_service.determine_workflow_state("WIP - Feature X") == "in_progress"
        assert board_service.determine_workflow_state("Code Review Needed") == "in_review"
    
    def test_determine_workflow_state_unknown(self, board_service):
        """Test unknown labels default to 'other'."""
        assert board_service.determine_workflow_state("Unknown Label") == "other"
        assert board_service.determine_workflow_state("") == "other"
    
    def test_get_issue_workflow_state_closed(self, board_service):
        """Test that closed issues are always 'done'."""
        issue = {"state": "closed", "labels": ["To Do"]}
        assert board_service.get_issue_workflow_state(issue) == "done"
    
    def test_get_issue_workflow_state_open_with_labels(self, board_service):
        """Test open issues with workflow labels."""
        issue = {"state": "opened", "labels": ["In Progress", "Backend"]}
        assert board_service.get_issue_workflow_state(issue) == "in_progress"
    
    def test_get_issue_workflow_state_open_without_labels(self, board_service):
        """Test open issues without workflow labels default to 'to_do'."""
        issue = {"state": "opened", "labels": []}
        assert board_service.get_issue_workflow_state(issue) == "to_do"
    
    def test_get_issue_workflow_state_open_with_done_label(self, board_service):
        """Test open issues with 'done' labels are not categorized as 'done' by default."""
        issue = {"state": "opened", "labels": ["Done", "Complete"]}
        # Should default to 'to_do' since open issues shouldn't be marked as 'done'
        assert board_service.get_issue_workflow_state(issue) == "to_do"
    
    def test_get_issue_workflow_state_open_with_done_label_allowed(self):
        """Test open issues with 'done' labels can be categorized as 'done' when configured."""
        config = {"board_service": {"allow_open_issues_as_done": True}}
        mock_client = Mock(spec=GitLabClient)
        board_service = BoardService(mock_client, config)
        
        issue = {"state": "opened", "labels": ["Done"]}
        assert board_service.get_issue_workflow_state(issue) == "done"
    
    def test_get_issue_workflow_state_with_board_labels(self, board_service):
        """Test workflow state detection with board-specific labels."""
        board_labels = {
            "custom_progress": ["Working", "Active"],
            "custom_review": ["Reviewing"]
        }
        
        issue1 = {"state": "opened", "labels": ["Working"]}
        issue2 = {"state": "opened", "labels": ["Reviewing"]}
        
        assert board_service.get_issue_workflow_state(issue1, board_labels) == "custom_progress"
        assert board_service.get_issue_workflow_state(issue2, board_labels) == "custom_review"
    
    def test_categorize_issues_by_workflow(self, board_service):
        """Test issue categorization by workflow state."""
        issues = [
            {"state": "opened", "labels": ["To Do"]},
            {"state": "opened", "labels": ["In Progress"]},
            {"state": "opened", "labels": ["Blocked"]},
            {"state": "closed", "labels": ["Done"]},
            {"state": "opened", "labels": []}  # No labels
        ]
        
        categorized = board_service.categorize_issues_by_workflow(issues)
        
        assert len(categorized["to_do"]) == 2  # "To Do" + no labels
        assert len(categorized["in_progress"]) == 1
        assert len(categorized["blocked"]) == 1
        assert len(categorized["done"]) == 1
    
    def test_get_project_boards_success(self, board_service, mock_client):
        """Test successful board retrieval."""
        mock_boards = [
            {"id": 1, "name": "Development"},
            {"id": 2, "name": "Sprint Board"}
        ]
        mock_client.get_boards.return_value = iter(mock_boards)
        
        boards = board_service.get_project_boards("project-1")
        
        assert len(boards) == 2
        assert boards[0]["name"] == "Development"
        mock_client.get_boards.assert_called_once_with("project-1")
    
    def test_get_project_boards_error(self, board_service, mock_client):
        """Test board retrieval with error."""
        mock_client.get_boards.side_effect = Exception("API Error")
        
        boards = board_service.get_project_boards("project-1")
        
        assert boards == []
    
    def test_get_default_board(self, board_service):
        """Test default board selection."""
        with patch.object(board_service, 'get_project_boards') as mock_get_boards:
            # Test with no boards
            mock_get_boards.return_value = []
            assert board_service.get_default_board("project-1") is None
            
            # Test with development board
            mock_get_boards.return_value = [
                {"id": 1, "name": "Sprint"},
                {"id": 2, "name": "Development"}
            ]
            board = board_service.get_default_board("project-1")
            assert board["name"] == "Development"
            
            # Test with no development board (returns first)
            mock_get_boards.return_value = [
                {"id": 1, "name": "Sprint"},
                {"id": 2, "name": "Planning"}
            ]
            board = board_service.get_default_board("project-1")
            assert board["name"] == "Sprint"
    
    def test_custom_label_mappings(self):
        """Test custom label mappings from config."""
        custom_config = {
            "board_label_mappings": {
                "custom_todo": ["Backlog", "New"],
                "custom_progress": ["Active", "Working"]
            }
        }
        
        mock_client = Mock(spec=GitLabClient)
        service = BoardService(mock_client, custom_config)
        
        assert service.determine_workflow_state("Backlog") == "custom_todo"
        assert service.determine_workflow_state("Active") == "custom_progress"
        assert service.determine_workflow_state("To Do") == "other"  # Not in custom mapping