"""Integration tests for branch rename workflow."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.rename_branches import BranchRenamer, main
from src.api import GitLabClient
from src.utils import Config


@pytest.mark.integration
class TestBranchRenameWorkflow:
    """Test complete branch rename workflow."""
    
    def test_full_rename_workflow_dry_run(self, mock_gitlab_client, test_config, capsys):
        """Test complete workflow in dry run mode."""
        # Set dry run
        test_config.data['features']['dry_run'] = True
        
        # Set up mock responses
        mock_gitlab_client.search_group_by_name.return_value = {
            'id': 100,
            'name': 'Test-Group'
        }
        
        mock_gitlab_client.get_projects.return_value = [
            {'id': 1, 'name': 'project-1', 'archived': False},
            {'id': 2, 'name': 'project-2', 'archived': False}
        ]
        
        mock_gitlab_client.branch_exists.side_effect = lambda pid, branch: (
            branch == 'trunk' and pid == 1
        )
        
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False
        }
        
        # Create renamer and process
        renamer = BranchRenamer(mock_gitlab_client, test_config)
        success = renamer.process_group('Test-Group', 'trunk', 'main')
        
        assert success is True
        assert renamer.stats['total'] == 2
        assert renamer.stats['renamed'] == 1  # Only project-1 has trunk
        assert renamer.stats['skipped'] == 1
        
        # Check output
        renamer.print_summary()
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out
        assert "Successfully renamed: 1" in captured.out
    
    @patch('scripts.rename_branches.GitLabClient')
    @patch('scripts.rename_branches.Config')
    def test_main_function_with_args(self, mock_config_class, mock_client_class, temp_dir):
        """Test main function with command line arguments."""
        # Set up mocks
        mock_config = Mock()
        mock_config.is_dry_run.return_value = True
        mock_config.get_groups.return_value = [{'name': 'Test-Group'}]
        mock_config.get_gitlab_config.return_value = {
            'url': 'https://gitlab.test.com',
            'token': 'test-token'
        }
        mock_config.get_log_config.return_value = {
            'level': 'INFO',
            'file': str(temp_dir / 'test.log')
        }
        mock_config.get.return_value = True
        mock_config.validate.return_value = None
        mock_config_class.return_value = mock_config
        
        mock_client = Mock()
        mock_client.search_group_by_name.return_value = {'id': 1, 'name': 'Test-Group'}
        mock_client.get_projects.return_value = []
        mock_client_class.return_value = mock_client
        
        # Test with dry run argument
        test_args = [
            'rename_branches.py',
            '--dry-run',
            '--old-branch', 'develop',
            '--new-branch', 'main'
        ]
        
        with patch('sys.argv', test_args):
            exit_code = main()
        
        assert exit_code == 1  # No projects processed
        mock_config.validate.assert_called_once()
        mock_client_class.assert_called_once()
    
    def test_rename_with_protected_branches(self, mock_gitlab_client, test_config):
        """Test handling of protected branches."""
        mock_gitlab_client.search_group_by_name.return_value = {
            'id': 100,
            'name': 'Test-Group'
        }
        
        mock_gitlab_client.get_projects.return_value = [
            {'id': 1, 'name': 'project-1', 'archived': False}
        ]
        
        mock_gitlab_client.branch_exists.return_value = True
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': True  # Protected branch
        }
        
        renamer = BranchRenamer(mock_gitlab_client, test_config)
        renamer.process_group('Test-Group', 'trunk', 'main')
        
        assert renamer.stats['skipped'] == 1
        assert renamer.stats['renamed'] == 0
        
        # Should not attempt to rename
        mock_gitlab_client.rename_branch.assert_not_called()
    
    def test_rename_with_api_failure(self, mock_gitlab_client, test_config):
        """Test handling API failures during rename."""
        mock_gitlab_client.search_group_by_name.return_value = {
            'id': 100,
            'name': 'Test-Group'
        }
        
        mock_gitlab_client.get_projects.return_value = [
            {'id': 1, 'name': 'project-1', 'archived': False}
        ]
        
        mock_gitlab_client.branch_exists.side_effect = [True, False]  # trunk exists, main doesn't
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False
        }
        
        # Make rename fail
        mock_gitlab_client.rename_branch.side_effect = Exception("API Error")
        
        renamer = BranchRenamer(mock_gitlab_client, test_config)
        renamer.dry_run = False  # Not dry run
        renamer.process_group('Test-Group', 'trunk', 'main')
        
        assert renamer.stats['failed'] == 1
        assert renamer.stats['renamed'] == 0
    
    def test_rename_multiple_groups(self, mock_gitlab_client, test_config, capsys):
        """Test processing multiple groups."""
        # Set up two groups
        mock_gitlab_client.search_group_by_name.side_effect = lambda name: {
            'Test-Group-1': {'id': 100, 'name': 'Test-Group-1'},
            'Test-Group-2': {'id': 200, 'name': 'Test-Group-2'}
        }.get(name)
        
        mock_gitlab_client.get_projects.side_effect = [
            [{'id': 1, 'name': 'project-1', 'archived': False}],  # Group 1
            [{'id': 2, 'name': 'project-2', 'archived': False}]   # Group 2
        ]
        
        mock_gitlab_client.branch_exists.return_value = False  # No trunk branches
        
        renamer = BranchRenamer(mock_gitlab_client, test_config)
        
        # Process both groups
        renamer.process_group('Test-Group-1', 'trunk', 'main')
        renamer.process_group('Test-Group-2', 'trunk', 'main')
        
        assert renamer.stats['total'] == 2
        assert renamer.stats['skipped'] == 2
        
        renamer.print_summary()
        captured = capsys.readouterr()
        assert "Total projects processed: 2" in captured.out