"""Custom exceptions for GitLab API operations."""


class GitLabAPIError(Exception):
    """Base exception for GitLab API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationError(GitLabAPIError):
    """Raised when authentication fails."""
    pass


class RateLimitError(GitLabAPIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class ResourceNotFoundError(GitLabAPIError):
    """Raised when a resource is not found."""
    pass


class PermissionError(GitLabAPIError):
    """Raised when user lacks permission for an operation."""
    pass

class ProjectNotFoundError(GitLabAPIError):
    """Raised when a project is not found."""
    pass