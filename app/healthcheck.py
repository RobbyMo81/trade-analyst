"""Health check system for monitoring application and dependencies"""

import logging
import asyncio
import aiohttp
import json
import psutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from .config import Config
from .utils.validators import is_valid_redirect_format, exact_match

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: str  # 'healthy', 'unhealthy', 'warning'
    message: str
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthStatus:
    """Overall health status"""
    is_healthy: bool
    timestamp: str
    checks: List[HealthCheck]
    summary: Dict[str, int]


class HealthChecker:
    """Performs various health checks on the application and its dependencies"""
    
    def __init__(self, config: Config):
        self.config = config
        self.timeout = config.get('health_check_timeout', 30)  # seconds
    
    async def check_all(self) -> HealthStatus:
        """
        Run all health checks
        
        Returns:
            HealthStatus: Overall health status with individual check results
        """
        try:
            logger.info("Running comprehensive health checks")
            start_time = datetime.now()
            
            # Run all health checks concurrently
            check_tasks = [
                self.check_system_resources(),
                self.check_disk_space(),
                self.check_log_files(),
                self.check_data_directories(),
                self.check_api_connectivity(),
                self.check_authentication(),
                self.check_database_connectivity(),
                self.check_redirect_allowlist(),
                self.check_external_dependencies()
            ]
            
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
            
            # Process results
            checks = []
            for result in results:
                if isinstance(result, Exception):
                    checks.append(HealthCheck(
                        name="health_check_error",
                        status="unhealthy",
                        message="Health check failed",
                        error=str(result)
                    ))
                elif result:
                    checks.append(result)
            
            # Calculate overall health
            is_healthy = all(check.status == 'healthy' for check in checks)
            
            # Create summary
            summary = {
                'healthy': sum(1 for check in checks if check.status == 'healthy'),
                'unhealthy': sum(1 for check in checks if check.status == 'unhealthy'),
                'warning': sum(1 for check in checks if check.status == 'warning')
            }
            
            health_status = HealthStatus(
                is_healthy=is_healthy,
                timestamp=datetime.now().isoformat(),
                checks=checks,
                summary=summary
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Health checks completed in {duration:.2f}s - Status: {'healthy' if is_healthy else 'unhealthy'}")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                is_healthy=False,
                timestamp=datetime.now().isoformat(),
                checks=[HealthCheck(
                    name="health_check_system",
                    status="unhealthy",
                    message="Health check system failure",
                    error=str(e)
                )],
                summary={'healthy': 0, 'unhealthy': 1, 'warning': 0}
            )
    
    async def check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        try:
            start_time = datetime.now()
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check if resources are within acceptable limits
            cpu_threshold = self.config.get('cpu_threshold', 80)
            memory_threshold = self.config.get('memory_threshold', 85)
            
            status = 'healthy'
            messages = []
            
            if cpu_percent > cpu_threshold:
                status = 'warning' if cpu_percent < 95 else 'unhealthy'
                messages.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > memory_threshold:
                status = 'warning' if memory_percent < 95 else 'unhealthy'
                messages.append(f"High memory usage: {memory_percent:.1f}%")
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message="; ".join(messages) if messages else "System resources normal",
                duration_ms=duration,
                metadata={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status="unhealthy",
                message="Failed to check system resources",
                error=str(e)
            )
    
    async def check_disk_space(self) -> HealthCheck:
        """Check available disk space"""
        try:
            start_time = datetime.now()
            
            # Check disk usage for current directory
            disk_usage = psutil.disk_usage('.')
            
            # Calculate free space percentage
            free_percent = (disk_usage.free / disk_usage.total) * 100
            used_percent = 100 - free_percent
            
            # Check thresholds
            disk_threshold = self.config.get('disk_threshold', 90)
            
            if used_percent > disk_threshold:
                status = 'warning' if used_percent < 95 else 'unhealthy'
                message = f"Low disk space: {used_percent:.1f}% used"
            else:
                status = 'healthy'
                message = f"Disk space normal: {used_percent:.1f}% used"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="disk_space",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'total_gb': disk_usage.total / (1024**3),
                    'free_gb': disk_usage.free / (1024**3),
                    'used_percent': used_percent
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="disk_space",
                status="unhealthy",
                message="Failed to check disk space",
                error=str(e)
            )
    
    async def check_log_files(self) -> HealthCheck:
        """Check log file accessibility and rotation"""
        try:
            start_time = datetime.now()
            
            logs_dir = Path("logs")
            
            if not logs_dir.exists():
                return HealthCheck(
                    name="log_files",
                    status="warning",
                    message="Logs directory does not exist"
                )
            
            # Check if logs directory is writable
            test_file = logs_dir / "health_check_test.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                return HealthCheck(
                    name="log_files",
                    status="unhealthy",
                    message="Logs directory is not writable"
                )
            
            # Check log file sizes
            log_files = list(logs_dir.glob("*.log"))
            large_files = []
            max_size_mb = self.config.get('max_log_size_mb', 100)
            
            for log_file in log_files:
                size_mb = log_file.stat().st_size / (1024**2)
                if size_mb > max_size_mb:
                    large_files.append(f"{log_file.name} ({size_mb:.1f}MB)")
            
            status = 'warning' if large_files else 'healthy'
            message = f"Large log files: {', '.join(large_files)}" if large_files else "Log files normal"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="log_files",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'log_count': len(log_files),
                    'large_files': len(large_files)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="log_files",
                status="unhealthy",
                message="Failed to check log files",
                error=str(e)
            )
    
    async def check_data_directories(self) -> HealthCheck:
        """Check data directory structure and accessibility"""
        try:
            start_time = datetime.now()
            
            required_dirs = ['data', 'data/quotes', 'data/historical', 'data/options', 'data/timesales']
            missing_dirs = []
            
            for dir_path in required_dirs:
                if not Path(dir_path).exists():
                    missing_dirs.append(dir_path)
            
            if missing_dirs:
                status = 'warning'
                message = f"Missing data directories: {', '.join(missing_dirs)}"
            else:
                status = 'healthy'
                message = "All data directories exist"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="data_directories",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'required_dirs': len(required_dirs),
                    'missing_dirs': len(missing_dirs)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="data_directories",
                status="unhealthy",
                message="Failed to check data directories",
                error=str(e)
            )
    
    async def check_api_connectivity(self) -> HealthCheck:
        """Check connectivity to external APIs"""
        try:
            start_time = datetime.now()
            
            # Get API endpoints from configuration
            api_endpoints = self.config.get('api_endpoints', {})
            
            if not api_endpoints:
                return HealthCheck(
                    name="api_connectivity",
                    status="warning",
                    message="No API endpoints configured"
                )
            
            results = {}
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for provider, endpoint in api_endpoints.items():
                    try:
                        async with session.get(endpoint + '/health', ssl=False) as response:
                            results[provider] = response.status == 200
                    except Exception:
                        results[provider] = False
            
            failed_apis = [provider for provider, success in results.items() if not success]
            
            if failed_apis:
                status = 'warning' if len(failed_apis) < len(api_endpoints) else 'unhealthy'
                message = f"API connectivity issues: {', '.join(failed_apis)}"
            else:
                status = 'healthy'
                message = "All APIs accessible"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="api_connectivity",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'total_apis': len(api_endpoints),
                    'failed_apis': len(failed_apis)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="api_connectivity",
                status="unhealthy",
                message="Failed to check API connectivity",
                error=str(e)
            )
    
    async def check_authentication(self) -> HealthCheck:
        """Check authentication status"""
        try:
            start_time = datetime.now()
            
            # Check if token files exist and are readable
            token_file = Path("tokens.json")
            
            if not token_file.exists():
                return HealthCheck(
                    name="authentication",
                    status="warning",
                    message="No authentication tokens found"
                )
            
            # Try to read token file
            try:
                with open(token_file, 'r') as f:
                    tokens = json.load(f)
                
                if not tokens:
                    status = 'warning'
                    message = "Token file is empty"
                else:
                    status = 'healthy'
                    message = f"Authentication tokens available for {len(tokens)} providers"
                    
            except json.JSONDecodeError:
                status = 'unhealthy'
                message = "Token file is corrupted"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="authentication",
                status=status,
                message=message,
                duration_ms=duration
            )
            
        except Exception as e:
            return HealthCheck(
                name="authentication",
                status="unhealthy",
                message="Failed to check authentication",
                error=str(e)
            )
    
    async def check_database_connectivity(self) -> HealthCheck:
        """Check database connectivity (if applicable)"""
        try:
            start_time = datetime.now()
            
            # For this application, we're using file-based storage
            # Check if we can write to the data directory
            data_dir = Path("data")
            
            if not data_dir.exists():
                return HealthCheck(
                    name="database_connectivity",
                    status="unhealthy",
                    message="Data directory does not exist"
                )
            
            # Test write access
            test_file = data_dir / "health_check_test.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                status = 'healthy'
                message = "Data storage accessible"
            except Exception:
                status = 'unhealthy'
                message = "Data storage not writable"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="database_connectivity",
                status=status,
                message=message,
                duration_ms=duration
            )
            
        except Exception as e:
            return HealthCheck(
                name="database_connectivity",
                status="unhealthy",
                message="Failed to check database connectivity",
                error=str(e)
            )
    
    async def check_external_dependencies(self) -> HealthCheck:
        """Check external service dependencies"""
        try:
            start_time = datetime.now()
            
            # Check internet connectivity
            test_urls = [
                'https://www.google.com',
                'https://httpbin.org/get'
            ]
            
            connectivity_results = []
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                for url in test_urls:
                    try:
                        async with session.get(url) as response:
                            connectivity_results.append(response.status == 200)
                    except Exception:
                        connectivity_results.append(False)
            
            if any(connectivity_results):
                status = 'healthy'
                message = "Internet connectivity available"
            else:
                status = 'unhealthy'
                message = "No internet connectivity"
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                name="external_dependencies",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'tested_urls': len(test_urls),
                    'successful_connections': sum(connectivity_results)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="external_dependencies",
                status="unhealthy",
                message="Failed to check external dependencies",
                error=str(e)
            )

    async def check_redirect_allowlist(self) -> HealthCheck:
        """Validate that configured redirect is exactly registered."""
        try:
            redirect = self.config.get('env.dev.redirect_uri') or ''
            registered = self.config.get('auth.registered_uris', []) or []
            if not is_valid_redirect_format(redirect):
                return HealthCheck(
                    name="redirect_uri",
                    status="unhealthy",
                    message=f"Redirect format invalid: {redirect}",
                )
            if not exact_match(redirect, registered):
                return HealthCheck(
                    name="redirect_uri",
                    status="unhealthy",
                    message="Redirect URI not in exact allowlist",
                    metadata={'redirect': redirect}
                )
            return HealthCheck(
                name="redirect_uri",
                status="healthy",
                message="Redirect URI exact match",
                metadata={'redirect': redirect}
            )
        except Exception as e:
            return HealthCheck(
                name="redirect_uri",
                status="unhealthy",
                message="Failed redirect validation",
                error=str(e)
            )


# Example usage
async def main():
    """Example usage of HealthChecker"""
    config = Config()
    health_checker = HealthChecker(config)
    
    health_status = await health_checker.check_all()
    
    print(f"Overall Health: {'✅ Healthy' if health_status.is_healthy else '❌ Unhealthy'}")
    print(f"Timestamp: {health_status.timestamp}")
    print(f"Summary: {health_status.summary}")
    print("\nDetailed Results:")
    
    for check in health_status.checks:
        status_icon = {'healthy': '✅', 'warning': '⚠️', 'unhealthy': '❌'}.get(check.status, '❓')
        print(f"  {status_icon} {check.name}: {check.message}")
        if check.error:
            print(f"    Error: {check.error}")


if __name__ == "__main__":
    asyncio.run(main())
