"""Unit tests for branch service."""

import pytest
from unittest.mock import Mock, patch, call
from src.services.branch_service import BranchService
from src.models.branch import BranchOperation, BranchOperationType


class TestBranchService:
    """Test branch service functionality."""
    
    def test_branch_service_initialization(self, mock_gitlab_client):
        """Test branch service initialization."""
        service = BranchService(mock_gitlab_client)
        
        assert service.client == mock_gitlab_client
        assert service.operations_log == []
    
    def test_rename_branches_bulk_dry_run(self, mock_gitlab_client, sample_projects):
        """Test bulk rename in dry run mode."""
        service = BranchService(mock_gitlab_client)
        
        # Set up mocks
        mock_gitlab_client.branch_exists.side_effect = lambda pid, branch: (
            branch == 'trunk' if pid == 1 else False
        )
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False,
            'commit': {'id': 'abc123'}
        }
        
        result = service.rename_branches_bulk(
            projects=sample_projects[:2],
            old_branch='trunk',
            new_branch='main',
            dry_run=True
        )
        
        assert result['total'] == 2
        assert result['renamed'] == 1
        assert result['skipped'] == 1
        assert result['failed'] == 0
        
        # Should not actually rename in dry run
        mock_gitlab_client.create_branch.assert_not_called()
        mock_gitlab_client.delete_branch.assert_not_called()
    
    def test_rename_branches_bulk_skip_protected(self, mock_gitlab_client, sample_projects):
        """Test skipping protected branches."""
        service = BranchService(mock_gitlab_client)
        
        # Set up mocks
        mock_gitlab_client.branch_exists.return_value = True
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': True,  # Protected branch
            'commit': {'id': 'abc123'}
        }
        
        result = service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='trunk',
            new_branch='main',
            dry_run=False,
            skip_protected=True
        )
        
        assert result['total'] == 1
        assert result['renamed'] == 0
        assert result['skipped'] == 1
        assert result['failed'] == 0
        
        # Should not rename protected branch
        mock_gitlab_client.rename_branch.assert_not_called()
    
    def test_rename_branches_bulk_success(self, mock_gitlab_client, sample_projects):
        """Test successful bulk rename."""
        service = BranchService(mock_gitlab_client)
        
        # Set up mocks
        mock_gitlab_client.branch_exists.side_effect = lambda pid, branch: (
            branch == 'trunk' if branch == 'trunk' else False
        )
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False,
            'commit': {'id': 'abc123'}
        }
        mock_gitlab_client.rename_branch.return_value = True
        
        result = service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='trunk',
            new_branch='main',
            dry_run=False
        )
        
        assert result['total'] == 1
        assert result['renamed'] == 1
        assert result['skipped'] == 0
        assert result['failed'] == 0
        
        # Should call rename
        mock_gitlab_client.rename_branch.assert_called_once_with(
            1, 'trunk', 'main', update_default=False
        )
    
    def test_rename_branches_bulk_with_merge_request_update(self, mock_gitlab_client, sample_projects):
        """Test rename with merge request update."""
        service = BranchService(mock_gitlab_client)
        
        # Set up mocks
        mock_gitlab_client.branch_exists.side_effect = lambda pid, branch: (
            branch == 'trunk' if branch == 'trunk' else False
        )
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False,
            'commit': {'id': 'abc123'}
        }
        mock_gitlab_client.rename_branch.return_value = True
        
        result = service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='trunk',
            new_branch='main',
            dry_run=False,
            update_merge_requests=True
        )
        
        assert result['renamed'] == 1
        
        # Should call rename with update_merge_requests
        mock_gitlab_client.rename_branch.assert_called_once_with(
            1, 'trunk', 'main', update_default=True
        )
    
    def test_rename_branches_bulk_failure(self, mock_gitlab_client, sample_projects):
        """Test handling rename failure."""
        service = BranchService(mock_gitlab_client)
        
        # Set up mocks
        mock_gitlab_client.branch_exists.side_effect = lambda pid, branch: (
            branch == 'trunk' if branch == 'trunk' else False
        )
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False,
            'commit': {'id': 'abc123'}
        }
        mock_gitlab_client.rename_branch.side_effect = Exception("API Error")
        
        result = service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='trunk',
            new_branch='main',
            dry_run=False
        )
        
        assert result['total'] == 1
        assert result['renamed'] == 0
        assert result['skipped'] == 0
        assert result['failed'] == 1
    
    def test_rename_branches_bulk_branch_not_found(self, mock_gitlab_client, sample_projects):
        """Test handling branch not found."""
        service = BranchService(mock_gitlab_client)
        
        # Branch doesn't exist
        mock_gitlab_client.branch_exists.return_value = False
        
        result = service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='nonexistent',
            new_branch='main',
            dry_run=False
        )
        
        assert result['total'] == 1
        assert result['renamed'] == 0
        assert result['skipped'] == 1
        assert result['failed'] == 0
    
    def test_rename_branches_bulk_new_branch_exists(self, mock_gitlab_client, sample_projects):
        """Test handling when new branch already exists."""
        service = BranchService(mock_gitlab_client)
        
        # Both branches exist
        mock_gitlab_client.branch_exists.return_value = True
        
        result = service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='trunk',
            new_branch='main',
            dry_run=False
        )
        
        assert result['total'] == 1
        assert result['renamed'] == 0
        assert result['skipped'] == 1
        assert result['failed'] == 0
    
    def test_operation_logging(self, mock_gitlab_client, sample_projects):
        """Test operation logging."""
        service = BranchService(mock_gitlab_client)
        
        # Set up for successful rename
        mock_gitlab_client.branch_exists.side_effect = lambda pid, branch: (
            branch == 'trunk' if branch == 'trunk' else False
        )
        mock_gitlab_client.get_branch.return_value = {
            'name': 'trunk',
            'protected': False,
            'commit': {'id': 'abc123'}
        }
        mock_gitlab_client.rename_branch.return_value = True
        
        service.rename_branches_bulk(
            projects=[sample_projects[0]],
            old_branch='trunk',
            new_branch='main',
            dry_run=False
        )
        
        # Check operations log
        assert len(service.operations_log) == 1
        operation = service.operations_log[0]
        assert operation.project_id == 1
        assert operation.project_name == 'project-alpha'
        assert operation.operation_type == BranchOperationType.RENAME
        assert operation.old_branch == 'trunk'
        assert operation.new_branch == 'main'
        assert operation.success is True
    
    def test_export_operations_log(self, mock_gitlab_client, temp_dir):
        """Test exporting operations log."""
        service = BranchService(mock_gitlab_client)
        
        # Add some operations to log
        service.operations_log = [
            BranchOperation(
                project_id=1,
                project_name='project-1',
                operation_type=BranchOperationType.RENAME,
                old_branch='trunk',
                new_branch='main',
                success=True
            ),
            BranchOperation(
                project_id=2,
                project_name='project-2',
                operation_type=BranchOperationType.RENAME,
                old_branch='trunk',
                new_branch='main',
                success=False,
                error_message='Branch protected'
            )
        ]
        
        # Export to JSON
        json_file = temp_dir / 'operations.json'
        service.export_operations_log(str(json_file))
        
        assert json_file.exists()
        
        import json
        with open(json_file) as f:
            data = json.load(f)
        
        assert len(data) == 2
        assert data[0]['project_name'] == 'project-1'
        assert data[0]['success'] is True
        assert data[1]['error_message'] == 'Branch protected'