"""Tests for sync_issues script."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json
import subprocess

# Mock the script module for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.sync_issues import IssueFile, get_issue_files, generate_curl_command, create_issue_with_curl, sync_issues


class TestIssueFile:
    """Test IssueFile class."""
    
    def test_parse_yaml_frontmatter(self, tmp_path):
        """Test parsing markdown with YAML frontmatter."""
        content = """---
title: Test Issue
labels: [bug, urgent]
assignee: john.doe
milestone: v1.0
due_date: 2024-12-31
weight: 5
priority: high
---

# Description

This is a test issue with YAML frontmatter.

#additional #labels
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        
        issue = IssueFile(test_file)
        
        assert issue.title == "Test Issue"
        assert "bug" in issue.labels
        assert "urgent" in issue.labels
        assert "additional" in issue.labels
        assert "labels" in issue.labels
        assert issue.assignee == "john.doe"
        assert issue.milestone == "v1.0"
        assert issue.due_date == "2024-12-31"
        assert issue.weight == 5
        assert issue.priority == "high"
        assert "This is a test issue" in issue.description
    
    def test_parse_simple_markdown(self, tmp_path):
        """Test parsing simple markdown without frontmatter."""
        content = """# Bug Fix

This is a simple bug fix issue.

#bug #critical #production
"""
        test_file = tmp_path / "bug-fix.md"
        test_file.write_text(content)
        
        issue = IssueFile(test_file)
        
        assert issue.title == "Bug Fix"
        assert "bug" in issue.labels
        assert "critical" in issue.labels
        assert "production" in issue.labels
        assert "This is a simple bug fix issue" in issue.description
    
    def test_parse_filename_as_title(self, tmp_path):
        """Test using filename as title when no heading."""
        content = """Just some description without a heading.

#feature #enhancement
"""
        test_file = tmp_path / "new-feature-request.md"
        test_file.write_text(content)
        
        issue = IssueFile(test_file)
        
        assert issue.title == "New Feature Request"
        assert "feature" in issue.labels
        assert "enhancement" in issue.labels
    
    def test_to_dict(self, tmp_path):
        """Test converting IssueFile to dictionary."""
        content = """---
title: Test Issue
labels: [bug, urgent]
assignee: john.doe
---

Description here.
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        
        issue = IssueFile(test_file)
        data = issue.to_dict()
        
        assert data['title'] == "Test Issue"
        assert data['labels'] == "bug,urgent"
        assert data['assignee'] == "john.doe"
        assert "Description here" in data['description']


class TestGetIssueFiles:
    """Test get_issue_files function."""
    
    def test_find_markdown_files(self, tmp_path):
        """Test finding markdown files in directory."""
        # Create test files
        (tmp_path / "issue1.md").write_text("# Issue 1")
        (tmp_path / "issue2.txt").write_text("Issue 2")
        (tmp_path / "issue3.markdown").write_text("# Issue 3")
        (tmp_path / "not-an-issue.py").write_text("print('hello')")
        
        issues = get_issue_files(tmp_path)
        
        assert len(issues) == 3
        filenames = [issue.filename for issue in issues]
        assert "issue1.md" in filenames
        assert "issue2.txt" in filenames
        assert "issue3.markdown" in filenames
        assert "not-an-issue.py" not in filenames
    
    def test_empty_directory(self, tmp_path):
        """Test handling empty directory."""
        issues = get_issue_files(tmp_path)
        assert len(issues) == 0
    
    def test_invalid_files(self, tmp_path, caplog):
        """Test handling files that fail to parse."""
        # Create a file that might cause parsing issues
        (tmp_path / "valid.md").write_text("# Valid Issue")
        
        with patch('scripts.sync_issues.IssueFile.__init__', side_effect=Exception("Parse error")) as mock_init:
            # First call succeeds, second fails
            mock_init.side_effect = [None, Exception("Parse error")]
            
            issues = get_issue_files(tmp_path)
            
            # Should handle the error gracefully
            assert "Failed to parse" in caplog.text


class TestGenerateCurlCommand:
    """Test generate_curl_command function."""
    
    def test_basic_curl_command(self, tmp_path):
        """Test generating basic curl command."""
        content = """---
title: Test Issue
labels: [bug]
---

Description
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        issue = IssueFile(test_file)
        
        cmd = generate_curl_command(
            issue,
            "https://gitlab.example.com",
            "123",
            "secret-token"
        )
        
        assert "curl" in cmd
        assert "--request POST" in cmd
        assert "https://gitlab.example.com/api/v4/projects/123/issues" in cmd
        assert 'PRIVATE-TOKEN: secret-token' in cmd
        assert 'title=Test Issue' in cmd
        assert 'labels=bug' in cmd
    
    def test_escaped_quotes(self, tmp_path):
        """Test escaping quotes in values."""
        content = """---
title: Test "Quoted" Issue
---

Description with "quotes"
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        issue = IssueFile(test_file)
        
        cmd = generate_curl_command(
            issue,
            "https://gitlab.example.com",
            "123",
            "token"
        )
        
        assert 'Test \\"Quoted\\" Issue' in cmd
        assert 'with \\"quotes\\"' in cmd


class TestCreateIssueWithCurl:
    """Test create_issue_with_curl function."""
    
    @patch('subprocess.run')
    def test_successful_creation(self, mock_run, tmp_path):
        """Test successful issue creation."""
        # Mock successful response
        mock_run.return_value = MagicMock(
            stdout='{"iid": 123, "web_url": "https://gitlab.example.com/issues/123"}',
            stderr='',
            returncode=0
        )
        
        content = "---\ntitle: Test\n---\nDescription"
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        issue = IssueFile(test_file)
        
        success, message = create_issue_with_curl(
            issue,
            "https://gitlab.example.com",
            "project-123",
            "token"
        )
        
        assert success is True
        assert "Created issue #123" in message
        assert "https://gitlab.example.com/issues/123" in message
    
    @patch('subprocess.run')
    def test_curl_failure(self, mock_run, tmp_path):
        """Test handling curl failure."""
        # Mock failed response
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'curl', stderr='Connection failed'
        )
        
        content = "---\ntitle: Test\n---\nDescription"
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        issue = IssueFile(test_file)
        
        success, message = create_issue_with_curl(
            issue,
            "https://gitlab.example.com",
            "project-123",
            "token"
        )
        
        assert success is False
        assert "Curl failed" in message
    
    def test_dry_run(self, tmp_path):
        """Test dry run mode."""
        content = "---\ntitle: Test\n---\nDescription"
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        issue = IssueFile(test_file)
        
        success, message = create_issue_with_curl(
            issue,
            "https://gitlab.example.com",
            "project-123",
            "token",
            dry_run=True
        )
        
        assert success is True
        assert "curl" in message


class TestSyncIssues:
    """Test sync_issues function."""
    
    @patch('scripts.sync_issues.create_issue_with_curl')
    @patch('scripts.sync_issues.get_issue_files')
    def test_successful_sync(self, mock_get_files, mock_create, tmp_path):
        """Test successful sync of multiple issues."""
        # Create mock issues
        issue1 = Mock()
        issue1.filename = "issue1.md"
        issue1.title = "Issue 1"
        issue1.labels = ["bug"]
        
        issue2 = Mock()
        issue2.filename = "issue2.md"
        issue2.title = "Issue 2"
        issue2.labels = []
        
        mock_get_files.return_value = [issue1, issue2]
        mock_create.side_effect = [
            (True, "Created issue #1"),
            (True, "Created issue #2")
        ]
        
        results = sync_issues(
            tmp_path,
            "https://gitlab.example.com",
            "123",
            "token"
        )
        
        assert results['total'] == 2
        assert results['success'] == 2
        assert results['failed'] == 0
        assert len(results['errors']) == 0
    
    @patch('scripts.sync_issues.create_issue_with_curl')
    @patch('scripts.sync_issues.get_issue_files')
    def test_partial_failure(self, mock_get_files, mock_create, tmp_path):
        """Test sync with some failures."""
        issue1 = Mock()
        issue1.filename = "issue1.md"
        issue1.title = "Issue 1"
        issue1.labels = []
        
        issue2 = Mock()
        issue2.filename = "issue2.md"
        issue2.title = "Issue 2"
        issue2.labels = []
        
        mock_get_files.return_value = [issue1, issue2]
        mock_create.side_effect = [
            (True, "Created issue #1"),
            (False, "API Error: Invalid token")
        ]
        
        results = sync_issues(
            tmp_path,
            "https://gitlab.example.com",
            "123",
            "token"
        )
        
        assert results['total'] == 2
        assert results['success'] == 1
        assert results['failed'] == 1
        assert len(results['errors']) == 1
        assert "API Error" in results['errors'][0]
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('scripts.sync_issues.get_issue_files')
    def test_generate_script(self, mock_get_files, mock_file, tmp_path):
        """Test generating shell script."""
        issue = Mock()
        issue.filename = "issue.md"
        issue.title = "Test Issue"
        issue.labels = []
        
        mock_get_files.return_value = [issue]
        
        with patch('scripts.sync_issues.generate_curl_command', return_value='curl command'):
            results = sync_issues(
                tmp_path,
                "https://gitlab.example.com",
                "123",
                "token",
                generate_script=True
            )
        
        # Should write script file
        mock_file.assert_called()
        written_content = ''.join(call[0][0] for call in mock_file().write.call_args_list)
        assert "#!/bin/bash" in written_content
        assert "curl command" in written_content


class TestYAMLParsing:
    """Test YAML frontmatter parsing edge cases."""
    
    def test_malformed_yaml(self, tmp_path):
        """Test handling malformed YAML."""
        content = """---
title: Test
labels: [unclosed bracket
---

Description
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        
        # Should handle gracefully
        issue = IssueFile(test_file)
        assert issue.title  # Should still get a title
        assert issue.description
    
    def test_no_frontmatter(self, tmp_path):
        """Test file without frontmatter."""
        content = """# Simple Issue

Just a description.
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)
        
        issue = IssueFile(test_file)
        assert issue.title == "Simple Issue"
        assert "Just a description" in issue.description
    
    def test_empty_file(self, tmp_path):
        """Test empty file handling."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("")
        
        issue = IssueFile(test_file)
        assert issue.title == "Empty"  # From filename
        assert issue.description == ""