"""Tests for analyze_projects script."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestProjectAnalytics:
    """Test project analytics functionality."""
    
    @patch('scripts.analyze_projects.GitLabClient')
    def test_analyze_single_project(self, mock_client_class):
        """Test analyzing a single project."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock project data
        mock_project = {
            'id': 123,
            'name': 'Test Project',
            'description': 'A test project',
            'created_at': '2024-01-01T00:00:00Z',
            'last_activity_at': datetime.now().isoformat(),
            'star_count': 10,
            'forks_count': 5,
            'open_issues_count': 15,
            'statistics': {
                'commit_count': 100,
                'repository_size': 1024000,
                'lfs_objects_size': 0
            }
        }
        mock_client.get_project.return_value = mock_project
        
        # Mock commits
        mock_commits = [
            {
                'id': 'abc123',
                'created_at': datetime.now().isoformat(),
                'author_name': 'John Doe',
                'message': 'Initial commit'
            }
        ] * 20
        mock_client.get_project_commits.return_value = mock_commits
        
        # Mock branches
        mock_branches = [
            {'name': 'main', 'protected': True},
            {'name': 'develop', 'protected': False},
            {'name': 'feature/test', 'protected': False}
        ]
        mock_client.get_project_branches.return_value = mock_branches
        
        # Mock contributors
        mock_contributors = [
            {'name': 'John Doe', 'commits': 50},
            {'name': 'Jane Smith', 'commits': 30}
        ]
        mock_client.get_project_contributors.return_value = mock_contributors
        
        from scripts.analyze_projects import analyze_project
        
        result = analyze_project(mock_client, 123)
        
        assert result['project']['name'] == 'Test Project'
        assert result['metrics']['total_commits'] == 20
        assert result['metrics']['total_branches'] == 3
        assert result['metrics']['protected_branches'] == 1
        assert result['metrics']['total_contributors'] == 2
        assert result['metrics']['open_issues'] == 15
    
    @patch('scripts.analyze_projects.GitLabClient')
    def test_analyze_group(self, mock_client_class):
        """Test analyzing a group."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock group data
        mock_group = {
            'id': 456,
            'name': 'Test Group',
            'full_path': 'test-group',
            'description': 'A test group'
        }
        mock_client.get_group.return_value = mock_group
        
        # Mock group projects
        mock_projects = [
            {
                'id': 101,
                'name': 'Project 1',
                'star_count': 5,
                'open_issues_count': 10
            },
            {
                'id': 102,
                'name': 'Project 2',
                'star_count': 8,
                'open_issues_count': 5
            }
        ]
        mock_client.get_group_projects.return_value = mock_projects
        
        from scripts.analyze_projects import analyze_group
        
        with patch('scripts.analyze_projects.analyze_project') as mock_analyze:
            # Mock individual project analysis
            mock_analyze.side_effect = [
                {
                    'project': mock_projects[0],
                    'metrics': {'total_commits': 50}
                },
                {
                    'project': mock_projects[1],
                    'metrics': {'total_commits': 75}
                }
            ]
            
            result = analyze_group(mock_client, 456)
            
            assert result['group']['name'] == 'Test Group'
            assert result['summary']['total_projects'] == 2
            assert result['summary']['total_stars'] == 13
            assert result['summary']['total_issues'] == 15
            assert len(result['projects']) == 2
    
    def test_calculate_trends(self):
        """Test trend calculation."""
        from scripts.analyze_projects import calculate_trends
        
        # Mock commit data over time
        now = datetime.now()
        commits = [
            {'created_at': now.isoformat()},
            {'created_at': (now - timedelta(days=1)).isoformat()},
            {'created_at': (now - timedelta(days=7)).isoformat()},
            {'created_at': (now - timedelta(days=14)).isoformat()},
            {'created_at': (now - timedelta(days=30)).isoformat()},
            {'created_at': (now - timedelta(days=60)).isoformat()}
        ]
        
        trends = calculate_trends(commits, days=90)
        
        assert trends['last_7_days'] == 2  # 2 commits in last 7 days
        assert trends['last_30_days'] == 4  # 4 commits in last 30 days
        assert trends['last_90_days'] == 6  # All commits in last 90 days
        assert 'daily_activity' in trends
        assert 'weekly_activity' in trends
    
    def test_format_output_json(self):
        """Test JSON output formatting."""
        from scripts.analyze_projects import format_output
        
        data = {
            'project': {'name': 'Test'},
            'metrics': {'commits': 100}
        }
        
        output = format_output(data, 'json')
        parsed = json.loads(output)
        
        assert parsed['project']['name'] == 'Test'
        assert parsed['metrics']['commits'] == 100
    
    def test_format_output_markdown(self):
        """Test Markdown output formatting."""
        from scripts.analyze_projects import format_output
        
        data = {
            'project': {
                'name': 'Test Project',
                'description': 'A test project'
            },
            'metrics': {
                'total_commits': 100,
                'total_branches': 5,
                'open_issues': 10
            }
        }
        
        output = format_output(data, 'markdown')
        
        assert '# Test Project' in output
        assert 'Total Commits: 100' in output
        assert 'Total Branches: 5' in output
        assert 'Open Issues: 10' in output
    
    @patch('scripts.analyze_projects.GitLabClient')
    def test_compare_projects(self, mock_client_class):
        """Test comparing multiple projects."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        project_ids = [101, 102]
        
        with patch('scripts.analyze_projects.analyze_project') as mock_analyze:
            mock_analyze.side_effect = [
                {
                    'project': {'id': 101, 'name': 'Project A'},
                    'metrics': {
                        'total_commits': 100,
                        'total_contributors': 5,
                        'open_issues': 10
                    }
                },
                {
                    'project': {'id': 102, 'name': 'Project B'},
                    'metrics': {
                        'total_commits': 200,
                        'total_contributors': 8,
                        'open_issues': 5
                    }
                }
            ]
            
            from scripts.analyze_projects import compare_projects
            
            result = compare_projects(mock_client, project_ids)
            
            assert len(result['projects']) == 2
            assert result['comparison']['most_commits']['name'] == 'Project B'
            assert result['comparison']['most_contributors']['name'] == 'Project B'
            assert result['comparison']['most_issues']['name'] == 'Project A'
    
    def test_generate_html_report(self):
        """Test HTML report generation."""
        from scripts.analyze_projects import generate_html_report
        
        data = {
            'project': {
                'name': 'Test Project',
                'description': 'A test project'
            },
            'metrics': {
                'total_commits': 100,
                'health_score': 85
            },
            'trends': {
                'daily_activity': {
                    '2024-01-01': 5,
                    '2024-01-02': 8
                }
            }
        }
        
        html = generate_html_report(data)
        
        assert '<html' in html
        assert 'Test Project' in html
        assert 'Total Commits: 100' in html
        assert 'Chart.js' in html  # Should include charting library
    
    @patch('builtins.open', new_callable=mock_open)
    def test_export_to_excel(self, mock_file):
        """Test Excel export functionality."""
        from scripts.analyze_projects import export_to_excel
        
        data = {
            'projects': [
                {
                    'project': {'name': 'Project A'},
                    'metrics': {'commits': 100}
                },
                {
                    'project': {'name': 'Project B'},
                    'metrics': {'commits': 200}
                }
            ]
        }
        
        with patch('pandas.ExcelWriter') as mock_writer:
            export_to_excel(data, 'output.xlsx')
            mock_writer.assert_called_once()


class TestCaching:
    """Test caching functionality."""
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        from scripts.analyze_projects import generate_cache_key
        
        key1 = generate_cache_key('project', 123, days=30)
        key2 = generate_cache_key('project', 123, days=30)
        key3 = generate_cache_key('project', 456, days=30)
        
        assert key1 == key2  # Same parameters should give same key
        assert key1 != key3  # Different parameters should give different key
    
    @patch('scripts.analyze_projects.load_from_cache')
    @patch('scripts.analyze_projects.save_to_cache')
    def test_cache_usage(self, mock_save, mock_load):
        """Test cache loading and saving."""
        mock_load.return_value = None  # Cache miss
        
        from scripts.analyze_projects import analyze_with_cache
        
        mock_client = Mock()
        mock_analyze_func = Mock(return_value={'data': 'test'})
        
        result = analyze_with_cache(
            mock_client,
            'project',
            123,
            analyze_func=mock_analyze_func
        )
        
        # Should call analyze function on cache miss
        mock_analyze_func.assert_called_once()
        # Should save to cache
        mock_save.assert_called_once()
        
        # Test cache hit
        mock_load.return_value = {'cached': 'data'}
        mock_analyze_func.reset_mock()
        
        result = analyze_with_cache(
            mock_client,
            'project',
            123,
            analyze_func=mock_analyze_func
        )
        
        # Should not call analyze function on cache hit
        mock_analyze_func.assert_not_called()
        assert result == {'cached': 'data'}