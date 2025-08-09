"""Configuration management for the Trade Analyst application"""

import os
import json
import toml
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "trade_analyst"
    username: str = "postgres"
    password: str = ""


@dataclass
class APIProviderConfig:
    """API provider configuration"""
    base_url: str
    auth_type: str = "oauth"
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    rate_limit: int = 100


class Config:
    """Configuration manager for the application"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_data = {}
        self.config_file = config_file
        
        # Load configuration from multiple sources
        self._load_default_config()
        
        if config_file:
            self._load_config_file(config_file)
        else:
            # Try to find config file in standard locations
            for config_path in ['config.toml', '../config.toml', 'config/config.toml']:
                if Path(config_path).exists():
                    self._load_config_file(config_path)
                    break
        
        # Override with environment variables
        self._load_environment_variables()
    
    def _load_default_config(self):
        """Load default configuration values"""
        self.config_data = {
            'app': {
                'name': 'Trade Analyst',
                'version': '1.0.0',
                'debug': False,
                'log_level': 'INFO'
            },
            'server': {
                'host': '127.0.0.1',
                'port': 5000,
                'workers': 1
            },
            'data': {
                'base_path': 'data',
                'retention_days': 90,
                'compression': 'snappy',
                'max_file_size_mb': 100
            },
            'logging': {
                'log_dir': 'logs',
                'max_log_size_mb': 10,
                'backup_count': 5,
                'log_rotation': True
            },
            'rate_limits': {
                'quotes_per_minute': 100,
                'historical_per_minute': 50,
                'options_per_minute': 30,
                'timesales_per_minute': 200
            },
            'health_checks': {
                'timeout_seconds': 30,
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'disk_threshold': 90
            },
            'auth': {
                'token_file': 'tokens.json',
                'callback_timeout_seconds': 300,
                'max_retry_attempts': 3
            },
            'api_providers': {},
            'features': {
                'enable_quotes': True,
                'enable_historical': True,
                'enable_options': True,
                'enable_timesales': True,
                'enable_export': True
            }
        }
    
    def _load_config_file(self, config_file: str):
        """Load configuration from TOML file"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_file}")
            
            if config_path.suffix.lower() == '.toml':
                with open(config_path, 'r') as f:
                    file_config = toml.load(f)
            elif config_path.suffix.lower() == '.json':
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            # Merge with existing config
            self._deep_merge(self.config_data, file_config)
            self.config_file = config_file
            
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")
    
    def _load_environment_variables(self):
        """Load configuration from environment variables"""
        env_mappings = {
            'TRADE_ANALYST_DEBUG': ('app', 'debug'),
            'TRADE_ANALYST_LOG_LEVEL': ('app', 'log_level'),
            'TRADE_ANALYST_HOST': ('server', 'host'),
            'TRADE_ANALYST_PORT': ('server', 'port'),
            'TRADE_ANALYST_DATA_PATH': ('data', 'base_path'),
            'TRADE_ANALYST_LOG_DIR': ('logging', 'log_dir'),
            'TRADE_ANALYST_RETENTION_DAYS': ('data', 'retention_days'),
            
            # API Provider environment variables
            'API_PROVIDER_1_URL': ('api_providers', 'provider1', 'base_url'),
            'API_PROVIDER_1_CLIENT_ID': ('api_providers', 'provider1', 'client_id'),
            'API_PROVIDER_1_CLIENT_SECRET': ('api_providers', 'provider1', 'client_secret'),
            
            # Database configuration
            'DB_HOST': ('database', 'host'),
            'DB_PORT': ('database', 'port'),
            'DB_NAME': ('database', 'database'),
            'DB_USER': ('database', 'username'),
            'DB_PASSWORD': ('database', 'password'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(self.config_data, config_path, self._convert_env_value(value))
    
    def _deep_merge(self, base_dict: Dict, update_dict: Dict):
        """Deep merge two dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _set_nested_value(self, data: Dict, path: tuple, value: Any):
        """Set a value in a nested dictionary using a path tuple"""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _convert_env_value(self, value: str) -> Union[str, int, bool, float]:
        """Convert environment variable string to appropriate type"""
        # Convert boolean values
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Try to convert to number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'app.debug', 'server.port')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                value = value[k]
            
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'app.debug')
            value: Value to set
        """
        keys = key.split('.')
        current = self.config_data
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
    
    def has_key(self, key: str) -> bool:
        """Check if configuration key exists"""
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                value = value[k]
            
            return True
        except (KeyError, TypeError):
            return False
    
    def get_auth_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get authentication configuration for a provider"""
        auth_config = self.get(f'auth_providers.{provider}')
        if not auth_config:
            # Try generic auth configuration
            auth_config = self.get('auth', {})
        
        return auth_config
    
    def get_api_config(self, provider: str) -> Optional[APIProviderConfig]:
        """Get API provider configuration"""
        provider_config = self.get(f'api_providers.{provider}')
        if not provider_config:
            return None
        
        return APIProviderConfig(
            base_url=provider_config.get('base_url', ''),
            auth_type=provider_config.get('auth_type', 'oauth'),
            client_id=provider_config.get('client_id', ''),
            client_secret=provider_config.get('client_secret', ''),
            scope=provider_config.get('scope', ''),
            rate_limit=provider_config.get('rate_limit', 100)
        )
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_config = self.get('database', {})
        
        return DatabaseConfig(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 5432),
            database=db_config.get('database', 'trade_analyst'),
            username=db_config.get('username', 'postgres'),
            password=db_config.get('password', '')
        )
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get(f'features.enable_{feature}', True)
    
    def get_rate_limit(self, service: str) -> int:
        """Get rate limit for a service"""
        return self.get(f'rate_limits.{service}_per_minute', 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.config_data.copy()
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary without sensitive data"""
        safe_config = self.to_dict()
        
        # Remove sensitive keys
        sensitive_keys = [
            'api_providers.*.client_secret',
            'api_providers.*.password',
            'database.password',
            'auth.client_secret'
        ]
        
        # Create a deep copy and remove sensitive data
        import copy
        safe_config = copy.deepcopy(safe_config)
        
        # Remove sensitive values (simplified approach)
        if 'api_providers' in safe_config:
            for provider_config in safe_config['api_providers'].values():
                if isinstance(provider_config, dict):
                    provider_config.pop('client_secret', None)
                    provider_config.pop('password', None)
        
        if 'database' in safe_config:
            safe_config['database'].pop('password', None)
        
        return safe_config
    
    def save_to_file(self, file_path: str):
        """Save current configuration to file"""
        config_path = Path(file_path)
        
        if config_path.suffix.lower() == '.toml':
            with open(config_path, 'w') as f:
                toml.dump(self.config_data, f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        else:
            raise ValueError(f"Unsupported file format: {config_path.suffix}")
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return any issues"""
        issues = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Check required fields
        required_fields = [
            'app.name',
            'server.host',
            'server.port',
            'data.base_path'
        ]
        
        for field in required_fields:
            if not self.has_key(field):
                issues['errors'].append(f"Missing required field: {field}")
        
        # Check data types
        type_checks = [
            ('server.port', int),
            ('data.retention_days', int),
            ('app.debug', bool)
        ]
        
        for field, expected_type in type_checks:
            value = self.get(field)
            if value is not None and not isinstance(value, expected_type):
                issues['warnings'].append(f"Field {field} should be {expected_type.__name__}, got {type(value).__name__}")
        
        # Check API providers
        api_providers = self.get('api_providers', {})
        if not api_providers:
            issues['warnings'].append("No API providers configured")
        else:
            for provider, config in api_providers.items():
                if not config.get('base_url'):
                    issues['errors'].append(f"API provider {provider} missing base_url")
        
        # Check paths
        data_path = Path(self.get('data.base_path', 'data'))
        if not data_path.exists():
            issues['info'].append(f"Data directory does not exist: {data_path}")
        
        log_dir = Path(self.get('logging.log_dir', 'logs'))
        if not log_dir.exists():
            issues['info'].append(f"Log directory does not exist: {log_dir}")
        
        return issues
    
    def reload(self):
        """Reload configuration from file and environment"""
        self._load_default_config()
        
        if self.config_file:
            self._load_config_file(self.config_file)
        
        self._load_environment_variables()


# Singleton instance
_config_instance = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config():
    """Reload the global configuration"""
    global _config_instance
    if _config_instance:
        _config_instance.reload()


# Example usage
if __name__ == "__main__":
    # Test configuration
    config = Config()
    
    print("Configuration loaded:")
    print(f"App name: {config.get('app.name')}")
    print(f"Server port: {config.get('server.port')}")
    print(f"Debug mode: {config.get('app.debug')}")
    
    # Test validation
    validation_result = config.validate()
    print(f"\nValidation result:")
    print(f"Errors: {validation_result['errors']}")
    print(f"Warnings: {validation_result['warnings']}")
    print(f"Info: {validation_result['info']}")
    
    # Test safe dictionary
    safe_dict = config.to_safe_dict()
    print(f"\nSafe config keys: {list(safe_dict.keys())}")
