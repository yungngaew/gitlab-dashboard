"""Tests for weekly productivity reports service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from collections import defaultdict

from src.services.weekly_reports import WeeklyProductivityReporter
from src.api.client import GitLabClient


class TestWeeklyProductivityReporter:
    """Test weekly productivity reporter functionality."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock GitLab client."""
        client = Mock(spec=GitLabClient)
        
        # Mock projects response
        client.get_projects.return_value = [
            {
                'id': 1,
                'name': 'project-1',
                'path_with_namespace': 'group/project-1',
                'last_activity_at': '2024-01-15T10:00:00Z',
                'default_branch': 'main',
                'visibility': 'private'
            },
            {
                'id': 2,
                'name': 'project-2',
                'path_with_namespace': 'group/project-2',
                'last_activity_at': '2024-01-14T15:30:00Z',
                'default_branch': 'main',
                'visibility': 'internal'
            }
        ]
        
        # Mock paginated API calls
        client._paginated_get.return_value = []
        
        return client
    
    @pytest.fixture
    def mock_analytics(self):
        """Create mock analytics service."""
        analytics = Mock()
        analytics.get_project_health.return_value = {'score': 85, 'grade': 'B'}
        return analytics
    
    @pytest.fixture
    def reporter(self, mock_client):
        """Create weekly productivity reporter instance."""
        with patch('src.services.weekly_reports.AdvancedAnalytics'):
            return WeeklyProductivityReporter(mock_client)
    
    def test_init(self, mock_client):
        """Test reporter initialization."""
        with patch('src.services.weekly_reports.AdvancedAnalytics') as mock_analytics:
            reporter = WeeklyProductivityReporter(mock_client)
            
            assert reporter.client == mock_client
            mock_analytics.assert_called_once_with(mock_client)
    
    def test_generate_team_report_structure(self, reporter, mock_client):
        """Test that generate_team_report returns correct structure."""
        group_ids = [1, 2]
        
        report = reporter.generate_team_report(group_ids)
        
        # Check report structure
        assert isinstance(report, dict)
        assert 'metadata' in report
        assert 'executive_summary' in report
        assert 'team_activity' in report
        assert 'project_breakdown' in report
        assert 'individual_metrics' in report
        assert 'insights_and_actions' in report
        
        # Check metadata
        metadata = report['metadata']
        assert 'generated_at' in metadata
        assert 'period_start' in metadata
        assert 'period_end' in metadata
        assert metadata['weeks_analyzed'] == 1
        assert metadata['groups_analyzed'] == 2
    
    def test_generate_team_report_with_team_members(self, reporter):
        """Test report generation with specific team members."""
        group_ids = [1]
        team_members = ['john.doe', 'jane.smith']
        
        report = reporter.generate_team_report(
            group_ids=group_ids,
            team_members=team_members
        )
        
        metadata = report['metadata']
        assert metadata['team_size'] == 2
    
    def test_generate_team_report_multiple_weeks(self, reporter):
        """Test report generation for multiple weeks."""
        group_ids = [1]
        weeks_back = 4
        
        report = reporter.generate_team_report(
            group_ids=group_ids,
            weeks_back=weeks_back
        )
        
        metadata = report['metadata']
        assert metadata['weeks_analyzed'] == 4
        
        # Check that period spans 4 weeks
        start_date = datetime.fromisoformat(metadata['period_start'])
        end_date = datetime.fromisoformat(metadata['period_end'])
        diff = end_date - start_date
        assert diff.days >= 28  # Approximately 4 weeks
    
    def test_generate_team_activity(self, reporter, mock_client):
        """Test team activity generation."""
        # Mock commits response
        mock_commits = [
            {
                'author_name': 'John Doe',
                'created_at': '2024-01-15T10:00:00Z'
            },
            {
                'author_name': 'Jane Smith',
                'created_at': '2024-01-14T15:30:00Z'
            }
        ]
        
        # Mock merge requests response
        mock_mrs = [
            {
                'author': {'username': 'john.doe'},
                'state': 'merged'
            },
            {
                'author': {'username': 'jane.smith'},
                'state': 'opened'
            }
        ]
        
        # Mock issues response
        mock_issues = [
            {
                'assignee': {'username': 'john.doe'},
                'state': 'closed'
            }
        ]
        
        mock_client._paginated_get.side_effect = [
            mock_commits,  # First call for commits
            mock_mrs,      # Second call for MRs
            mock_issues    # Third call for issues
        ] * 2  # For both projects
        
        projects = [
            {'id': 1, 'name': 'project-1'},
            {'id': 2, 'name': 'project-2'}
        ]
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        activity = reporter._generate_team_activity(
            projects, start_date, end_date
        )
        
        # Check structure
        assert 'commits' in activity
        assert 'merge_requests' in activity
        assert 'issues' in activity
        assert 'velocity_trends' in activity
        assert 'collaboration_metrics' in activity
        
        # Check commit data
        commits = activity['commits']
        assert commits['total'] == 4  # 2 commits per project
        assert 'John Doe' in commits['by_author']
        assert 'Jane Smith' in commits['by_author']
        
        # Check MR data
        mrs = activity['merge_requests']
        assert mrs['total'] == 4  # 2 MRs per project
        assert mrs['merged'] == 2
        assert mrs['opened'] == 2
    
    def test_generate_project_breakdown(self, reporter, mock_client):
        """Test project breakdown generation."""
        # Mock responses for each project
        mock_client._paginated_get.side_effect = [
            # Project 1 - commits
            [{'created_at': '2024-01-15T10:00:00Z'}],
            # Project 1 - issues
            [{'state': 'opened', 'created_at': '2024-01-15T10:00:00Z'}],
            # Project 1 - merge requests
            [{'state': 'opened'}],
            # Project 2 - commits
            [],
            # Project 2 - issues
            [{'state': 'closed', 'created_at': '2024-01-10T10:00:00Z'}],
            # Project 2 - merge requests
            []
        ]
        
        projects = [
            {
                'id': 1,
                'name': 'active-project',
                'path_with_namespace': 'group/active-project',
                'last_activity_at': '2024-01-15T10:00:00Z',
                'default_branch': 'main',
                'visibility': 'private'
            },
            {
                'id': 2,
                'name': 'inactive-project',
                'path_with_namespace': 'group/inactive-project',
                'last_activity_at': '2024-01-01T10:00:00Z',
                'default_branch': 'main',
                'visibility': 'private'
            }
        ]
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        breakdown = reporter._generate_project_breakdown(
            projects, start_date, end_date
        )
        
        # Check structure
        assert 'projects' in breakdown
        assert 'health_summary' in breakdown
        assert 'activity_distribution' in breakdown
        
        # Check projects
        project_data = breakdown['projects']
        assert len(project_data) == 2
        
        # Check that projects are sorted by health score (worst first)
        if len(project_data) > 1:
            assert project_data[0]['health_score'] <= project_data[1]['health_score']
        
        # Check health summary
        health_summary = breakdown['health_summary']
        assert 'healthy' in health_summary
        assert 'warning' in health_summary
        assert 'critical' in health_summary
    
    def test_generate_individual_metrics(self, reporter, mock_client):
        """Test individual contributor metrics generation."""
        # Mock responses
        mock_commits = [
            {
                'author_name': 'John Doe',
                'stats': {'additions': 100, 'deletions': 50}
            },
            {
                'author_name': 'Jane Smith',
                'stats': {'additions': 200, 'deletions': 25}
            }
        ]
        
        mock_mrs = [
            {
                'author': {'username': 'john.doe'},
                'state': 'merged'
            }
        ]
        
        mock_issues = [
            {
                'author': {'username': 'jane.smith'},
                'assignee': {'username': 'john.doe'},
                'state': 'closed'
            }
        ]
        
        mock_client._paginated_get.side_effect = [
            mock_commits,  # commits
            mock_mrs,      # merge requests
            mock_issues    # issues
        ]
        
        projects = [{'id': 1, 'name': 'test-project'}]
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        metrics = reporter._generate_individual_metrics(
            projects, start_date, end_date
        )
        
        # Check structure
        assert 'contributors' in metrics
        assert 'team_stats' in metrics
        
        # Check contributors
        contributors = metrics['contributors']
        assert 'John Doe' in contributors
        assert 'Jane Smith' in contributors
        
        john_metrics = contributors['John Doe']
        assert john_metrics['commits'] == 1
        assert john_metrics['lines_added'] == 100
        assert john_metrics['lines_removed'] == 50
        assert john_metrics['merge_requests_created'] == 1
        assert john_metrics['merge_requests_merged'] == 1
        
        # Check team stats
        team_stats = metrics['team_stats']
        assert team_stats['total_contributors'] == 2
    
    def test_generate_executive_summary(self, reporter):
        """Test executive summary generation."""
        team_activity = {
            'commits': {'total': 50},
            'merge_requests': {'total': 10, 'merged': 8},
            'issues': {'total': 5}
        }
        
        project_breakdown = {
            'health_summary': {'healthy': 3, 'warning': 1, 'critical': 1}
        }
        
        individual_metrics = {
            'contributors': {
                'John Doe': {'commits': 25},
                'Jane Smith': {'commits': 15},
                'Bob Wilson': {'commits': 10}
            }
        }
        
        summary = reporter._generate_executive_summary(
            team_activity, project_breakdown, individual_metrics
        )
        
        # Check structure
        assert 'key_metrics' in summary
        assert 'trends' in summary
        assert 'highlights' in summary
        assert 'concerns' in summary
        
        # Check key metrics
        key_metrics = summary['key_metrics']
        assert key_metrics['total_commits'] == 50
        assert key_metrics['total_merge_requests'] == 10
        assert key_metrics['merge_rate'] == 80.0  # 8/10 * 100
        assert key_metrics['active_contributors'] == 3
        assert key_metrics['healthy_projects'] == 3
        assert key_metrics['projects_needing_attention'] == 2  # warning + critical
    
    def test_calculate_velocity_trends(self, reporter):
        """Test velocity trend calculation."""
        activity = {
            'commits': {
                'by_day': {
                    '2024-01-01': 5,
                    '2024-01-02': 7,
                    '2024-01-03': 8,
                    '2024-01-04': 6,
                    '2024-01-05': 10,
                    '2024-01-06': 12,
                    '2024-01-07': 9
                }
            }
        }
        
        trends = reporter._calculate_velocity_trends(activity)
        
        assert 'trend' in trends
        assert 'direction' in trends
        assert trends['trend'] == 'calculated'
        assert trends['direction'] in ['increasing', 'decreasing', 'stable']
    
    def test_calculate_collaboration_metrics(self, reporter):
        """Test collaboration metrics calculation."""
        activity = {
            'commits': {
                'by_author': {
                    'John Doe': 20,
                    'Jane Smith': 15,
                    'Bob Wilson': 10,
                    'Alice Brown': 5
                }
            }
        }
        
        metrics = reporter._calculate_collaboration_metrics(activity)
        
        assert 'collaboration_score' in metrics
        assert 'distribution' in metrics
        assert 'active_contributors' in metrics
        assert 'gini_coefficient' in metrics
        
        assert metrics['active_contributors'] == 4
        assert metrics['distribution'] in [
            'well_distributed', 'moderately_distributed', 'concentrated'
        ]
    
    def test_calculate_project_health(self, reporter):
        """Test project health calculation."""
        # Healthy project metrics
        healthy_metrics = {
            'commits_this_week': 10,
            'open_issues': 5,
            'last_commit_days_ago': 1,
            'open_merge_requests': 2
        }
        
        health_score = reporter._calculate_project_health(healthy_metrics)
        assert health_score >= 70
        
        # Unhealthy project metrics
        unhealthy_metrics = {
            'commits_this_week': 0,
            'open_issues': 25,
            'last_commit_days_ago': 15,
            'open_merge_requests': 15
        }
        
        health_score = reporter._calculate_project_health(unhealthy_metrics)
        assert health_score <= 50
    
    def test_generate_insights_and_actions(self, reporter):
        """Test insights and actions generation."""
        report = {
            'project_breakdown': {
                'projects': [
                    {'health_status': 'critical', 'name': 'project-1'},
                    {'health_status': 'critical', 'name': 'project-2'},
                    {'health_status': 'healthy', 'name': 'project-3'}
                ]
            },
            'individual_metrics': {
                'contributors': {
                    'John Doe': {'collaboration_score': 30},
                    'Jane Smith': {'collaboration_score': 80}
                }
            },
            'team_activity': {
                'merge_requests': {'total': 10, 'merged': 3}
            }
        }
        
        insights = reporter._generate_insights_and_actions(report)
        
        # Check structure
        assert 'recommended_actions' in insights
        assert 'team_focus_areas' in insights
        assert 'individual_coaching' in insights
        assert 'process_improvements' in insights
        
        # Should recommend addressing critical projects
        actions = insights['recommended_actions']
        assert len(actions) > 0
        assert any('critical' in action.get('action', '').lower() for action in actions)
        
        # Should identify low collaboration
        coaching = insights['individual_coaching']
        if coaching:
            assert any('collaboration' in item.get('focus', '') for item in coaching)
    
    @patch('src.services.weekly_reports.logger')
    def test_error_handling(self, mock_logger, reporter, mock_client):
        """Test error handling in report generation."""
        # Mock client to raise exception
        mock_client.get_projects.side_effect = Exception("API Error")
        
        # Should handle gracefully and still return a report structure
        report = reporter.generate_team_report([1])
        
        # Should log the error
        mock_logger.warning.assert_called()
        
        # Should still have basic structure
        assert isinstance(report, dict)
        assert 'metadata' in report
    
    def test_team_member_filtering(self, reporter, mock_client):
        """Test that team member filtering works correctly."""
        # Mock commits with different authors
        mock_commits = [
            {'author_name': 'John Doe', 'created_at': '2024-01-15T10:00:00Z'},
            {'author_name': 'Jane Smith', 'created_at': '2024-01-15T11:00:00Z'},
            {'author_name': 'External Contributor', 'created_at': '2024-01-15T12:00:00Z'}
        ]
        
        mock_client._paginated_get.return_value = mock_commits
        
        projects = [{'id': 1, 'name': 'test-project'}]
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        team_members = ['John Doe', 'Jane Smith']  # Exclude external contributor
        
        activity = reporter._generate_team_activity(
            projects, start_date, end_date, team_members
        )
        
        # Should only include team members
        assert activity['commits']['total'] == 2  # Not 3
        assert 'John Doe' in activity['commits']['by_author']
        assert 'Jane Smith' in activity['commits']['by_author']
        assert 'External Contributor' not in activity['commits']['by_author']