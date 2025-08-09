"""System initialization and setup"""

import logging
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from .config import Config

logger = logging.getLogger(__name__)


class SystemInitializer:
    """Handles system initialization and setup"""
    
    def __init__(self, config: Config):
        self.config = config
        self.required_directories = [
            'logs',
            'data',
            'data/quotes',
            'data/historical',
            'data/options',
            'data/timesales',
            'data/exports'
        ]
    
    async def initialize(self) -> bool:
        """
        Initialize the system
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("Starting system initialization")
            
            # Create required directories
            if not await self._create_directories():
                logger.error("Failed to create required directories")
                return False
            
            # Initialize logging
            if not await self._setup_logging():
                logger.error("Failed to setup logging")
                return False
            
            # Initialize data storage
            if not await self._setup_data_storage():
                logger.error("Failed to setup data storage")
                return False
            
            # Validate configuration
            if not await self._validate_configuration():
                logger.error("Configuration validation failed")
                return False
            
            # Initialize API connections
            if not await self._initialize_api_connections():
                logger.error("Failed to initialize API connections")
                return False
            
            logger.info("System initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            return False
    
    async def _create_directories(self) -> bool:
        """Create required directories"""
        try:
            logger.info("Creating required directories")
            
            for directory in self.required_directories:
                dir_path = Path(directory)
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                else:
                    logger.debug(f"Directory already exists: {directory}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            return False
    
    async def _setup_logging(self) -> bool:
        """Setup logging configuration"""
        try:
            logger.info("Setting up logging configuration")
            
            # Ensure logs directory exists
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Create log rotation setup
            log_config = {
                'main_log': 'logs/trade-analyst.log',
                'error_log': 'logs/trade-analyst-error.log',
                'access_log': 'logs/access.log',
                'data_log': 'logs/data-collection.log'
            }
            
            # Create log files if they don't exist
            for log_name, log_path in log_config.items():
                log_file = Path(log_path)
                if not log_file.exists():
                    log_file.touch()
                    logger.info(f"Created log file: {log_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")
            return False
    
    async def _setup_data_storage(self) -> bool:
        """Setup data storage directories and initial files"""
        try:
            logger.info("Setting up data storage")
            
            # Create metadata files for each data type
            data_types = ['quotes', 'historical', 'options', 'timesales']
            
            for data_type in data_types:
                metadata_file = Path(f"data/{data_type}/metadata.json")
                if not metadata_file.exists():
                    # Create initial metadata
                    import json
                    initial_metadata = {
                        'data_type': data_type,
                        'created_at': '2024-01-01T00:00:00Z',
                        'last_updated': '2024-01-01T00:00:00Z',
                        'record_count': 0,
                        'schema_version': '1.0',
                        'files': []
                    }
                    
                    with open(metadata_file, 'w') as f:
                        json.dump(initial_metadata, f, indent=2)
                    
                    logger.info(f"Created metadata file: {metadata_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup data storage: {e}")
            return False
    
    async def _validate_configuration(self) -> bool:
        """Validate application configuration"""
        try:
            logger.info("Validating configuration")
            
            # Check required configuration keys
            required_keys = [
                'api_providers',
                'data_retention_days',
                'export_formats',
                'rate_limits'
            ]
            
            for key in required_keys:
                if not self.config.has_key(key):
                    logger.warning(f"Missing configuration key: {key}")
            
            # Validate API provider configurations
            providers = self.config.get('api_providers', {})
            for provider_name, provider_config in providers.items():
                if not self._validate_provider_config(provider_name, provider_config):
                    logger.warning(f"Invalid configuration for provider: {provider_name}")
            
            # Validate rate limits
            rate_limits = self.config.get('rate_limits', {})
            if not rate_limits:
                logger.warning("No rate limits configured")
            
            logger.info("Configuration validation completed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def _validate_provider_config(self, provider_name: str, provider_config: Dict[str, Any]) -> bool:
        """Validate individual provider configuration"""
        required_fields = ['base_url', 'auth_type']
        
        for field in required_fields:
            if field not in provider_config:
                logger.error(f"Missing required field '{field}' for provider {provider_name}")
                return False
        
        return True
    
    async def _initialize_api_connections(self) -> bool:
        """Initialize API connections and test connectivity"""
        try:
            logger.info("Initializing API connections")
            
            # Get API providers from config
            providers = self.config.get('api_providers', {})
            
            connection_results = {}
            
            for provider_name, provider_config in providers.items():
                try:
                    # Test connection to provider
                    success = await self._test_provider_connection(provider_name, provider_config)
                    connection_results[provider_name] = success
                    
                    if success:
                        logger.info(f"Successfully connected to provider: {provider_name}")
                    else:
                        logger.warning(f"Failed to connect to provider: {provider_name}")
                        
                except Exception as e:
                    logger.error(f"Error testing connection to provider {provider_name}: {e}")
                    connection_results[provider_name] = False
            
            # Check if at least one provider is available
            if not any(connection_results.values()):
                logger.error("No API providers are available")
                return False
            
            logger.info("API connections initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize API connections: {e}")
            return False
    
    async def _test_provider_connection(self, provider_name: str, provider_config: Dict[str, Any]) -> bool:
        """Test connection to a specific provider"""
        try:
            # TODO: Implement actual connection testing
            # For now, just validate the configuration structure
            base_url = provider_config.get('base_url')
            if not base_url:
                return False
            
            # Simulate connection test
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # In a real implementation, you would make an HTTP request to test connectivity
            return True
            
        except Exception as e:
            logger.error(f"Provider connection test failed for {provider_name}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup system resources"""
        try:
            logger.info("Cleaning up system resources")
            
            # TODO: Implement cleanup logic
            # - Close database connections
            # - Stop background tasks
            # - Clean temporary files
            
            logger.info("System cleanup completed")
            
        except Exception as e:
            logger.error(f"System cleanup failed: {e}")
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            import psutil
            import platform
            
            system_info = {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': {
                    'total': psutil.disk_usage('.').total,
                    'free': psutil.disk_usage('.').free,
                    'used': psutil.disk_usage('.').used
                },
                'directories': {
                    'logs_size': self._get_directory_size('logs'),
                    'data_size': self._get_directory_size('data')
                }
            }
            
            return system_info
            
        except ImportError:
            # psutil not available, return basic info
            return {
                'platform': 'unknown',
                'directories': {
                    'logs_exists': Path('logs').exists(),
                    'data_exists': Path('data').exists()
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}
    
    def _get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size
        except Exception:
            return 0


# Example usage
async def main():
    """Example usage of SystemInitializer"""
    config = Config()
    initializer = SystemInitializer(config)
    
    success = await initializer.initialize()
    if success:
        print("System initialized successfully")
        
        system_info = await initializer.get_system_info()
        print(f"System info: {system_info}")
    else:
        print("System initialization failed")


if __name__ == "__main__":
    asyncio.run(main())
