"""Unit tests for analytics services."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from src.services.analytics import GitLabAnalytics
from src.services.analytics_advanced import AdvancedAnalytics


class TestGitLabAnalytics:
    """Test basic analytics service."""
    
    def test_get_project_metrics(self, mock_gitlab_client):
        """Test getting project metrics."""
        # Mock project data
        mock_gitlab_client.get_project.return_value = {
            'id': 1,
            'name': 'test-project',
            'path_with_namespace': 'group/test-project',
            'created_at': '2024-01-01T00:00:00Z',
            'last_activity_at': '2024-06-01T00:00:00Z',
            'default_branch': 'main',
            'visibility': 'private',
            'archived': False
        }
        
        # Mock paginated responses
        mock_gitlab_client._paginated_get.side_effect = [
            # Commits
            [
                {'created_at': '2024-06-01T10:00:00Z', 'author_name': 'User1'},
                {'created_at': '2024-06-02T10:00:00Z', 'author_name': 'User2'}
            ],
            # Branches
            [
                {'name': 'main', 'protected': True, 'commit': {'created_at': '2024-06-01T00:00:00Z'}},
                {'name': 'develop', 'protected': False, 'commit': {'created_at': '2024-05-01T00:00:00Z'}}
            ],
            # Issues
            [
                {'state': 'opened', 'labels': ['bug']},
                {'state': 'closed', 'labels': ['feature']}
            ],
            # Merge requests
            [
                {'state': 'opened'},
                {'state': 'merged'}
            ],
            # Contributors
            [
                {'name': 'User1', 'email': 'user1@example.com', 'commits': 10},
                {'name': 'User2', 'email': 'user2@example.com', 'commits': 5}
            ]
        ]
        
        analytics = GitLabAnalytics(mock_gitlab_client)
        metrics = analytics.get_project_metrics(1)
        
        assert metrics['project']['name'] == 'test-project'
        assert metrics['commits']['total'] == 2
        assert metrics['branches']['total'] == 2
        assert metrics['issues']['total'] == 2
        assert metrics['issues']['open'] == 1
        assert metrics['merge_requests']['total'] == 2
        assert metrics['contributors']['total'] == 2
    
    def test_generate_markdown_report(self, mock_gitlab_client):
        """Test markdown report generation."""
        analytics = GitLabAnalytics(mock_gitlab_client)
        
        metrics = {
            'project': {
                'name': 'test-project',
                'path': 'group/test-project',
                'created_at': '2024-01-01',
                'last_activity_at': '2024-06-01',
                'default_branch': 'main',
                'visibility': 'private'
            },
            'commits': {
                'total': 100,
                'average_per_day': 3.3,
                'by_author': {'User1': 60, 'User2': 40}
            },
            'branches': {
                'total': 5,
                'active': 3,
                'stale': 2,
                'protected': 1
            },
            'issues': {
                'total': 50,
                'open': 10,
                'closed': 40,
                'closure_rate': 0.8
            },
            'merge_requests': {
                'total': 30,
                'open': 5,
                'merged': 20,
                'merge_rate': 0.67
            },
            'contributors': {
                'total': 5,
                'top_contributors': [
                    {'name': 'User1', 'commits': 60, 'additions': 1000, 'deletions': 200}
                ]
            }
        }
        
        report = analytics.generate_summary_report(metrics, format='markdown')
        
        assert '# GitLab Analytics Report: test-project' in report
        assert '**Total Commits (last 30 days):** 100' in report
        assert '**Open Issues:** 10' in report
        assert '**Merge Rate:** 67.0%' in report
        assert 'User1: 60 commits' in report


class TestAdvancedAnalytics:
    """Test advanced analytics features."""
    
    def test_calculate_health_score(self, mock_gitlab_client):
        """Test health score calculation."""
        analytics = AdvancedAnalytics(mock_gitlab_client)
        
        metrics = {
            'commits': {
                'weekly_average': 10,
                'commit_trend': 0.5,
                'unique_authors': 5
            },
            'issues': {
                'total_created': 20,
                'open_issues': 5,
                'avg_resolution_days': 7
            },
            'merge_requests': {
                'total_created': 15,
                'merge_rate': 0.8,
                'avg_merge_hours': 12
            }
        }
        
        health = analytics._calculate_health_score(metrics)
        
        assert 'score' in health
        assert 'grade' in health
        assert 'factors' in health
        assert 'recommendations' in health
        assert 0 <= health['score'] <= 100
        assert health['grade'] in ['A', 'B', 'C', 'D', 'F']
    
    def test_analyze_commit_trends(self, mock_gitlab_client):
        """Test commit trend analysis."""
        # Mock commits over time
        commits = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(30):
            commits.append({
                'created_at': (base_date + timedelta(days=i)).isoformat() + 'Z',
                'author_name': f'User{i % 3}',
                'message': 'Test commit'
            })
        
        mock_gitlab_client._paginated_get.return_value = commits
        
        analytics = AdvancedAnalytics(mock_gitlab_client)
        trends = analytics._analyze_commit_trends(
            1, 
            base_date, 
            datetime.now()
        )
        
        assert trends['total_commits'] == 30
        assert trends['unique_authors'] == 3
        assert 'weekly_average' in trends
        assert 'commit_trend' in trends
        assert 'most_active_day' in trends
    
    def test_compare_projects(self, mock_gitlab_client):
        """Test project comparison."""
        # Mock project data
        projects = [
            {'id': 1, 'name': 'project-1'},
            {'id': 2, 'name': 'project-2'}
        ]
        
        mock_gitlab_client.get_project.side_effect = projects
        
        # Mock empty trends for simplicity
        mock_gitlab_client._paginated_get.return_value = []
        
        analytics = AdvancedAnalytics(mock_gitlab_client)
        comparison = analytics.compare_projects([1, 2])
        
        assert 'projects' in comparison
        assert 'rankings' in comparison
        assert len(comparison['projects']) == 2
        assert 1 in comparison['projects']
        assert 2 in comparison['projects']
    
    def test_generate_recommendations(self, mock_gitlab_client):
        """Test recommendation generation."""
        analytics = AdvancedAnalytics(mock_gitlab_client)
        
        metrics = {
            'commits': {
                'commit_trend': -0.7,
                'weekly_average': 0.5,
                'unique_authors': 1
            },
            'issues': {
                'avg_resolution_days': 45,
                'issues_without_assignee': 10,
                'total_created': 20,
                'overdue_issues': 5
            },
            'merge_requests': {
                'merge_rate': 0.5,
                'avg_merge_hours': 200
            }
        }
        
        recommendations = analytics._generate_recommendations(metrics, 50)
        
        assert len(recommendations) > 0
        assert any('declining' in r for r in recommendations)
        assert any('low commit activity' in r.lower() for r in recommendations)
        assert any('overdue' in r for r in recommendations)