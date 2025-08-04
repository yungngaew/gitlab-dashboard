"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import json
import tempfile
import os

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import GitLabClient
from src.utils import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables."""
    def _mock_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
    return _mock_env


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    config_data = {
        'gitlab': {
            'rate_limit': 3,
            'timeout': 30,
            'retry_count': 3,
            'page_size': 100,
            'verify_ssl': True
        },
        'features': {
            'dry_run': False,
            'backup': True,
            'concurrent_workers': 5,
            'show_progress': True,
            'colored_output': True
        },
        'branch_operations': {
            'default_old_branch': 'trunk',
            'default_new_branch': 'main',
            'skip_protected': True,
            'update_merge_requests': True
        },
        'issue_operations': {
            'default_labels': [],
            'template_dir': 'templates/issues',
            'add_timestamp': True
        },
        'groups': [
            {
                'name': 'Test-Group',
                'filters': {
                    'exclude_archived': True,
                    'min_activity_days': 30
                }
            }
        ],
        'logging': {
            'level': 'INFO',
            'file': str(temp_dir / 'test.log'),
            'max_size': 10,
            'backup_count': 5,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }
    
    config_file = temp_dir / 'config.yaml'
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    return Config(str(config_file))


@pytest.fixture
def mock_gitlab_client():
    """Create a mocked GitLab client."""
    client = Mock(spec=GitLabClient)
    
    # Mock common methods
    client.get_projects = Mock(return_value=[
        {'id': 1, 'name': 'test-project-1', 'default_branch': 'main'},
        {'id': 2, 'name': 'test-project-2', 'default_branch': 'trunk'}
    ])
    
    client.get_project = Mock(return_value={
        'id': 1,
        'name': 'test-project',
        'default_branch': 'main',
        'description': 'Test project'
    })
    
    client.search_group_by_name = Mock(return_value={
        'id': 100,
        'name': 'Test-Group',
        'full_path': 'test-group'
    })
    
    client.branch_exists = Mock(side_effect=lambda project_id, branch: 
        branch in ['main', 'trunk', 'develop'])
    
    client.get_branch = Mock(return_value={
        'name': 'trunk',
        'protected': False,
        'commit': {'id': 'abc123'}
    })
    
    client.create_issue = Mock(return_value={
        'id': 1,
        'iid': 1,
        'title': 'Test Issue',
        'web_url': 'https://gitlab.com/test/issue/1'
    })
    
    return client


@pytest.fixture
def sample_projects():
    """Sample project data for testing."""
    return [
        {
            'id': 1,
            'name': 'project-alpha',
            'default_branch': 'trunk',
            'archived': False,
            'last_activity_at': '2024-01-01T00:00:00Z'
        },
        {
            'id': 2,
            'name': 'project-beta',
            'default_branch': 'main',
            'archived': False,
            'last_activity_at': '2024-01-02T00:00:00Z'
        },
        {
            'id': 3,
            'name': 'project-gamma',
            'default_branch': 'trunk',
            'archived': True,
            'last_activity_at': '2023-12-01T00:00:00Z'
        }
    ]


@pytest.fixture
def sample_issues():
    """Sample issue data for testing."""
    return [
        {
            'title': 'Implement feature X',
            'description': 'Feature X needs to be implemented',
            'labels': ['feature', 'priority:high'],
            'assignee_id': None,
            'milestone_id': None,
            'due_date': '2024-02-01'
        },
        {
            'title': 'Fix bug Y',
            'description': 'Bug Y is causing issues',
            'labels': ['bug', 'priority:critical'],
            'assignee_id': 123,
            'milestone_id': 1,
            'due_date': None
        }
    ]


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    def _mock_response(status_code=200, json_data=None, headers=None):
        response = Mock()
        response.status_code = status_code
        response.json = Mock(return_value=json_data or {})
        response.headers = headers or {}
        response.text = json.dumps(json_data) if json_data else ''
        response.raise_for_status = Mock()
        if status_code >= 400:
            response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        return response
    return _mock_response