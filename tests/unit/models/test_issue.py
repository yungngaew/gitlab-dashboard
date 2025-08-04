"""Unit tests for issue models."""

import pytest
from datetime import date
from src.models.issue import Issue, IssueCreate, IssueType, IssueTemplate


class TestIssueModels:
    """Test issue-related models."""
    
    def test_issue_create_basic(self):
        """Test creating a basic issue."""
        issue = IssueCreate(
            title="Test Issue",
            description="Test description",
            labels=["bug", "priority:high"]
        )
        
        assert issue.title == "Test Issue"
        assert issue.description == "Test description"
        assert issue.labels == ["bug", "priority:high"]
        assert issue.issue_type is None
        assert issue.assignee_id is None
        assert issue.milestone_id is None
        assert issue.due_date is None
        assert issue.weight is None
    
    def test_issue_create_full(self):
        """Test creating an issue with all fields."""
        issue = IssueCreate(
            title="Feature Request",
            description="Implement new feature",
            labels=["feature", "enhancement"],
            issue_type=IssueType.ISSUE,
            assignee_id=123,
            milestone_id=456,
            due_date=date(2024, 12, 31),
            weight=5
        )
        
        assert issue.title == "Feature Request"
        assert issue.issue_type == IssueType.ISSUE
        assert issue.assignee_id == 123
        assert issue.milestone_id == 456
        assert issue.due_date == date(2024, 12, 31)
        assert issue.weight == 5
    
    def test_issue_to_dict(self):
        """Test converting issue to dictionary for API."""
        issue = IssueCreate(
            title="Test Issue",
            description="Description",
            labels=["bug"],
            due_date=date(2024, 6, 15),
            weight=3
        )
        
        result = issue.to_dict()
        
        assert result['title'] == "Test Issue"
        assert result['description'] == "Description"
        assert result['labels'] == "bug"  # Should be comma-separated string
        assert result['due_date'] == "2024-06-15"
        assert result['weight'] == 3
        assert 'assignee_id' not in result  # None values should be excluded
    
    def test_issue_type_enum(self):
        """Test IssueType enum values."""
        assert IssueType.ISSUE.value == "issue"
        assert IssueType.INCIDENT.value == "incident"
        assert IssueType.TEST_CASE.value == "test_case"
        assert IssueType.REQUIREMENT.value == "requirement"
    
    def test_issue_template_basic(self):
        """Test creating a basic issue template."""
        template = IssueTemplate(
            name="bug",
            title_template="Bug: {bug_name}",
            description_template="Bug found in {component}:\n{description}",
            required_variables=["bug_name", "component", "description"]
        )
        
        assert template.name == "bug"
        assert template.title_template == "Bug: {bug_name}"
        assert template.required_variables == ["bug_name", "component", "description"]
        assert template.optional_variables == []
        assert template.default_labels == []
    
    def test_issue_template_full(self):
        """Test creating a full issue template."""
        template = IssueTemplate(
            name="feature",
            title_template="Feature: {feature_name}",
            description_template="{description}",
            required_variables=["feature_name", "description"],
            optional_variables=["acceptance_criteria", "technical_notes"],
            default_labels=["feature", "needs-review"],
            default_weight=5,
            default_issue_type=IssueType.ISSUE
        )
        
        assert template.name == "feature"
        assert template.optional_variables == ["acceptance_criteria", "technical_notes"]
        assert template.default_labels == ["feature", "needs-review"]
        assert template.default_weight == 5
        assert template.default_issue_type == IssueType.ISSUE
    
    def test_issue_template_create_issue(self):
        """Test creating an issue from a template."""
        template = IssueTemplate(
            name="bug",
            title_template="Bug: {bug_name}",
            description_template="Component: {component}\n\nDescription:\n{description}",
            required_variables=["bug_name", "component", "description"],
            default_labels=["bug"],
            default_weight=3
        )
        
        issue = template.create_issue(
            bug_name="Login failure",
            component="Authentication",
            description="Users cannot login with valid credentials"
        )
        
        assert issue.title == "Bug: Login failure"
        assert "Component: Authentication" in issue.description
        assert "Users cannot login with valid credentials" in issue.description
        assert issue.labels == ["bug"]
        assert issue.weight == 3
    
    def test_issue_template_missing_required_variable(self):
        """Test template with missing required variable."""
        template = IssueTemplate(
            name="test",
            title_template="{title}",
            description_template="{description}",
            required_variables=["title", "description"]
        )
        
        with pytest.raises(ValueError) as exc_info:
            template.create_issue(title="Only title")
        
        assert "Missing required variable" in str(exc_info.value)
    
    def test_issue_template_with_optional_variables(self):
        """Test template with optional variables."""
        template = IssueTemplate(
            name="story",
            title_template="Story: {title}",
            description_template="{description}\n\nNotes: {notes}",
            required_variables=["title", "description"],
            optional_variables=["notes"]
        )
        
        # Without optional variable
        issue1 = template.create_issue(
            title="User login",
            description="As a user, I want to login"
        )
        assert "Notes: " in issue1.description
        
        # With optional variable
        issue2 = template.create_issue(
            title="User login",
            description="As a user, I want to login",
            notes="Consider OAuth integration"
        )
        assert "Notes: Consider OAuth integration" in issue2.description
    
    def test_issue_model_from_api_response(self):
        """Test creating Issue model from API response."""
        api_data = {
            'id': 123,
            'iid': 45,
            'title': 'Test Issue',
            'description': 'Test description',
            'state': 'opened',
            'labels': ['bug', 'priority:high'],
            'web_url': 'https://gitlab.com/project/issues/45',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-02T00:00:00Z'
        }
        
        issue = Issue(**api_data)
        
        assert issue.id == 123
        assert issue.iid == 45
        assert issue.title == 'Test Issue'
        assert issue.state == 'opened'
        assert issue.labels == ['bug', 'priority:high']
        assert issue.web_url == 'https://gitlab.com/project/issues/45'