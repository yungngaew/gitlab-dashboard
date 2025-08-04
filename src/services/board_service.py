"""GitLab board service for managing issue workflow states through labels."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from ..api.client import GitLabClient
from ..api.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class BoardService:
    """Service for GitLab board operations and label-based workflow management."""
    
    # Common board label patterns for workflow states
    DEFAULT_LABEL_MAPPINGS = {
        'to_do': ['To Do', 'TODO', 'Backlog', 'Open', 'New', 'To-Do', 'Ready'],
        'in_progress': ['In Progress', 'Doing', 'In Development', 'InProgress', 'WIP', 
                        'Work In Progress', 'Active', 'Started'],
        'in_review': ['In Review', 'Code Review', 'Review', 'Testing', 'QA', 
                      'Awaiting Review', 'Under Review'],
        'blocked': ['Blocked', 'On Hold', 'Waiting', 'Pending', 'Stalled'],
        'done': ['Done', 'Closed', 'Complete', 'Completed', 'Finished', 'Resolved']
    }
    
    def __init__(self, client: GitLabClient, config: Optional[Dict[str, Any]] = None):
        """Initialize board service.
        
        Args:
            client: GitLab API client
            config: Optional configuration with custom label mappings
        """
        self.client = client
        self.config = config or {}
        
        # Use custom label mappings from config or defaults
        self.label_mappings = self.config.get('board_label_mappings', self.DEFAULT_LABEL_MAPPINGS)
        
        # Create reverse mapping for quick label-to-state lookup
        self._create_reverse_mapping()
    
    def _create_reverse_mapping(self):
        """Create reverse mapping from label to workflow state."""
        self.label_to_state = {}
        for state, labels in self.label_mappings.items():
            for label in labels:
                # Store both exact and lowercase versions for flexible matching
                self.label_to_state[label] = state
                self.label_to_state[label.lower()] = state
    
    def get_project_boards(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all boards for a project.
        
        Args:
            project_id: Project ID or path
            
        Returns:
            List of board dictionaries
        """
        try:
            boards = list(self.client.get_boards(project_id))
            logger.info(f"Found {len(boards)} boards for project {project_id}")
            return boards
        except Exception as e:
            logger.error(f"Failed to fetch boards for project {project_id}: {e}")
            return []
    
    def get_default_board(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the default or first board for a project.
        
        Args:
            project_id: Project ID or path
            
        Returns:
            Board dictionary or None if no boards exist
        """
        boards = self.get_project_boards(project_id)
        if not boards:
            return None
        
        # Look for a board named "Development" or similar
        for board in boards:
            if board.get('name', '').lower() in ['development', 'default', 'main']:
                return board
        
        # Otherwise return the first board
        return boards[0]
    
    def get_board_workflow_labels(self, project_id: str, board_id: int) -> Dict[str, List[str]]:
        """Get workflow labels from board lists.
        
        Args:
            project_id: Project ID or path
            board_id: Board ID
            
        Returns:
            Dictionary mapping workflow states to label names
        """
        workflow_labels = defaultdict(list)
        
        try:
            lists = list(self.client.get_board_lists(project_id, board_id))
            
            for board_list in lists:
                # Skip special lists (like "Closed" which uses issue state, not labels)
                if board_list.get('list_type') == 'closed':
                    continue
                
                label = board_list.get('label')
                if label:
                    label_name = label.get('name', '')
                    # Determine workflow state from label
                    state = self.determine_workflow_state(label_name)
                    workflow_labels[state].append(label_name)
                    logger.debug(f"Board list '{label_name}' mapped to state '{state}'")
            
            return dict(workflow_labels)
            
        except Exception as e:
            logger.error(f"Failed to fetch board lists: {e}")
            return {}
    
    def determine_workflow_state(self, label: str) -> str:
        """Determine workflow state from a label.
        
        Args:
            label: Label name
            
        Returns:
            Workflow state (to_do, in_progress, in_review, blocked, done, or other)
        """
        if not label:
            return 'other'
        
        # Check exact match first
        if label in self.label_to_state:
            return self.label_to_state[label]
        
        # Check lowercase match
        label_lower = label.lower()
        if label_lower in self.label_to_state:
            return self.label_to_state[label_lower]
        
        # Check partial matches
        for state, patterns in self.label_mappings.items():
            for pattern in patterns:
                if pattern.lower() in label_lower or label_lower in pattern.lower():
                    return state
        
        return 'other'
    
    def categorize_issues_by_workflow(
        self, 
        issues: List[Dict[str, Any]], 
        board_labels: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize issues by their workflow state based on labels.
        
        Args:
            issues: List of issue dictionaries
            board_labels: Optional board-specific label mappings
            
        Returns:
            Dictionary mapping workflow states to lists of issues
        """
        categorized = defaultdict(list)
        
        for issue in issues:
            state = self.get_issue_workflow_state(issue, board_labels)
            categorized[state].append(issue)
        
        return dict(categorized)
    
    def get_issue_workflow_state(
        self, 
        issue: Dict[str, Any], 
        board_labels: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """Determine the workflow state of an issue based on its labels.
        
        Args:
            issue: Issue dictionary
            board_labels: Optional board-specific label mappings
            
        Returns:
            Workflow state string
        """
        # If issue is closed, it's done regardless of labels
        if issue.get('state') == 'closed':
            return 'done'
        
        issue_labels = issue.get('labels', [])
        if not issue_labels:
            return 'to_do'  # Default for unlabeled open issues
        
        # Check if we should allow open issues to be marked as "done" based on labels
        allow_open_as_done = self.config.get('board_service', {}).get('allow_open_issues_as_done', False)
        
        # First check board-specific labels if provided
        if board_labels:
            for state, labels in board_labels.items():
                for label in labels:
                    if label in issue_labels:
                        # Don't categorize open issues as "done" based on labels unless configured
                        if state == 'done' and not allow_open_as_done:
                            continue
                        return state
        
        # Then check against general label mappings
        for label in issue_labels:
            state = self.determine_workflow_state(label)
            # Don't categorize open issues as "done" based on labels unless configured
            if state != 'other' and (state != 'done' or allow_open_as_done):
                return state
        
        # Default to 'to_do' if no workflow labels found
        return 'to_do'
    
    def get_workflow_statistics(
        self, 
        project_id: str, 
        board_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get workflow statistics for a project.
        
        Args:
            project_id: Project ID or path
            board_id: Optional board ID (uses default if not provided)
            
        Returns:
            Dictionary with workflow statistics
        """
        stats = {
            'total_issues': 0,
            'by_state': defaultdict(int),
            'board_info': None,
            'workflow_labels': {}
        }
        
        # Get board info
        if board_id is None:
            board = self.get_default_board(project_id)
            if board:
                board_id = board['id']
                stats['board_info'] = {
                    'id': board['id'],
                    'name': board.get('name', 'Unknown')
                }
        
        # Get board labels if we have a board
        if board_id:
            stats['workflow_labels'] = self.get_board_workflow_labels(project_id, board_id)
        
        # Get all open issues
        try:
            issues = list(self.client.get_issues(project_id=project_id, state='opened'))
            stats['total_issues'] = len(issues)
            
            # Categorize by workflow state
            categorized = self.categorize_issues_by_workflow(issues, stats['workflow_labels'])
            
            for state, issue_list in categorized.items():
                stats['by_state'][state] = len(issue_list)
            
        except Exception as e:
            logger.error(f"Failed to get workflow statistics: {e}")
        
        return dict(stats)
    
    def filter_issues_by_workflow_state(
        self,
        project_id: str,
        states: List[str],
        board_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Filter issues by workflow states.
        
        Args:
            project_id: Project ID or path
            states: List of workflow states to filter by
            board_id: Optional board ID
            
        Returns:
            List of issues matching the specified states
        """
        # Get board labels if board specified
        board_labels = None
        if board_id:
            board_labels = self.get_board_workflow_labels(project_id, board_id)
        
        # Get all open issues
        all_issues = list(self.client.get_issues(project_id=project_id, state='opened'))
        
        # Filter by workflow state
        filtered_issues = []
        for issue in all_issues:
            state = self.get_issue_workflow_state(issue, board_labels)
            if state in states:
                filtered_issues.append(issue)
        
        return filtered_issues