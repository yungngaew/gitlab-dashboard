"""Branch data models."""

from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class BranchOperationType(str, Enum):
    """Types of branch operations."""
    RENAME = "rename"
    CREATE = "create"
    DELETE = "delete"
    PROTECT = "protect"
    UNPROTECT = "unprotect"


@dataclass
class Branch:
    """GitLab branch model."""
    name: str
    commit: Dict[str, Any]
    merged: bool = False
    protected: bool = False
    developers_can_push: bool = False
    developers_can_merge: bool = False
    can_push: bool = True
    default: bool = False
    web_url: Optional[str] = None
    
    @classmethod
    def from_gitlab_response(cls, data: Dict[str, Any]) -> 'Branch':
        """Create Branch instance from GitLab API response."""
        return cls(
            name=data['name'],
            commit=data['commit'],
            merged=data.get('merged', False),
            protected=data.get('protected', False),
            developers_can_push=data.get('developers_can_push', False),
            developers_can_merge=data.get('developers_can_merge', False),
            can_push=data.get('can_push', True),
            default=data.get('default', False),
            web_url=data.get('web_url')
        )
    
    @property
    def last_commit_date(self) -> Optional[datetime]:
        """Get the last commit date."""
        if self.commit and 'committed_date' in self.commit:
            return datetime.fromisoformat(
                self.commit['committed_date'].replace('Z', '+00:00')
            )
        return None
    
    @property
    def last_commit_author(self) -> Optional[str]:
        """Get the last commit author."""
        if self.commit and 'author_name' in self.commit:
            return self.commit['author_name']
        return None


@dataclass
class BranchOperation:
    """Model for tracking branch operations."""
    operation_type: BranchOperationType
    project_id: int
    project_name: str
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    timestamp: datetime = None
    success: bool = False
    error_message: Optional[str] = None
    dry_run: bool = False
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            'operation_type': self.operation_type.value,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'source_branch': self.source_branch,
            'target_branch': self.target_branch,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error_message': self.error_message,
            'dry_run': self.dry_run
        }