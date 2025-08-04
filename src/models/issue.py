"""Issue data models."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field


class IssueType(str, Enum):
    """Issue type enumeration."""
    FEATURE = "feature"
    BUG = "bug"
    TASK = "task"
    ENHANCEMENT = "enhancement"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    EPIC = "epic"


class IssuePriority(str, Enum):
    """Issue priority enumeration."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class Issue:
    """GitLab issue model."""
    id: int
    iid: int  # Internal ID within project
    project_id: int
    title: str
    description: Optional[str] = None
    state: str = "opened"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    milestone: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    assignees: List[Dict[str, Any]] = field(default_factory=list)
    author: Optional[Dict[str, Any]] = None
    due_date: Optional[date] = None
    web_url: Optional[str] = None
    time_stats: Optional[Dict[str, Any]] = None
    weight: Optional[int] = None
    issue_type: Optional[str] = None
    
    @classmethod
    def from_gitlab_response(cls, data: Dict[str, Any]) -> 'Issue':
        """Create Issue instance from GitLab API response."""
        return cls(
            id=data['id'],
            iid=data['iid'],
            project_id=data['project_id'],
            title=data['title'],
            description=data.get('description'),
            state=data.get('state', 'opened'),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
            closed_at=datetime.fromisoformat(data['closed_at'].replace('Z', '+00:00')) if data.get('closed_at') else None,
            labels=data.get('labels', []),
            milestone=data.get('milestone'),
            assignee=data.get('assignee'),
            assignees=data.get('assignees', []),
            author=data.get('author'),
            due_date=date.fromisoformat(data['due_date']) if data.get('due_date') else None,
            web_url=data.get('web_url'),
            time_stats=data.get('time_stats'),
            weight=data.get('weight'),
            issue_type=data.get('issue_type')
        )


@dataclass
class IssueCreate:
    """Model for creating a new issue."""
    title: str
    description: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    milestone_id: Optional[int] = None
    assignee_ids: List[int] = field(default_factory=list)
    due_date: Optional[Union[date, str]] = None
    issue_type: Optional[IssueType] = None
    weight: Optional[int] = None
    confidential: bool = False
    
    # Template-specific fields
    template_variables: Dict[str, Any] = field(default_factory=dict)
    parent_issue_id: Optional[int] = None  # For sub-tasks
    related_issue_ids: List[int] = field(default_factory=list)
    
    def to_gitlab_params(self) -> Dict[str, Any]:
        """Convert to GitLab API parameters."""
        params = {
            'title': self.title,
        }
        
        if self.description:
            params['description'] = self.description
        
        if self.labels:
            params['labels'] = ','.join(self.labels)
        
        if self.milestone_id:
            params['milestone_id'] = self.milestone_id
        
        if self.assignee_ids:
            params['assignee_ids'] = self.assignee_ids
        
        if self.due_date:
            if isinstance(self.due_date, date):
                params['due_date'] = self.due_date.isoformat()
            else:
                params['due_date'] = self.due_date
        
        if self.issue_type:
            params['issue_type'] = self.issue_type.value
        
        if self.weight is not None:
            params['weight'] = self.weight
        
        if self.confidential:
            params['confidential'] = self.confidential
        
        return params
    
    def apply_template(self, template: 'IssueTemplate'):
        """Apply a template to this issue."""
        if template.title_template and not self.title:
            self.title = template.render_title(self.template_variables)
        
        if template.description_template:
            self.description = template.render_description(self.template_variables)
        
        if template.default_labels:
            self.labels.extend(template.default_labels)
            self.labels = list(set(self.labels))  # Remove duplicates
        
        if template.default_issue_type and not self.issue_type:
            self.issue_type = template.default_issue_type


@dataclass
class IssueTemplate:
    """Template for creating issues."""
    name: str
    title_template: str
    description_template: str
    default_labels: List[str] = field(default_factory=list)
    default_issue_type: Optional[IssueType] = None
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    
    def render_title(self, variables: Dict[str, Any]) -> str:
        """Render title with variables."""
        self._validate_variables(variables)
        return self.title_template.format(**variables)
    
    def render_description(self, variables: Dict[str, Any]) -> str:
        """Render description with variables."""
        self._validate_variables(variables)
        return self.description_template.format(**variables)
    
    def _validate_variables(self, variables: Dict[str, Any]):
        """Validate that all required variables are provided."""
        missing = set(self.required_variables) - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required template variables: {', '.join(missing)}")
    
    @classmethod
    def from_file(cls, file_path: str) -> 'IssueTemplate':
        """Load template from a file."""
        import yaml
        
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data['name'],
            title_template=data['title_template'],
            description_template=data['description_template'],
            default_labels=data.get('default_labels', []),
            default_issue_type=IssueType(data['default_issue_type']) if data.get('default_issue_type') else None,
            required_variables=data.get('required_variables', []),
            optional_variables=data.get('optional_variables', [])
        )