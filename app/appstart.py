"""Application startup orchestrator - coordinates healthcheck, system initialization, and export operations"""

import logging
from typing import Optional
from .healthcheck import HealthChecker
from .systeminit import SystemInitializer
from .config import Config
from .logging import setup_logging

logger = logging.getLogger(__name__)


class AppOrchestrator:
    """Orchestrates application startup sequence"""
    
    def __init__(self, config: Config):
        self.config = config
        self.health_checker = HealthChecker(config)
        self.system_initializer = SystemInitializer(config)
    
    async def startup(self, dry_run: bool = False) -> bool:
        """
        Execute startup sequence: healthcheck -> system init -> (optional) export
        
        Args:
            dry_run: If True, perform dry run without actual export
            
        Returns:
            bool: True if startup successful, False otherwise
        """
        try:
            logger.info("Starting application orchestration")
            # Log chosen provider base to aid diagnostics
            try:
                md_base = self.config.get_schwab_market_base()
                if md_base:
                    logger.info("Schwab Market Data base: %s", md_base)
                else:
                    logger.info("Schwab Market Data base: <not configured>")
            except Exception:
                # non-fatal
                pass
            
            # Step 1: Health check
            logger.info("Running health checks...")
            health_status = await self.health_checker.check_all()
            if not health_status.is_healthy:
                unhealthy_msgs = [c.message for c in health_status.checks if c.status == 'unhealthy']
                logger.error("Health check failed: %s", "; ".join(unhealthy_msgs) or "see details")
                return False
            
            # Step 2: System initialization
            logger.info("Initializing system...")
            init_success = await self.system_initializer.initialize()
            if not init_success:
                logger.error("System initialization failed")
                return False
            
            # Step 3: Optional export (dry run or actual)
            if dry_run:
                logger.info("Dry run mode - skipping actual export")
                await self._dry_export()
            else:
                logger.info("Startup sequence completed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Startup orchestration failed: {e}")
            return False
    
    async def _dry_export(self):
        """Perform a dry run export to validate configuration"""
        logger.info("Performing dry run export validation")
        # TODO: Implement dry run export logic
        pass


async def main():
    """Main application startup entry point"""
    setup_logging()
    config = Config()
    orchestrator = AppOrchestrator(config)
    
    success = await orchestrator.startup()
    if not success:
        logger.error("Application startup failed")
        return False
    
    logger.info("Application started successfully")
    return True


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
