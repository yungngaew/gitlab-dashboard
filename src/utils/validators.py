"""Input validation utilities."""

import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from pathlib import Path


class ValidationError(ValueError):
    """Custom validation error."""
    pass


class IssueValidator:
    """Validator for issue data."""
    
    # GitLab limits
    MAX_TITLE_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 1_000_000  # 1MB
    MAX_LABELS = 50
    MAX_LABEL_LENGTH = 255
    
    # Patterns
    LABEL_PATTERN = re.compile(r'^[a-zA-Z0-9\-_. ]+$')
    DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    @classmethod
    def validate_title(cls, title: str) -> str:
        """Validate issue title."""
        if not title or not title.strip():
            raise ValidationError("Issue title cannot be empty")
        
        title = title.strip()
        
        if len(title) > cls.MAX_TITLE_LENGTH:
            raise ValidationError(
                f"Issue title too long ({len(title)} chars). "
                f"Maximum: {cls.MAX_TITLE_LENGTH} chars"
            )
        
        return title
    
    @classmethod
    def validate_description(cls, description: Optional[str]) -> Optional[str]:
        """Validate issue description."""
        if not description:
            return None
        
        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"Issue description too long ({len(description)} chars). "
                f"Maximum: {cls.MAX_DESCRIPTION_LENGTH} chars"
            )
        
        return description
    
    @classmethod
    def validate_labels(cls, labels: List[str]) -> List[str]:
        """Validate issue labels."""
        if not labels:
            return []
        
        if len(labels) > cls.MAX_LABELS:
            raise ValidationError(
                f"Too many labels ({len(labels)}). "
                f"Maximum: {cls.MAX_LABELS}"
            )
        
        validated_labels = []
        for label in labels:
            label = label.strip()
            
            if not label:
                continue
            
            if len(label) > cls.MAX_LABEL_LENGTH:
                raise ValidationError(
                    f"Label '{label}' too long ({len(label)} chars). "
                    f"Maximum: {cls.MAX_LABEL_LENGTH} chars"
                )
            
            if not cls.LABEL_PATTERN.match(label):
                raise ValidationError(
                    f"Invalid label '{label}'. "
                    "Labels can only contain letters, numbers, hyphens, underscores, dots, and spaces"
                )
            
            validated_labels.append(label)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_labels = []
        for label in validated_labels:
            if label.lower() not in seen:
                seen.add(label.lower())
                unique_labels.append(label)
        
        return unique_labels
    
    @classmethod
    def validate_due_date(cls, due_date: Union[str, date, None]) -> Optional[str]:
        """Validate and format due date."""
        if not due_date:
            return None
        
        if isinstance(due_date, date):
            return due_date.isoformat()
        
        if isinstance(due_date, str):
            if not cls.DATE_PATTERN.match(due_date):
                raise ValidationError(
                    f"Invalid date format '{due_date}'. "
                    "Expected format: YYYY-MM-DD"
                )
            
            # Validate it's a real date
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                raise ValidationError(f"Invalid date: {due_date}")
            
            return due_date
        
        raise ValidationError(
            f"Invalid due date type: {type(due_date)}. "
            "Expected string (YYYY-MM-DD) or date object"
        )
    
    @classmethod
    def validate_weight(cls, weight: Optional[int]) -> Optional[int]:
        """Validate issue weight."""
        if weight is None:
            return None
        
        if not isinstance(weight, int):
            raise ValidationError(f"Weight must be an integer, got {type(weight)}")
        
        if weight < 0:
            raise ValidationError("Weight cannot be negative")
        
        if weight > 200:  # GitLab's max weight
            raise ValidationError(f"Weight {weight} too high. Maximum: 200")
        
        return weight
    
    @classmethod
    def validate_issue_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete issue data."""
        validated = {}
        
        # Required fields
        validated['title'] = cls.validate_title(data.get('title', ''))
        
        # Optional fields
        if 'description' in data:
            validated['description'] = cls.validate_description(data['description'])
        
        if 'labels' in data:
            validated['labels'] = cls.validate_labels(data['labels'])
        
        if 'due_date' in data:
            validated['due_date'] = cls.validate_due_date(data['due_date'])
        
        if 'weight' in data:
            validated['weight'] = cls.validate_weight(data['weight'])
        
        # Pass through other fields
        for key in ['milestone_id', 'assignee_ids', 'confidential']:
            if key in data:
                validated[key] = data[key]
        
        return validated


class FileValidator:
    """Validator for file operations."""
    
    @staticmethod
    def validate_file_exists(file_path: Union[str, Path]) -> Path:
        """Validate that a file exists."""
        path = Path(file_path)
        
        if not path.exists():
            raise ValidationError(f"File not found: {path}")
        
        if not path.is_file():
            raise ValidationError(f"Not a file: {path}")
        
        return path
    
    @staticmethod
    def validate_directory_exists(dir_path: Union[str, Path]) -> Path:
        """Validate that a directory exists."""
        path = Path(dir_path)
        
        if not path.exists():
            raise ValidationError(f"Directory not found: {path}")
        
        if not path.is_dir():
            raise ValidationError(f"Not a directory: {path}")
        
        return path
    
    @staticmethod
    def validate_file_extension(
        file_path: Union[str, Path], 
        allowed_extensions: List[str]
    ) -> Path:
        """Validate file extension."""
        path = Path(file_path)
        
        if not any(path.suffix.lower() == ext.lower() for ext in allowed_extensions):
            raise ValidationError(
                f"Invalid file extension '{path.suffix}'. "
                f"Allowed: {', '.join(allowed_extensions)}"
            )
        
        return path


class ProjectValidator:
    """Validator for project data."""
    
    @staticmethod
    def validate_project_name(name: str) -> str:
        """Validate project name."""
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty")
        
        name = name.strip()
        
        if len(name) > 255:
            raise ValidationError(
                f"Project name too long ({len(name)} chars). Maximum: 255 chars"
            )
        
        return name
    
    @staticmethod
    def validate_project_path(path: str) -> str:
        """Validate project path."""
        if not path:
            return ""
        
        # GitLab path rules
        pattern = re.compile(r'^[a-zA-Z0-9_\-]+$')
        
        if not pattern.match(path):
            raise ValidationError(
                f"Invalid project path '{path}'. "
                "Path can only contain letters, numbers, underscores, and hyphens"
            )
        
        return path


class TemplateValidator:
    """Validator for template data."""
    
    @staticmethod
    def validate_template_variables(
        template: str,
        provided_variables: Dict[str, Any],
        required_variables: List[str]
    ) -> None:
        """Validate that all required template variables are provided."""
        # Extract variables from template
        import re
        template_vars = re.findall(r'\{(\w+)\}', template)
        
        # Check required variables
        missing_required = set(required_variables) - set(provided_variables.keys())
        if missing_required:
            raise ValidationError(
                f"Missing required template variables: {', '.join(missing_required)}"
            )
        
        # Check template variables are provided
        missing_template = set(template_vars) - set(provided_variables.keys())
        if missing_template:
            raise ValidationError(
                f"Missing template variables: {', '.join(missing_template)}"
            )