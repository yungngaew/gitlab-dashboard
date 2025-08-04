"""Tests for weekly report email template."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.templates.weekly_report_email import WeeklyReportEmailTemplate


class TestWeeklyReportEmailTemplate:
    """Test weekly report email template functionality."""
    
    @pytest.fixture
    def template(self):
        """Create email template instance."""
        return WeeklyReportEmailTemplate()
    
    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data for testing."""
        return {
            'metadata': {
                'generated_at': '2024-01-15T10:00:00',
                'period_start': '2024-01-08T00:00:00',
                'period_end': '2024-01-15T23:59:59',
                'weeks_analyzed': 1,
                'groups_analyzed': 2,
                'team_size': 5
            },
            'executive_summary': {
                'key_metrics': {
                    'total_commits': 45,
                    'total_merge_requests': 12,
                    'merge_rate': 83.3,
                    'active_contributors': 5,
                    'healthy_projects': 8,
                    'projects_needing_attention': 2
                },
                'highlights': [
                    '🎯 Excellent merge request acceptance rate',
                    '💚 More healthy projects than critical ones',
                    '⭐ Top contributor: John Doe with 20 commits'
                ],
                'concerns': [
                    '🚨 2 projects in critical health',
                    '📉 Very low commit activity this week'
                ]
            },
            'team_activity': {
                'commits': {
                    'total': 45,
                    'by_author': {
                        'John Doe': 20,
                        'Jane Smith': 15,
                        'Bob Wilson': 10
                    },
                    'by_day': {
                        '2024-01-08': 5,
                        '2024-01-09': 8,
                        '2024-01-10': 12,
                        '2024-01-11': 7,
                        '2024-01-12': 13
                    }
                },
                'merge_requests': {
                    'total': 12,
                    'opened': 8,
                    'merged': 10,
                    'closed': 2
                },
                'issues': {
                    'total': 15,
                    'opened': 10,
                    'closed': 5,
                    'in_progress': 8
                }
            },
            'project_breakdown': {
                'projects': [
                    {
                        'id': 1,
                        'name': 'critical-project',
                        'path': 'group/critical-project',
                        'health_status': 'critical',
                        'health_score': 35,
                        'metrics': {
                            'commits_this_week': 0,
                            'open_issues': 25,
                            'open_merge_requests': 3
                        },
                        'recommendations': ['No commits this week - check if project is active']
                    },
                    {
                        'id': 2,
                        'name': 'healthy-project',
                        'path': 'group/healthy-project',
                        'health_status': 'healthy',
                        'health_score': 85,
                        'metrics': {
                            'commits_this_week': 15,
                            'open_issues': 3,
                            'open_merge_requests': 1
                        },
                        'recommendations': []
                    }
                ],
                'health_summary': {
                    'healthy': 8,
                    'warning': 1,
                    'critical': 2
                }
            },
            'individual_metrics': {
                'contributors': {
                    'John Doe': {
                        'commits': 20,
                        'productivity_score': 85.5,
                        'collaboration_score': 75.0
                    },
                    'Jane Smith': {
                        'commits': 15,
                        'productivity_score': 72.3,
                        'collaboration_score': 90.0
                    }
                },
                'team_stats': {
                    'total_contributors': 5,
                    'avg_commits': 9.0,
                    'avg_productivity': 78.9,
                    'top_performer': 'John Doe',
                    'most_collaborative': 'Jane Smith'
                }
            },
            'insights_and_actions': {
                'recommended_actions': [
                    {
                        'priority': 'high',
                        'action': 'Address 2 critical health projects',
                        'rationale': 'These projects may be blocking team progress'
                    }
                ],
                'team_focus_areas': ['Code review efficiency', 'Testing automation'],
                'individual_coaching': [
                    {
                        'focus': 'collaboration',
                        'suggestion': 'Encourage more code reviews and cross-project work'
                    }
                ]
            }
        }
    
    def test_init(self, template):
        """Test template initialization."""
        assert isinstance(template.chart_cache, dict)
    
    def test_generate_html_email_structure(self, template, sample_report_data):
        """Test that HTML email generation produces valid structure."""
        html = template.generate_html_email(sample_report_data)
        
        # Check basic HTML structure
        assert html.startswith('<!DOCTYPE html>')
        assert '<html lang="en">' in html
        assert '<head>' in html
        assert '<body>' in html
        assert '</html>' in html
        
        # Check CSS inclusion
        assert '<style>' in html
        assert 'email-container' in html
        assert 'section-title' in html
        
        # Check main sections
        assert 'Weekly Productivity Report' in html
        assert 'Executive Summary' in html
        assert 'Team Activity' in html
        assert 'Project Health' in html
        assert 'Team Performance' in html
        assert 'Insights & Next Steps' in html
    
    def test_generate_html_email_with_team_name(self, template, sample_report_data):
        """Test HTML generation with custom team name."""
        team_name = "AI Development Team"
        html = template.generate_html_email(sample_report_data, team_name=team_name)
        
        assert team_name in html
    
    def test_generate_html_email_without_charts(self, template, sample_report_data):
        """Test HTML generation without charts."""
        html = template.generate_html_email(
            sample_report_data, 
            include_charts=False
        )
        
        # Should not contain chart sections
        assert 'chart-container' not in html
        assert 'chart-image' not in html
    
    def test_header_generation(self, template):
        """Test header section generation."""
        metadata = {
            'period_start': '2024-01-08T00:00:00',
            'period_end': '2024-01-15T23:59:59',
            'generated_at': '2024-01-16T10:00:00'
        }
        
        header = template._generate_header("Test Team", metadata)
        
        assert 'Weekly Productivity Report' in header
        assert 'Test Team' in header
        assert 'January 08 - January 15, 2024' in header
        assert '2024-01-16 10:00' in header
    
    def test_executive_summary_section(self, template, sample_report_data):
        """Test executive summary section generation."""
        summary = sample_report_data['executive_summary']
        section = template._generate_executive_summary_section(summary)
        
        # Check metrics grid
        assert 'metrics-grid' in section
        assert '45' in section  # total commits
        assert '12' in section  # total MRs
        assert '83.3%' in section  # merge rate
        assert '5' in section   # contributors
        
        # Check highlights and concerns
        assert 'Excellent merge request acceptance rate' in section
        assert '2 projects in critical health' in section
    
    def test_team_activity_section(self, template, sample_report_data):
        """Test team activity section generation."""
        activity = sample_report_data['team_activity']
        section = template._generate_team_activity_section(activity)
        
        # Check activity metrics
        assert '45' in section  # commits
        assert '8' in section   # MRs opened
        assert '10' in section  # MRs merged
        assert '10' in section  # issues created
        assert '5' in section   # issues resolved
        
        # Check top contributors
        assert 'John Doe' in section
        assert '20 commits' in section
    
    def test_project_health_section(self, template, sample_report_data):
        """Test project health section generation."""
        breakdown = sample_report_data['project_breakdown']
        section = template._generate_project_health_section(breakdown)
        
        # Check health summary
        assert '8' in section  # healthy projects
        assert '1' in section  # warning projects
        assert '2' in section  # critical projects
        
        # Check project cards
        assert 'critical-project' in section
        assert 'healthy-project' in section
        assert 'Needs Attention' in section
        assert 'Performing Well' in section
    
    def test_individual_highlights_section(self, template, sample_report_data):
        """Test individual highlights section generation."""
        metrics = sample_report_data['individual_metrics']
        section = template._generate_individual_highlights_section(metrics)
        
        # Check team stats
        assert '5' in section    # total contributors
        assert '9.0' in section  # avg commits
        assert '78.9' in section # avg productivity
        
        # Check highlights
        assert 'John Doe' in section      # most active
        assert 'Jane Smith' in section    # best collaborator
    
    def test_insights_section(self, template, sample_report_data):
        """Test insights section generation."""
        insights = sample_report_data['insights_and_actions']
        section = template._generate_insights_section(insights)
        
        # Check recommended actions
        assert 'Address 2 critical health projects' in section
        assert 'priority-high' in section
        
        # Check focus areas
        assert 'Code review efficiency' in section
        assert 'Testing automation' in section
    
    def test_format_top_contributors(self, template):
        """Test top contributors formatting."""
        by_author = {
            'John Doe': 20,
            'Jane Smith': 15,
            'Bob Wilson': 10,
            'Alice Brown': 5,
            'Charlie Davis': 3,
            'Eve Miller': 1
        }
        
        result = template._format_top_contributors(by_author)
        
        # Should show top 5 contributors
        assert 'John Doe' in result
        assert '20 commits' in result
        assert 'Jane Smith' in result
        assert 'Charlie Davis' in result
        assert 'Eve Miller' not in result  # Should be excluded (6th place)
    
    def test_format_top_contributors_empty(self, template):
        """Test top contributors formatting with empty data."""
        result = template._format_top_contributors({})
        assert 'No activity this week' in result
    
    def test_format_project_card(self, template):
        """Test project card formatting."""
        project = {
            'name': 'test-project',
            'health_status': 'warning',
            'health_score': 65,
            'metrics': {
                'commits_this_week': 5,
                'open_issues': 12
            }
        }
        
        card = template._format_project_card(project)
        
        assert 'test-project' in card
        assert 'Warning' in card
        assert '65' in card
        assert '5 commits' in card
        assert '12 open issues' in card
        assert 'health-warning' in card
    
    @patch('src.templates.weekly_report_email.plt')
    def test_create_commits_chart_with_matplotlib(self, mock_plt, template):
        """Test chart creation with matplotlib available."""
        commits_by_day = {
            '2024-01-08': 5,
            '2024-01-09': 8,
            '2024-01-10': 12
        }
        
        # Mock matplotlib components
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig = Mock()
        mock_plt.close = Mock()
        
        with patch('src.templates.weekly_report_email.BytesIO') as mock_bytesio, \
             patch('src.templates.weekly_report_email.base64.b64encode') as mock_b64:
            
            mock_buffer = Mock()
            mock_bytesio.return_value = mock_buffer
            mock_b64.return_value.decode.return_value = 'fake_base64_data'
            
            result = template._create_commits_chart(commits_by_day)
            
            # Should create chart elements
            mock_plt.subplots.assert_called_once()
            mock_ax.plot.assert_called_once()
            mock_ax.fill_between.assert_called_once()
            
            # Should return HTML with embedded image
            assert 'chart-image' in result
            assert 'data:image/png;base64,fake_base64_data' in result
    
    def test_create_commits_chart_no_data(self, template):
        """Test chart creation with no data."""
        result = template._create_commits_chart({})
        assert result == ""
    
    def test_generate_text_charts_section(self, template, sample_report_data):
        """Test text-based charts fallback."""
        result = template._generate_text_charts_section(sample_report_data)
        
        # Should contain ASCII-style chart
        assert 'Activity Trends' in result
        assert 'monospace' in result
        assert '█' in result or '░' in result  # ASCII bar characters
    
    def test_html_sanitization(self, template, sample_report_data):
        """Test that generated HTML is safe."""
        # Add potentially dangerous content
        sample_report_data['team_activity']['commits']['by_author'] = {
            '<script>alert("xss")</script>': 10,
            'Normal User': 5
        }
        
        html = template.generate_html_email(sample_report_data)
        
        # Should not contain executable script tags
        assert '<script>' not in html
        assert 'alert(' not in html
    
    def test_email_styles_completeness(self, template):
        """Test that email styles are comprehensive."""
        styles = template._get_email_styles()
        
        # Check for key style classes
        required_classes = [
            'email-container',
            'header',
            'section',
            'metrics-grid',
            'metric-card',
            'project-card',
            'health-badge',
            'insights-list',
            'footer'
        ]
        
        for css_class in required_classes:
            assert css_class in styles
        
        # Check for responsive design
        assert '@media' in styles
        assert 'max-width: 600px' in styles
    
    def test_footer_generation(self, template):
        """Test footer generation."""
        metadata = {'generated_at': '2024-01-16T10:00:00'}
        footer = template._generate_footer(metadata)
        
        assert 'GitLab Tools' in footer
        assert 'team lead' in footer
        assert 'footer' in footer