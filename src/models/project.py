"""Project data models."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Project:
    """GitLab project model."""
    id: int
    name: str
    name_with_namespace: str
    path: str
    path_with_namespace: str
    description: Optional[str] = None
    default_branch: Optional[str] = None
    visibility: str = "private"
    ssh_url_to_repo: Optional[str] = None
    http_url_to_repo: Optional[str] = None
    web_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    archived: bool = False
    topics: List[str] = field(default_factory=list)
    issues_enabled: bool = True
    merge_requests_enabled: bool = True
    wiki_enabled: bool = True
    snippets_enabled: bool = True
    statistics: Optional[Dict[str, Any]] = None
    namespace: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_gitlab_response(cls, data: Dict[str, Any]) -> 'Project':
        """Create Project instance from GitLab API response."""
        return cls(
            id=data['id'],
            name=data['name'],
            name_with_namespace=data['name_with_namespace'],
            path=data['path'],
            path_with_namespace=data['path_with_namespace'],
            description=data.get('description'),
            default_branch=data.get('default_branch'),
            visibility=data.get('visibility', 'private'),
            ssh_url_to_repo=data.get('ssh_url_to_repo'),
            http_url_to_repo=data.get('http_url_to_repo'),
            web_url=data.get('web_url'),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            last_activity_at=datetime.fromisoformat(data['last_activity_at'].replace('Z', '+00:00')) if data.get('last_activity_at') else None,
            archived=data.get('archived', False),
            topics=data.get('topics', []),
            issues_enabled=data.get('issues_enabled', True),
            merge_requests_enabled=data.get('merge_requests_enabled', True),
            wiki_enabled=data.get('wiki_enabled', True),
            snippets_enabled=data.get('snippets_enabled', True),
            statistics=data.get('statistics'),
            namespace=data.get('namespace')
        )
    
    @property
    def is_active(self) -> bool:
        """Check if project is active (not archived)."""
        return not self.archived
    
    @property
    def group_name(self) -> Optional[str]:
        """Get the group name if project is in a group."""
        if self.namespace and self.namespace.get('kind') == 'group':
            return self.namespace.get('name')
        return None
    
    @property
    def group_id(self) -> Optional[int]:
        """Get the group ID if project is in a group."""
        if self.namespace and self.namespace.get('kind') == 'group':
            return self.namespace.get('id')
        return None


@dataclass
class ProjectCreate:
    """Model for creating a new project."""
    name: str
    path: Optional[str] = None
    namespace_id: Optional[int] = None
    description: Optional[str] = None
    visibility: str = "private"
    initialize_with_readme: bool = True
    default_branch: str = "main"
    topics: List[str] = field(default_factory=list)
    
    def to_gitlab_params(self) -> Dict[str, Any]:
        """Convert to GitLab API parameters."""
        params = {
            'name': self.name,
            'visibility': self.visibility,
            'initialize_with_readme': self.initialize_with_readme,
            'default_branch': self.default_branch
        }
        
        if self.path:
            params['path'] = self.path
        else:
            # Generate path from name
            params['path'] = self.name.lower().replace(' ', '-')
        
        if self.namespace_id:
            params['namespace_id'] = self.namespace_id
        
        if self.description:
            params['description'] = self.description
        
        if self.topics:
            params['topics'] = self.topics
        
        return params