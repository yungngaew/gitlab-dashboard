"""GitLab API client with enhanced features."""

import time
import logging
from typing import Dict, List, Any, Optional, Iterator, Union
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .exceptions import (
    GitLabAPIError, 
    AuthenticationError, 
    RateLimitError,
    ResourceNotFoundError,
    PermissionError
)


logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, requests_per_second: float = 3.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_interval:
            sleep_time = self.min_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class GitLabClient:
    """Enhanced GitLab API client with automatic pagination, rate limiting, and retry logic."""
    
    def __init__(
        self, 
        url: str, 
        token: str, 
        config: Optional[Dict[str, Any]] = None,
        verify_ssl: bool = True
    ):
        """Initialize GitLab client.
        
        Args:
            url: GitLab instance URL
            token: Personal access token
            config: Optional configuration dict
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = f"{url.rstrip('/')}/api/v4"
        self.token = token
        self.verify_ssl = verify_ssl
        self.config = config or {}
        
        # Setup rate limiter
        rate_limit = self.config.get('rate_limit', 3)
        self.rate_limiter = RateLimiter(rate_limit)
        
        # Setup session with retry logic
        self.session = self._create_session()
        
        # Test authentication
        self._verify_authentication()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic and connection pooling."""
        session = requests.Session()
        
        # Set headers
        session.headers.update({
            'Private-Token': self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.get('retry_count', 3),
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _verify_authentication(self):
        """Verify that the token is valid."""
        try:
            self._request('GET', 'user')
            logger.info("GitLab authentication successful")
        except GitLabAPIError as e:
            raise AuthenticationError(f"Authentication failed: {e}")
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Union[Dict, List]:
        """Make a request to the GitLab API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response data as dict or list
            
        Raises:
            GitLabAPIError: On API errors
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Build full URL
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        # Set timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.config.get('timeout', 30)
        
        # Make request
        try:
            response = self.session.request(
                method, 
                url, 
                verify=self.verify_ssl,
                **kwargs
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds",
                    retry_after=retry_after
                )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid or expired token")
            
            # Handle permission errors
            if response.status_code == 403:
                raise PermissionError("Insufficient permissions for this operation")
            
            # Handle not found
            if response.status_code == 404:
                raise ResourceNotFoundError(f"Resource not found: {endpoint}")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Return JSON data if available
            if response.text:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            raise GitLabAPIError(f"Request failed: {e}")
    
    def get(self, endpoint: str, **kwargs) -> Union[Dict, List]:
        """Make a GET request to the GitLab API.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response data as dict or list
        """
        return self._request('GET', endpoint, **kwargs)
    
    def _paginated_get(
        self, 
        endpoint: str, 
        per_page: int = 100,
        **params
    ) -> Iterator[Dict]:
        """Get paginated results from GitLab API.
        
        Args:
            endpoint: API endpoint
            per_page: Number of results per page
            **params: Query parameters
            
        Yields:
            Individual items from all pages
        """
        params['per_page'] = per_page
        params['page'] = 1
        
        while True:
            response = self.session.get(
                urljoin(self.base_url + '/', endpoint.lstrip('/')),
                params=params,
                verify=self.verify_ssl,
                timeout=self.config.get('timeout', 30)
            )
            
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            for item in data:
                yield item
            
            # Check if there are more pages
            if 'X-Next-Page' in response.headers and response.headers['X-Next-Page']:
                params['page'] = int(response.headers['X-Next-Page'])
            else:
                break
    
    # Project operations
    def get_project(self, project_id: Union[int, str]) -> Dict:
        """Get a single project by ID or path."""
        return self._request('GET', f'projects/{project_id}')
    
    def get_projects(
        self, 
        group_id: Optional[int] = None,
        search: Optional[str] = None,
        archived: Optional[bool] = None,
        **kwargs
    ) -> Iterator[Dict]:
        """Get projects with filters."""
        params = {}
        
        if group_id:
            endpoint = f'groups/{group_id}/projects'
            params['include_subgroups'] = kwargs.get('include_subgroups', True)
        else:
            endpoint = 'projects'
            
        if search:
            params['search'] = search
        if archived is not None:
            params['archived'] = archived
            
        params.update(kwargs)
        
        return self._paginated_get(endpoint, **params)
    
    # Group operations
    def get_group(self, group_id: Union[int, str]) -> Dict:
        """Get a single group by ID or path."""
        return self._request('GET', f'groups/{group_id}')
    
    def get_groups(self, search: Optional[str] = None, **kwargs) -> Iterator[Dict]:
        """Get groups with filters."""
        params = {}
        if search:
            params['search'] = search
        params.update(kwargs)
        
        return self._paginated_get('groups', **params)
    
    def search_group_by_name(self, name: str) -> Optional[Dict]:
        """Search for a group by exact name match."""
        for group in self.get_groups(search=name):
            if group['name'] == name:
                return group
        return None
    
    # Branch operations
    def get_branches(self, project_id: Union[int, str]) -> Iterator[Dict]:
        """Get all branches for a project."""
        return self._paginated_get(f'projects/{project_id}/repository/branches')
    
    def get_branch(self, project_id: Union[int, str], branch: str) -> Dict:
        """Get a single branch."""
        return self._request('GET', f'projects/{project_id}/repository/branches/{branch}')
    
    def branch_exists(self, project_id: Union[int, str], branch: str) -> bool:
        """Check if a branch exists."""
        try:
            self.get_branch(project_id, branch)
            return True
        except ResourceNotFoundError:
            return False
    
    def create_branch(
        self, 
        project_id: Union[int, str], 
        branch: str, 
        ref: str
    ) -> Dict:
        """Create a new branch."""
        return self._request(
            'POST',
            f'projects/{project_id}/repository/branches',
            params={'branch': branch, 'ref': ref}
        )
    
    def delete_branch(self, project_id: Union[int, str], branch: str) -> None:
        """Delete a branch."""
        self._request('DELETE', f'projects/{project_id}/repository/branches/{branch}')
    
    def update_default_branch(
        self, 
        project_id: Union[int, str], 
        branch: str
    ) -> Dict:
        """Update the default branch of a project."""
        return self._request(
            'PUT',
            f'projects/{project_id}',
            json={'default_branch': branch}
        )
    
    # Board operations
    def get_boards(self, project_id: Union[int, str]) -> Iterator[Dict]:
        """Get all boards for a project."""
        return self._paginated_get(f'projects/{project_id}/boards')
    
    def get_board(self, project_id: Union[int, str], board_id: int) -> Dict:
        """Get a single board by ID."""
        return self._request('GET', f'projects/{project_id}/boards/{board_id}')
    
    def get_board_lists(self, project_id: Union[int, str], board_id: int) -> Iterator[Dict]:
        """Get all lists (columns) for a board."""
        return self._paginated_get(f'projects/{project_id}/boards/{board_id}/lists')
    
    def rename_branch(
        self, 
        project_id: Union[int, str], 
        old_branch: str, 
        new_branch: str,
        update_default: bool = True
    ) -> bool:
        """Rename a branch (create new, update default if needed, delete old).
        
        Args:
            project_id: Project ID or path
            old_branch: Current branch name
            new_branch: New branch name
            update_default: Whether to update default branch if renaming default
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get project info to check default branch
            project = self.get_project(project_id)
            is_default = project.get('default_branch') == old_branch
            
            # Check if old branch exists
            if not self.branch_exists(project_id, old_branch):
                logger.warning(f"Branch '{old_branch}' not found in project {project_id}")
                return False
            
            # Check if new branch already exists
            if self.branch_exists(project_id, new_branch):
                logger.warning(f"Branch '{new_branch}' already exists in project {project_id}")
                return False
            
            # Create new branch from old
            self.create_branch(project_id, new_branch, old_branch)
            logger.info(f"Created branch '{new_branch}' from '{old_branch}'")
            
            # Update default branch if necessary
            if is_default and update_default:
                self.update_default_branch(project_id, new_branch)
                logger.info(f"Updated default branch to '{new_branch}'")
            
            # Delete old branch
            self.delete_branch(project_id, old_branch)
            logger.info(f"Deleted old branch '{old_branch}'")
            
            return True
            
        except GitLabAPIError as e:
            logger.error(f"Failed to rename branch: {e}")
            return False
    
    # Issue operations
    def create_issue(
        self,
        project_id: Union[int, str],
        title: str,
        description: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee_id: Optional[int] = None,
        milestone_id: Optional[int] = None,
        due_date: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """Create a new issue in a project.
        
        Args:
            project_id: Project ID or path
            title: Issue title
            description: Issue description
            labels: List of label names
            assignee_id: ID of user to assign
            milestone_id: ID of milestone
            due_date: Due date in YYYY-MM-DD format
            **kwargs: Additional issue fields
            
        Returns:
            Created issue data
        """
        data = {'title': title}
        
        if description:
            data['description'] = description
        if labels:
            data['labels'] = ','.join(labels)
        if assignee_id:
            data['assignee_id'] = assignee_id
        if milestone_id:
            data['milestone_id'] = milestone_id
        if due_date:
            data['due_date'] = due_date
            
        data.update(kwargs)
        
        return self._request('POST', f'projects/{project_id}/issues', json=data)
    
    def get_issues(
        self,
        project_id: Optional[Union[int, str]] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> Iterator[Dict]:
        """Get issues with filters.
        
        Args:
            project_id: Optional project ID to filter by
            state: Issue state (opened, closed, all)
            labels: List of labels to filter by
            **kwargs: Additional filters
            
        Yields:
            Issue dictionaries
        """
        if project_id:
            endpoint = f'projects/{project_id}/issues'
        else:
            endpoint = 'issues'
            
        params = {}
        if state:
            params['state'] = state
        if labels:
            params['labels'] = ','.join(labels)
        params.update(kwargs)
        
        return self._paginated_get(endpoint, **params)
    
    # Board operations
    def get_boards(self, project_id: Union[int, str]) -> Iterator[Dict]:
        """Get project boards.
        
        Args:
            project_id: Project ID
            
        Yields:
            Board dictionaries
        """
        return self._paginated_get(f'projects/{project_id}/boards')
    
    def get_board_lists(self, project_id: Union[int, str], board_id: int) -> Iterator[Dict]:
        """Get board lists (columns).
        
        Args:
            project_id: Project ID
            board_id: Board ID
            
        Yields:
            Board list dictionaries with label information
        """
        return self._paginated_get(f'projects/{project_id}/boards/{board_id}/lists')
    
    def get_board_issues(
        self, 
        project_id: Union[int, str], 
        board_id: int, 
        list_id: Optional[int] = None,
        **kwargs
    ) -> Iterator[Dict]:
        """Get issues from a board or specific board list.
        
        Args:
            project_id: Project ID
            board_id: Board ID
            list_id: Optional list ID to filter by specific column
            **kwargs: Additional filters
            
        Yields:
            Issue dictionaries
        """
        if list_id:
            endpoint = f'projects/{project_id}/boards/{board_id}/lists/{list_id}/issues'
        else:
            endpoint = f'projects/{project_id}/boards/{board_id}/issues'
        
        return self._paginated_get(endpoint, **kwargs)