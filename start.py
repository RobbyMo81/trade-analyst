#!/usr/bin/env python3
"""
Trade Analyst Application Startup Script

This script provides a convenient way to start the Trade Analyst application
with various configuration options and modes.
"""

import sys
import os
import subprocess
import argparse
import logging
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def setup_logging(level: str = "INFO"):
    """Setup basic logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def check_requirements():
    """Check if required packages are installed"""
    try:
        import flask
        import pandas
        import aiohttp
        import click
        import toml
        print("✓ Core dependencies found")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def check_environment():
    """Check environment setup"""
    issues = []
    
    # Check config file
    if not os.path.exists("config.toml"):
        issues.append("Missing config.toml file")
    
    # Check data directories
    data_dirs = ["data", "logs", "tokens"]
    for dir_name in data_dirs:
        if not os.path.exists(dir_name):
            print(f"Creating directory: {dir_name}")
            os.makedirs(dir_name, exist_ok=True)
    
    # Check .env file
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("⚠ No .env file found. Please copy .env.example to .env and configure")
            issues.append("Missing .env file")
        else:
            issues.append("Missing .env and .env.example files")
    
    if issues:
        print("\n".join([f"✗ {issue}" for issue in issues]))
        return False
    
    print("✓ Environment setup looks good")
    return True

def start_server(host: str = "localhost", port: int = 8080, debug: bool = False):
    """Start the Flask server"""
    try:
        from app.main import serve_callback
        
        print(f"Starting Trade Analyst server on http://{host}:{port}")
        print("Press Ctrl+C to stop the server")
        
        # Start the server
        serve_callback(host, port, debug)
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

def run_health_check():
    """Run health check"""
    try:
        from app.main import healthcheck
        healthcheck()
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

def run_auth_flow():
    """Run authentication flow"""
    try:
        from app.main import auth_login
        auth_login()
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)

def export_data(symbol: str = None, data_type: str = "all", format: str = "csv"):
    """Export data"""
    try:
        from app.main import export as export_cmd
        
        # Build export arguments
        args = [data_type]
        if symbol:
            args.extend(["--symbol", symbol])
        args.extend(["--format", format])
        
        export_cmd(args)
    except Exception as e:
        print(f"Export failed: {e}")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Trade Analyst Application")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start the web server")
    server_parser.add_argument("--host", default="localhost", help="Server host")
    server_parser.add_argument("--port", type=int, default=8080, help="Server port")
    server_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Health check command
    subparsers.add_parser("health", help="Run health check")
    
    # Authentication command
    subparsers.add_parser("auth", help="Run authentication flow")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("--symbol", help="Symbol to export")
    export_parser.add_argument("--type", default="all", choices=["quotes", "historical", "options", "timesales", "all"],
                              help="Data type to export")
    export_parser.add_argument("--format", default="csv", choices=["csv", "json", "parquet"],
                              help="Export format")
    
    # Install command
    subparsers.add_parser("install", help="Install dependencies")
    
    # Setup command
    subparsers.add_parser("setup", help="Setup environment")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Handle commands
    if args.command == "install":
        install_dependencies()
        return
    
    if args.command == "setup":
        if not check_requirements():
            print("Run: python start.py install")
            return
        check_environment()
        return
    
    # Check dependencies for other commands
    if not check_requirements():
        print("Please install dependencies first: python start.py install")
        sys.exit(1)
    
    if not check_environment():
        print("Please fix environment issues first")
        sys.exit(1)
    
    if args.command == "server":
        start_server(args.host, args.port, args.debug)
    elif args.command == "health":
        run_health_check()
    elif args.command == "auth":
        run_auth_flow()
    elif args.command == "export":
        export_data(args.symbol, args.type, args.format)
    else:
        # Default to server
        print("No command specified, starting server...")
        start_server()

if __name__ == "__main__":
    main()
