"""Command Line Interface for Trade Analyst Application"""

import click
import asyncio
import logging
from typing import Optional
from .appstart import AppOrchestrator
from .config import Config
from .logging import setup_logging
from .server import app as flask_app
from .auth import AuthManager
from .healthcheck import HealthChecker

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx, verbose, config):
    """Trade Analyst CLI - Financial data collection and analysis tool"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_path'] = config
    
    # Setup logging
    setup_logging(verbose=verbose)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind the server to')
@click.option('--port', default=5000, help='Port to bind the server to')
@click.option('--debug', is_flag=True, help='Run in debug mode')
@click.pass_context
def serve_callback(ctx, host, port, debug):
    """Start the callback server for OAuth authentication"""
    logger.info(f"Starting callback server on {host}:{port}")
    flask_app.run(host=host, port=port, debug=debug)


@cli.command()
@click.option('--provider', default='default', help='Authentication provider to use')
@click.pass_context
def auth_login(ctx, provider):
    """Initiate authentication login flow"""
    async def _auth_login():
        config = Config(ctx.obj.get('config_path'))
        auth_manager = AuthManager(config)
        
        try:
            success = await auth_manager.login(provider)
            if success:
                click.echo("Authentication successful!")
            else:
                click.echo("Authentication failed!")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            click.echo(f"Authentication error: {e}")
            return False
        
        return True
    
    success = asyncio.run(_auth_login())
    if not success:
        raise click.ClickException("Authentication failed")


@cli.command()
@click.pass_context
def healthcheck(ctx):
    """Run system health checks"""
    async def _healthcheck():
        config = Config(ctx.obj.get('config_path'))
        health_checker = HealthChecker(config)
        
        health_status = await health_checker.check_all()
        
        if health_status.is_healthy:
            click.echo("✅ All health checks passed")
            for check in health_status.checks:
                click.echo(f"  ✅ {check.name}: {check.status}")
        else:
            click.echo("❌ Health checks failed")
            for check in health_status.checks:
                status_icon = "✅" if check.status == "healthy" else "❌"
                click.echo(f"  {status_icon} {check.name}: {check.status}")
                if check.error:
                    click.echo(f"    Error: {check.error}")
        
        return health_status.is_healthy
    
    success = asyncio.run(_healthcheck())
    if not success:
        raise click.ClickException("Health checks failed")


@cli.command()
@click.option('--dry-run', is_flag=True, help='Perform dry run without actual export')
@click.option('--data-type', type=click.Choice(['quotes', 'historical', 'options', 'timesales']), 
              help='Type of data to export')
@click.pass_context
def export(ctx, dry_run, data_type):
    """Export financial data"""
    async def _export():
        config = Config(ctx.obj.get('config_path'))
        orchestrator = AppOrchestrator(config)
        
        if dry_run:
            click.echo("Performing dry run export...")
            success = await orchestrator.startup(dry_run=True)
        else:
            click.echo(f"Exporting {data_type or 'all'} data...")
            success = await orchestrator.startup(dry_run=False)
            # TODO: Add specific data type export logic
        
        return success
    
    success = asyncio.run(_export())
    if success:
        click.echo("Export completed successfully!")
    else:
        raise click.ClickException("Export failed")


@cli.command()
@click.pass_context
def status(ctx):
    """Show application status"""
    config = Config(ctx.obj.get('config_path'))
    
    click.echo("Trade Analyst Status:")
    click.echo(f"Configuration: {config.config_file or 'default'}")
    click.echo(f"Log Level: {logging.getLogger().level}")
    # TODO: Add more status information


if __name__ == '__main__':
    cli()
