# Issues Directory

This directory contains markdown and text files that represent GitLab issues. Each file will be synced to GitLab as a separate issue.

## File Format

### Option 1: Markdown with YAML Frontmatter

```markdown
---
title: Issue Title
labels: [label1, label2, label3]
assignee: username
milestone: v1.0
due_date: 2024-12-31
weight: 5
priority: high
---

# Issue Description

Detailed description of the issue...
```

### Option 2: Simple Markdown

```markdown
# Issue Title

Issue description...

#label1 #label2 #label3
```

### Option 3: Plain Text

```
Issue Title

Issue description...

Labels: label1, label2, label3
```

## Syncing Issues

To sync all issues to GitLab:

```bash
# Using curl (default)
python scripts/sync_issues.py PROJECT_ID

# Using GitLab API
python scripts/sync_issues.py PROJECT_ID --use-api

# Preview without creating
python scripts/sync_issues.py PROJECT_ID --dry-run

# Generate shell script
python scripts/sync_issues.py PROJECT_ID --generate-script
```

## Metadata Fields

- **title**: Issue title (required)
- **labels**: Comma-separated list or array of labels
- **assignee**: GitLab username to assign
- **milestone**: Milestone title
- **due_date**: Due date in YYYY-MM-DD format
- **weight**: Issue weight (0-200)
- **priority**: Priority level (low, medium, high, critical)

## Tips

1. Use descriptive filenames (they become the default title)
2. Hashtags in the content are automatically extracted as labels
3. YAML frontmatter provides the most control
4. Files are processed alphabetically