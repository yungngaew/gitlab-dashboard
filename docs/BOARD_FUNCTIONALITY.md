# GitLab Board Label Filtering

This document explains the new GitLab board label filtering functionality for tracking issue workflow states.

## Overview

The GitLab board service provides intelligent issue state tracking by analyzing GitLab board labels to determine where issues are in your workflow. This goes beyond simple "open/closed" states to provide detailed workflow visibility.

## Features

### 1. Automatic Board Detection
- Finds your project's default board automatically
- Supports multiple boards per project
- Prefers boards named "Development", "Default", or "Main"

### 2. Workflow State Mapping
Issues are automatically categorized into workflow states based on their labels:

- **To Do**: Backlog items, new issues
- **In Progress**: Active development work
- **In Review**: Code review, testing, QA
- **Blocked**: Waiting for dependencies
- **Done**: Completed work

### 3. Flexible Label Patterns
The system recognizes common board label patterns:

```yaml
to_do:
  - "To Do", "TODO", "Backlog", "Open", "New", "Ready"

in_progress:
  - "In Progress", "Doing", "In Development", "WIP", "Active"

in_review:
  - "In Review", "Code Review", "Testing", "QA", "Under Review"

blocked:
  - "Blocked", "On Hold", "Waiting", "Pending", "Stalled"

done:
  - "Done", "Closed", "Complete", "Finished", "Resolved"
```

## Usage

### Enhanced Issue Listing

Use the new `--use-board-labels` flag to get accurate workflow state tracking:

```bash
# Basic usage with board labels
python scripts/list_project_issues.py project-id --use-board-labels

# Use a specific board
python scripts/list_project_issues.py project-id --use-board-labels --board-id 123

# Include unassigned issues with board state tracking
python scripts/list_project_issues.py project-id --use-board-labels --include-unassigned
```

### Test Board Functionality

Test your board configuration with the dedicated test script:

```bash
# Test basic board functionality
python scripts/test_board_service.py project-id

# Test with a specific board
python scripts/test_board_service.py project-id --board-id 123  

# Show detailed issue breakdown
python scripts/test_board_service.py project-id --show-issues
```

### Executive Dashboard

The executive dashboard now automatically uses board labels for better issue analytics:

```bash
python scripts/generate_executive_dashboard.py
```

## Configuration

### Custom Label Mappings

You can customize label mappings in `config/config.yaml`:

```yaml
board_label_mappings:
  to_do:
    - "Backlog"
    - "Ready for Dev"
    - "Planned"
  
  in_progress:
    - "In Development"
    - "Working"
    - "Sprint Active"
  
  in_review:
    - "Code Review"
    - "Testing"
    - "QA Review"
  
  blocked:
    - "Blocked"
    - "Waiting for Approval"
    - "Dependencies"
  
  done:
    - "Completed"
    - "Deployed"
    - "Closed"
```

### Environment Variables

No additional environment variables are needed. The board service uses your existing GitLab configuration.

## API Methods

### BoardService Class

The main service class provides these methods:

```python
from src.services.board_service import BoardService

# Initialize
board_service = BoardService(gitlab_client, config)

# Get project boards
boards = board_service.get_project_boards(project_id)

# Get default board
default_board = board_service.get_default_board(project_id)

# Get workflow labels from board
workflow_labels = board_service.get_board_workflow_labels(project_id, board_id)

# Determine issue workflow state
state = board_service.get_issue_workflow_state(issue_dict)

# Get workflow statistics
stats = board_service.get_workflow_statistics(project_id)

# Filter issues by workflow state
issues = board_service.filter_issues_by_workflow_state(
    project_id, 
    states=['in_progress', 'in_review']
)
```

### GitLab API Extensions

New methods added to the GitLab client:

```python
# Get all boards for a project
boards = client.get_boards(project_id)

# Get specific board
board = client.get_board(project_id, board_id)

# Get board lists (columns)
lists = client.get_board_lists(project_id, board_id)
```

## How It Works

### 1. Board Discovery
1. Query GitLab API for project boards
2. Select default board or use specified board ID
3. Fetch board lists (columns) and their associated labels

### 2. Label Analysis
1. Map board labels to workflow states using configurable patterns
2. Support both exact and partial label matching
3. Case-insensitive matching for flexibility

### 3. Issue Categorization
1. Analyze each issue's labels
2. Determine workflow state based on label mappings
3. Closed issues are always considered "done"
4. Unlabeled issues default to "to_do"

### 4. State Priority
When multiple workflow labels are present:
1. Board-specific labels take precedence
2. More specific states (like "blocked") override general ones
3. First matching state wins for ties

## Migration Guide

### From Legacy Assignee-Based Tracking

Old behavior:
- Issues with assignees = "In Progress"
- Issues without assignees = "Open"

New behavior:
- Issues categorized by actual board labels
- More accurate workflow state representation
- Backward compatibility with `--use-board-labels` flag

### Updating Scripts

Add the `--use-board-labels` flag to existing scripts:

```bash
# Before
python scripts/list_project_issues.py my-project

# After
python scripts/list_project_issues.py my-project --use-board-labels
```

## Troubleshooting

### No Boards Found
- Ensure your project has at least one board
- Check that your GitLab token has sufficient permissions
- Verify the project ID is correct

### Incorrect State Detection
- Review your board label configuration
- Check that labels match exactly (case-insensitive)
- Consider adding custom label mappings in config

### Performance Issues
- Board information is cached per project
- Use specific board IDs when possible
- Consider rate limiting for large projects

## Examples

### Example Output

```
📋 Testing Board Service for Project: my-project
============================================================

1. Available Boards:
   - ID: 123, Name: Development
   - ID: 124, Name: Sprint Planning

2. Using Default Board: Development (ID: 123)

3. Board Workflow Labels:
   To Do: Backlog, Ready
   In Progress: Doing, In Development
   In Review: Code Review, Testing
   Blocked: Blocked, On Hold

4. Workflow Statistics:
   Total Open Issues: 45
   By Workflow State:
     To Do: 12
     In Progress: 18
     In Review: 8
     Blocked: 3
     Other: 4
```

### Example Markdown Report

```markdown
# Issue Assignment Report

**Project**: my-project
**Generated**: 2025-07-01 10:30:00
**Board**: Development (ID: 123)

## Summary

- **Total Open Issues**: 45

### Workflow State Breakdown:
- **To Do**: 12
- **In Progress**: 18
- **In Review**: 8
- **Blocked**: 3

## Issue Assignments by Member

| ID | Assignee | To Do | In Progress | In Review | Blocked | Total |
|:---|:---------|------:|------------:|----------:|--------:|------:|
| 101 | Alice Johnson | 2 | 8 | 3 | 1 | 14 |
| 102 | Bob Smith | 4 | 6 | 2 | 0 | 12 |
| 103 | Carol Davis | 3 | 4 | 3 | 2 | 12 |
| 0 | Unassigned | 3 | 0 | 0 | 0 | 3 |

---
*Note: Issue states are determined by GitLab board labels.*
```

## Benefits

1. **Accurate Workflow Tracking**: Real workflow states instead of simple assignee presence
2. **Better Project Visibility**: Clear view of where work is in the pipeline
3. **Improved Analytics**: More meaningful metrics and reports
4. **Team Accountability**: Better understanding of individual and team workload
5. **Process Optimization**: Identify bottlenecks and workflow issues

## Future Enhancements

- [ ] Support for custom workflow states
- [ ] Integration with GitLab milestones
- [ ] Workflow transition tracking
- [ ] Automated state updates based on merge requests
- [ ] Advanced analytics and reporting dashboards