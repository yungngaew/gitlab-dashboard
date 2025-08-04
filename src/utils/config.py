"""Configuration management for GitLab tools."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    # Simple fallback for loading .env file
    def load_dotenv():
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()


class Config:
    """Configuration manager that merges YAML config with environment variables."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Find config file
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Look for config in standard locations
            possible_paths = [
                Path("config/config.yaml"),
                Path("config.yaml"),
                Path.home() / ".gitlab-tools" / "config.yaml"
            ]
            
            for path in possible_paths:
                if path.exists():
                    self.config_path = path
                    break
            else:
                # Use default config path
                self.config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        # Load configuration
        self._config = self._load_config()
        
        # Override with environment variables
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # GitLab credentials
        if os.getenv('GITLAB_URL'):
            self._config.setdefault('gitlab', {})['url'] = os.getenv('GITLAB_URL')
        
        if os.getenv('GITLAB_API_TOKEN'):
            self._config.setdefault('gitlab', {})['token'] = os.getenv('GITLAB_API_TOKEN')
        
        # Rate limiting
        if os.getenv('GITLAB_RATE_LIMIT'):
            self._config.setdefault('gitlab', {})['rate_limit'] = float(os.getenv('GITLAB_RATE_LIMIT'))
        
        # Timeout
        if os.getenv('GITLAB_TIMEOUT'):
            self._config.setdefault('gitlab', {})['timeout'] = int(os.getenv('GITLAB_TIMEOUT'))
        
        # Default groups
        if os.getenv('GITLAB_DEFAULT_GROUPS'):
            groups = os.getenv('GITLAB_DEFAULT_GROUPS').split(',')
            self._config['groups'] = [{'name': g.strip()} for g in groups]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'gitlab.rate_limit')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_gitlab_config(self) -> Dict[str, Any]:
        """Get GitLab-specific configuration."""
        return self.get('gitlab', {})
    
    def get_groups(self) -> list:
        """Get configured groups."""
        return self.get('groups', [])
    
    def is_dry_run(self) -> bool:
        """Check if dry-run mode is enabled."""
        # CLI flag takes precedence
        if os.getenv('GITLAB_DRY_RUN'):
            return os.getenv('GITLAB_DRY_RUN').lower() in ('true', '1', 'yes')
        return self.get('features.dry_run', False)
    
    def should_backup(self) -> bool:
        """Check if backup is enabled."""
        return self.get('features.backup', True)
    
    def get_output_dir(self) -> Path:
        """Get output directory path."""
        output_dir = self.get('output.directory', 'outputs')
        return Path(output_dir)
    
    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get('logging', {})
    
    def get_teams_config(self) -> Dict[str, Any]:
        """Get Teams-specific configuration."""
        return self.get('teams', {})
    
    def get_history_config(self) -> Dict[str, Any]:
        """Get history-specific configuration."""
        return self.get('history', {})
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email-specific configuration."""
        return self.get('email', {})
    
    def validate(self) -> bool:
        """Validate required configuration values.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If required configuration is missing
        """
        gitlab_config = self.get_gitlab_config()
        
        if not gitlab_config.get('url'):
            raise ValueError("GitLab URL not configured. Set GITLAB_URL environment variable.")
        
        if not gitlab_config.get('token'):
            raise ValueError("GitLab API token not configured. Set GITLAB_API_TOKEN environment variable.")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary.
        
        Returns:
            Copy of the configuration dictionary
        """
        return self._config.copy()
    
    @property
    def data(self) -> Dict[str, Any]:
        """Return configuration data for backward compatibility.
        
        Returns:
            Copy of the configuration dictionary
        """
        return self._config.copy()
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(config_path={self.config_path})"