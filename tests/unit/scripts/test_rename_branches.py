"""Tests for rename_branches script."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestBranchRenaming:
    """Test branch renaming functionality."""
    
    @patch('scripts.rename_branches.GitLabClient')
    def test_get_projects_to_process(self, mock_client_class):
        """Test getting projects to process."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock groups and projects
        mock_groups = [
            {'id': 1, 'name': 'Group 1'},
            {'id': 2, 'name': 'Group 2'}
        ]
        mock_client.get_groups.return_value = mock_groups
        
        mock_projects = [
            {'id': 101, 'name': 'Project 1', 'default_branch': 'trunk'},
            {'id': 102, 'name': 'Project 2', 'default_branch': 'main'},
            {'id': 103, 'name': 'Project 3', 'default_branch': 'trunk'}
        ]
        mock_client.get_all_projects.return_value = mock_projects
        
        from scripts.rename_branches import get_projects_to_process
        
        # Test with group filter
        projects = get_projects_to_process(mock_client, group_names=['Group 1'])
        assert len(projects) > 0
        
        # Test with project filter
        projects = get_projects_to_process(mock_client, project_ids=[101])
        assert len(projects) == 1
        assert projects[0]['id'] == 101
    
    @patch('scripts.rename_branches.GitLabClient')
    def test_check_branch_exists(self, mock_client_class):
        """Test checking if branch exists."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock branch data
        mock_branches = [
            {'name': 'main'},
            {'name': 'trunk'},
            {'name': 'develop'}
        ]
        mock_client.get_project_branches.return_value = mock_branches
        
        from scripts.rename_branches import check_branch_exists
        
        assert check_branch_exists(mock_client, 101, 'trunk') is True
        assert check_branch_exists(mock_client, 101, 'main') is True
        assert check_branch_exists(mock_client, 101, 'feature') is False
    
    @patch('scripts.rename_branches.GitLabClient')
    def test_is_protected_branch(self, mock_client_class):
        """Test checking if branch is protected."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock protected branches
        mock_protected = [
            {'name': 'main'},
            {'name': 'trunk'}
        ]
        mock_client.get_protected_branches.return_value = mock_protected
        
        from scripts.rename_branches import is_protected_branch
        
        assert is_protected_branch(mock_client, 101, 'trunk') is True
        assert is_protected_branch(mock_client, 101, 'main') is True
        assert is_protected_branch(mock_client, 101, 'develop') is False
    
    @patch('scripts.rename_branches.GitLabClient')
    def test_rename_branch(self, mock_client_class):
        """Test renaming a branch."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock API responses
        mock_client.create_branch.return_value = {'name': 'main'}
        mock_client.delete_branch.return_value = True
        mock_client.update_default_branch.return_value = {'default_branch': 'main'}
        
        from scripts.rename_branches import rename_branch
        
        project = {'id': 101, 'name': 'Test Project'}
        result = rename_branch(mock_client, project, 'trunk', 'main')
        
        assert result['success'] is True
        assert result['project_id'] == 101
        assert result['old_branch'] == 'trunk'
        assert result['new_branch'] == 'main'
        
        # Verify API calls
        mock_client.create_branch.assert_called_once_with(101, 'main', 'trunk')
        mock_client.update_default_branch.assert_called_once_with(101, 'main')
        mock_client.delete_branch.assert_called_once_with(101, 'trunk')
    
    @patch('scripts.rename_branches.GitLabClient')
    def test_rename_branch_with_protection(self, mock_client_class):
        """Test renaming a protected branch."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock protected branch
        mock_protection = {
            'name': 'trunk',
            'push_access_levels': [{'access_level': 40}],
            'merge_access_levels': [{'access_level': 40}]
        }
        mock_client.get_protected_branch.return_value = mock_protection
        mock_client.create_branch.return_value = {'name': 'main'}
        
        from scripts.rename_branches import rename_branch_with_protection
        
        project = {'id': 101, 'name': 'Test Project'}
        result = rename_branch_with_protection(
            mock_client, project, 'trunk', 'main', mock_protection
        )
        
        assert result['success'] is True
        assert result['protection_transferred'] is True
        
        # Verify protection was transferred
        mock_client.protect_branch.assert_called_once()
        mock_client.unprotect_branch.assert_called_once_with(101, 'trunk')
    
    @patch('scripts.rename_branches.GitLabClient')
    def test_rename_branch_failure(self, mock_client_class):
        """Test handling rename failure."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock API failure
        mock_client.create_branch.side_effect = Exception("API Error")
        
        from scripts.rename_branches import rename_branch
        
        project = {'id': 101, 'name': 'Test Project'}
        result = rename_branch(mock_client, project, 'trunk', 'main')
        
        assert result['success'] is False
        assert 'API Error' in result['error']
        
        # Should not call delete if create failed
        mock_client.delete_branch.assert_not_called()
    
    def test_process_rename_operations_dry_run(self):
        """Test processing renames in dry run mode."""
        from scripts.rename_branches import process_rename_operations
        
        mock_client = Mock()
        projects = [
            {'id': 101, 'name': 'Project 1', 'default_branch': 'trunk'},
            {'id': 102, 'name': 'Project 2', 'default_branch': 'trunk'}
        ]
        
        # Mock branch checks
        with patch('scripts.rename_branches.check_branch_exists', return_value=True):
            with patch('scripts.rename_branches.is_protected_branch', return_value=False):
                results = process_rename_operations(
                    mock_client, projects, 'trunk', 'main', dry_run=True
                )
        
        assert len(results) == 2
        assert all(r['dry_run'] for r in results)
        assert all(r['would_rename'] for r in results)
    
    def test_generate_report(self):
        """Test report generation."""
        from scripts.rename_branches import generate_report
        
        results = [
            {
                'project_id': 101,
                'project_name': 'Project 1',
                'success': True,
                'old_branch': 'trunk',
                'new_branch': 'main'
            },
            {
                'project_id': 102,
                'project_name': 'Project 2',
                'success': False,
                'error': 'Branch not found'
            }
        ]
        
        # Test markdown report
        md_report = generate_report(results, 'markdown')
        assert '# Branch Rename Report' in md_report
        assert 'Project 1' in md_report
        assert 'Success' in md_report
        assert 'Failed' in md_report
        
        # Test JSON report
        json_report = generate_report(results, 'json')
        data = json.loads(json_report)
        assert data['total_projects'] == 2
        assert data['successful'] == 1
        assert data['failed'] == 1


class TestBranchValidation:
    """Test branch validation functions."""
    
    def test_validate_branch_name(self):
        """Test branch name validation."""
        from scripts.rename_branches import validate_branch_name
        
        # Valid names
        assert validate_branch_name('main') is True
        assert validate_branch_name('feature/new-feature') is True
        assert validate_branch_name('release-1.0') is True
        
        # Invalid names
        assert validate_branch_name('') is False
        assert validate_branch_name('branch with spaces') is False
        assert validate_branch_name('branch~name') is False
        assert validate_branch_name('..branch') is False
    
    def test_check_merge_requests(self):
        """Test checking for open merge requests."""
        from scripts.rename_branches import check_open_merge_requests
        
        mock_client = Mock()
        
        # No open MRs
        mock_client.get_project_merge_requests.return_value = []
        assert check_open_merge_requests(mock_client, 101, 'trunk') == 0
        
        # Has open MRs
        mock_mrs = [
            {'source_branch': 'trunk', 'state': 'opened'},
            {'source_branch': 'feature', 'state': 'opened'},
            {'source_branch': 'trunk', 'state': 'closed'}
        ]
        mock_client.get_project_merge_requests.return_value = mock_mrs
        assert check_open_merge_requests(mock_client, 101, 'trunk') == 1


class TestConfigurationHandling:
    """Test configuration handling."""
    
    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
branch_operations:
  old_branch_name: develop
  new_branch_name: main
  skip_protected: true
  
groups:
  - AI-ML-Services
  - Research Repos
"""
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.exists', return_value=True):
                from scripts.rename_branches import load_config
                
                config = load_config('config.yaml')
                assert config['branch_operations']['old_branch_name'] == 'develop'
                assert config['branch_operations']['new_branch_name'] == 'main'
                assert len(config['groups']) == 2
    
    def test_merge_cli_args_with_config(self):
        """Test merging CLI arguments with config."""
        from scripts.rename_branches import merge_config_with_args
        
        config = {
            'branch_operations': {
                'old_branch_name': 'develop',
                'new_branch_name': 'main'
            }
        }
        
        args = Mock()
        args.old_branch = 'trunk'  # Override config
        args.new_branch = None  # Use config value
        args.groups = ['New Group']
        
        merged = merge_config_with_args(config, args)
        
        assert merged['old_branch'] == 'trunk'  # CLI override
        assert merged['new_branch'] == 'main'  # From config
        assert merged['groups'] == ['New Group']  # CLI value