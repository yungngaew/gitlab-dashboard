"""Unit tests for configuration management."""

import pytest
import os
from pathlib import Path
import yaml
from src.utils.config import Config


class TestConfig:
    """Test configuration management."""
    
    def test_config_load_from_file(self, temp_dir):
        """Test loading configuration from file."""
        config_data = {
            'gitlab': {'url': 'https://gitlab.example.com'},
            'features': {'dry_run': True}
        }
        
        config_file = temp_dir / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        assert config.get('gitlab.url') == 'https://gitlab.example.com'
        assert config.get('features.dry_run') is True
    
    def test_config_environment_override(self, temp_dir, mock_env):
        """Test environment variables override file config."""
        config_data = {
            'gitlab': {
                'url': 'https://gitlab.example.com',
                'token': 'file-token'
            }
        }
        
        config_file = temp_dir / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Set environment variable
        mock_env(GITLAB_API_TOKEN='env-token')
        
        config = Config(str(config_file))
        
        assert config.get('gitlab.url') == 'https://gitlab.example.com'
        assert config.get('gitlab.token') == 'env-token'  # Should use env value
    
    def test_config_get_nested(self, test_config):
        """Test getting nested configuration values."""
        assert test_config.get('gitlab.rate_limit') == 3
        assert test_config.get('features.show_progress') is True
        assert test_config.get('branch_operations.default_old_branch') == 'trunk'
    
    def test_config_get_default(self, test_config):
        """Test getting configuration with default value."""
        assert test_config.get('nonexistent.key', 'default') == 'default'
        assert test_config.get('gitlab.missing', 100) == 100
    
    def test_config_get_groups(self, test_config):
        """Test getting groups configuration."""
        groups = test_config.get_groups()
        
        assert len(groups) == 1
        assert groups[0]['name'] == 'Test-Group'
        assert groups[0]['filters']['exclude_archived'] is True
    
    def test_config_is_dry_run(self, test_config, mock_env):
        """Test dry run detection."""
        # Default from config
        assert test_config.is_dry_run() is False
        
        # Override with environment variable
        mock_env(GITLAB_DRY_RUN='true')
        config = Config(test_config.config_file)
        assert config.is_dry_run() is True
    
    def test_config_get_gitlab_config(self, temp_dir, mock_env):
        """Test getting GitLab configuration."""
        config_data = {
            'gitlab': {
                'rate_limit': 5,
                'timeout': 60
            }
        }
        
        config_file = temp_dir / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        mock_env(
            GITLAB_URL='https://gitlab.test.com',
            GITLAB_API_TOKEN='test-token'
        )
        
        config = Config(str(config_file))
        gitlab_config = config.get_gitlab_config()
        
        assert gitlab_config['url'] == 'https://gitlab.test.com'
        assert gitlab_config['token'] == 'test-token'
        assert gitlab_config['rate_limit'] == 5
        assert gitlab_config['timeout'] == 60
    
    def test_config_validate_missing_gitlab_url(self, temp_dir):
        """Test validation fails without GitLab URL."""
        config_data = {'features': {'dry_run': False}}
        
        config_file = temp_dir / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "GITLAB_URL" in str(exc_info.value)
    
    def test_config_validate_missing_token(self, temp_dir, mock_env):
        """Test validation fails without GitLab token."""
        config_data = {'features': {'dry_run': False}}
        
        config_file = temp_dir / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        mock_env(GITLAB_URL='https://gitlab.test.com')
        
        config = Config(str(config_file))
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "GITLAB_API_TOKEN" in str(exc_info.value)
    
    def test_config_validate_success(self, temp_dir, mock_env):
        """Test successful validation."""
        config_data = {'features': {'dry_run': False}}
        
        config_file = temp_dir / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        mock_env(
            GITLAB_URL='https://gitlab.test.com',
            GITLAB_API_TOKEN='test-token'
        )
        
        config = Config(str(config_file))
        config.validate()  # Should not raise
    
    def test_config_get_log_config(self, test_config):
        """Test getting logging configuration."""
        log_config = test_config.get_log_config()
        
        assert log_config['level'] == 'INFO'
        assert 'file' in log_config
        assert log_config['max_size'] == 10
        assert log_config['backup_count'] == 5
    
    def test_config_nonexistent_file(self):
        """Test loading nonexistent config file."""
        config = Config('/nonexistent/config.yaml')
        
        # Should still work with defaults/env vars
        assert config.data == {}
        assert config.get('missing.key', 'default') == 'default'
    
    def test_config_invalid_yaml(self, temp_dir):
        """Test handling invalid YAML file."""
        config_file = temp_dir / 'invalid.yaml'
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        config = Config(str(config_file))
        
        # Should handle gracefully
        assert config.data == {}
    
    def test_config_to_dict(self, test_config):
        """Test to_dict method returns configuration dictionary."""
        config_dict = test_config.to_dict()
        
        # Should return a dictionary
        assert isinstance(config_dict, dict)
        
        # Should contain expected keys
        assert 'gitlab' in config_dict
        assert 'features' in config_dict
        
        # Should be a copy (modifying shouldn't affect original)
        config_dict['new_key'] = 'new_value'
        assert 'new_key' not in test_config.to_dict()
    
    def test_config_data_property(self, test_config):
        """Test data property for backward compatibility."""
        # data property should work the same as to_dict()
        assert test_config.data == test_config.to_dict()
        
        # Should also be a copy
        data = test_config.data
        data['test'] = 'value'
        assert 'test' not in test_config.data