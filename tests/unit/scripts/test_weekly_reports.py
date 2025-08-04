"""Tests for weekly_reports script."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestWeeklyReports:
    """Test weekly reports generation."""
    
    @patch('scripts.weekly_reports.GitLabClient')
    def test_collect_weekly_data(self, mock_client_class):
        """Test collecting weekly data for groups."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock groups
        mock_groups = [
            {'id': 1, 'name': 'Group 1', 'full_path': 'group1'}
        ]
        mock_client.get_groups.return_value = mock_groups
        
        # Mock projects
        mock_projects = [
            {
                'id': 101,
                'name': 'Project 1',
                'last_activity_at': datetime.now().isoformat()
            }
        ]
        mock_client.get_group_projects.return_value = mock_projects
        
        # Mock commits
        now = datetime.now()
        mock_commits = [
            {
                'id': 'abc123',
                'created_at': now.isoformat(),
                'author_name': 'John Doe',
                'author_email': 'john@example.com',
                'message': 'Fix bug'
            },
            {
                'id': 'def456',
                'created_at': (now - timedelta(days=2)).isoformat(),
                'author_name': 'Jane Smith',
                'author_email': 'jane@example.com',
                'message': 'Add feature'
            }
        ]
        mock_client._paginated_get.return_value = iter(mock_commits)
        
        # Mock merge requests
        mock_mrs = [
            {
                'id': 1,
                'title': 'Fix critical bug',
                'state': 'merged',
                'created_at': (now - timedelta(days=3)).isoformat(),
                'merged_at': (now - timedelta(days=1)).isoformat(),
                'author': {'name': 'John Doe'}
            }
        ]
        
        # Mock issues
        mock_issues = [
            {
                'id': 1,
                'title': 'Bug report',
                'state': 'closed',
                'created_at': (now - timedelta(days=5)).isoformat(),
                'closed_at': (now - timedelta(days=2)).isoformat()
            }
        ]
        
        with patch('scripts.weekly_reports.WeeklyProductivityReporter') as mock_reporter:
            from scripts.weekly_reports import collect_weekly_data
            
            instance = mock_reporter.return_value
            instance.generate_report.return_value = {
                'summary': {
                    'total_commits': 2,
                    'total_merge_requests': 1,
                    'total_issues_closed': 1
                },
                'groups': mock_groups,
                'projects': mock_projects
            }
            
            result = collect_weekly_data(mock_client, [1], weeks=1)
            
            assert result['summary']['total_commits'] == 2
            assert result['summary']['total_merge_requests'] == 1
            assert result['summary']['total_issues_closed'] == 1
    
    def test_generate_weekly_summary(self):
        """Test generating weekly summary."""
        from scripts.weekly_reports import generate_weekly_summary
        
        data = {
            'summary': {
                'total_commits': 50,
                'total_merge_requests': 10,
                'total_issues_closed': 15,
                'unique_contributors': 5
            },
            'team_members': [
                {
                    'name': 'John Doe',
                    'commits': 20,
                    'merge_requests': 5,
                    'issues_closed': 8
                },
                {
                    'name': 'Jane Smith',
                    'commits': 30,
                    'merge_requests': 5,
                    'issues_closed': 7
                }
            ],
            'projects': [
                {
                    'name': 'Project A',
                    'commits': 30,
                    'health_score': 85
                },
                {
                    'name': 'Project B',
                    'commits': 20,
                    'health_score': 75
                }
            ]
        }
        
        summary = generate_weekly_summary(data)
        
        assert '50 commits' in summary
        assert '10 merge requests' in summary
        assert '15 issues' in summary
        assert 'John Doe' in summary
        assert 'Jane Smith' in summary
        assert 'Project A' in summary
        assert 'Project B' in summary
    
    @patch('scripts.weekly_reports.EmailService')
    def test_send_email_report(self, mock_email_class):
        """Test sending email report."""
        mock_email = Mock()
        mock_email_class.return_value = mock_email
        mock_email.send_report.return_value = True
        
        from scripts.weekly_reports import send_email_report
        
        report_data = {
            'summary': {'total_commits': 50},
            'team_name': 'Development Team'
        }
        
        recipients = ['team@example.com', 'manager@example.com']
        
        result = send_email_report(report_data, recipients)
        
        assert result is True
        mock_email.send_report.assert_called_once()
        
        # Check email was sent to all recipients
        call_args = mock_email.send_report.call_args
        assert all(r in call_args[0][0] for r in recipients)
    
    def test_format_team_performance(self):
        """Test formatting team performance data."""
        from scripts.weekly_reports import format_team_performance
        
        team_data = [
            {
                'name': 'John Doe',
                'commits': 25,
                'merge_requests': 5,
                'issues_closed': 10,
                'projects': ['Project A', 'Project B']
            },
            {
                'name': 'Jane Smith',
                'commits': 30,
                'merge_requests': 8,
                'issues_closed': 5,
                'projects': ['Project B', 'Project C']
            }
        ]
        
        formatted = format_team_performance(team_data)
        
        # Should be sorted by total contributions
        assert formatted[0]['name'] == 'Jane Smith'  # 30+8+5 = 43
        assert formatted[1]['name'] == 'John Doe'   # 25+5+10 = 40
        
        # Should include performance metrics
        assert 'productivity_score' in formatted[0]
        assert 'contribution_percentage' in formatted[0]
    
    def test_generate_html_email(self):
        """Test HTML email generation."""
        from scripts.weekly_reports import generate_html_email
        
        report_data = {
            'team_name': 'Development Team',
            'period': 'Week of Jan 1-7, 2024',
            'summary': {
                'total_commits': 100,
                'total_merge_requests': 20,
                'total_issues_closed': 30,
                'unique_contributors': 8
            },
            'highlights': [
                'Completed authentication feature',
                'Fixed 15 critical bugs',
                'Improved CI/CD pipeline'
            ],
            'team_members': [
                {
                    'name': 'John Doe',
                    'commits': 40,
                    'merge_requests': 8
                }
            ]
        }
        
        html = generate_html_email(report_data)
        
        assert '<html' in html
        assert 'Development Team' in html
        assert 'Week of Jan 1-7, 2024' in html
        assert '100' in html  # commits
        assert 'John Doe' in html
        assert 'Completed authentication feature' in html
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_report_to_file(self, mock_file):
        """Test saving report to file."""
        from scripts.weekly_reports import save_report
        
        report_data = {
            'summary': {'total_commits': 50},
            'team_name': 'Test Team'
        }
        
        # Test JSON format
        save_report(report_data, 'report.json', format='json')
        mock_file.assert_called_with('report.json', 'w', encoding='utf-8')
        
        # Test HTML format
        save_report(report_data, 'report.html', format='html')
        assert mock_file.call_count == 2
        
        # Test Markdown format
        save_report(report_data, 'report.md', format='markdown')
        assert mock_file.call_count == 3
    
    def test_calculate_productivity_metrics(self):
        """Test productivity metrics calculation."""
        from scripts.weekly_reports import calculate_productivity_metrics
        
        contributor_data = {
            'commits': 20,
            'merge_requests': 5,
            'issues_closed': 10,
            'code_reviews': 8
        }
        
        metrics = calculate_productivity_metrics(contributor_data)
        
        assert 'productivity_score' in metrics
        assert 'efficiency_rating' in metrics
        assert 'collaboration_score' in metrics
        assert metrics['productivity_score'] > 0
    
    def test_identify_top_performers(self):
        """Test identifying top performers."""
        from scripts.weekly_reports import identify_top_performers
        
        team_data = [
            {'name': 'John', 'productivity_score': 85},
            {'name': 'Jane', 'productivity_score': 92},
            {'name': 'Bob', 'productivity_score': 78},
            {'name': 'Alice', 'productivity_score': 88}
        ]
        
        top = identify_top_performers(team_data, top_n=2)
        
        assert len(top) == 2
        assert top[0]['name'] == 'Jane'
        assert top[1]['name'] == 'Alice'
    
    def test_generate_charts(self):
        """Test chart generation for reports."""
        from scripts.weekly_reports import generate_commit_chart, generate_contribution_chart
        
        # Commit chart data
        commit_data = {
            '2024-01-01': 5,
            '2024-01-02': 8,
            '2024-01-03': 3,
            '2024-01-04': 10,
            '2024-01-05': 7
        }
        
        chart = generate_commit_chart(commit_data)
        assert 'labels' in chart
        assert 'datasets' in chart
        assert len(chart['labels']) == 5
        
        # Contribution chart data
        contribution_data = [
            {'name': 'John', 'commits': 20},
            {'name': 'Jane', 'commits': 30},
            {'name': 'Bob', 'commits': 15}
        ]
        
        chart = generate_contribution_chart(contribution_data)
        assert 'labels' in chart
        assert chart['labels'] == ['John', 'Jane', 'Bob']
        assert chart['datasets'][0]['data'] == [20, 30, 15]