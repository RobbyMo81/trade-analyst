#!/usr/bin/env python3
"""
Trade Analyst Application Startup Script

This script provides a convenient way to start the Trade Analyst application
with various configuration options and modes.
"""

from typing import Optional
import sys
import os
import subprocess
import argparse
import logging
import asyncio
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

def start_callback_server_background(port: int = 8443) -> Optional[subprocess.Popen]:
    """Start the callback server in background for authentication"""
    try:
        print(f"Starting callback server on port {port}...")
        # Start callback server as background process
        callback_cmd = [
            sys.executable, "-m", "scripts.callback_server", 
            "--env", "dev", "--port", str(port), "--tls"
        ]
        
        callback_process = subprocess.Popen(
            callback_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        # Give it a moment to start
        import time
        time.sleep(2)
        
        if callback_process.poll() is None:  # Still running
            print(f"✓ Callback server started on https://127.0.0.1:{port}")
            return callback_process
        else:
            print("✗ Callback server failed to start")
            return None
            
    except Exception as e:
        print(f"✗ Failed to start callback server: {e}")
        return None

def run_authentication_flow():
    """Run the complete authentication flow with integrated callback server"""
    try:
        # Start callback server first
        callback_process = start_callback_server_background()
        
        if not callback_process:
            print("Cannot proceed without callback server")
            return False
            
        try:
            print("\nStarting authentication flow...")
            print("A browser window will open for Schwab login.")
            
            # Run auth-login command  
            auth_cmd = [
                sys.executable, "-m", "scripts.secure_auth_login",
                "--env", "dev", "--timeout", "180"
            ]
            
            result = subprocess.run(auth_cmd, cwd=os.getcwd())
            
            if result.returncode == 0:
                print("✓ Authentication completed successfully")
                return True
            else:
                print("✗ Authentication failed")
                return False
                
        finally:
            # Clean up callback server
            if callback_process and callback_process.poll() is None:
                callback_process.terminate()
                callback_process.wait(timeout=5)
                print("✓ Callback server stopped")
                
    except Exception as e:
        print(f"✗ Authentication flow failed: {e}")
        return False

def check_authentication():
    """Check if user is authenticated, and if not, run the integrated auth flow"""
    try:
        from app.config import Config
        from app.auth import AuthManager
        
        # Initialize auth manager
        config = Config()
        auth_manager = AuthManager(config)
        
        # Check if we have a valid token
        async def _check_token():
            try:
                token = await auth_manager.get_access_token("default")
                return token is not None
            except Exception:
                return False
        
        # Run async check
        has_token = asyncio.run(_check_token())
        
        if not has_token:
            print("⚠ No valid authentication token found")
            print("Starting integrated authentication flow...")
            return run_authentication_flow()
        else:
            print("✓ Authentication token found")
            return True
            
    except Exception as e:
        print(f"✗ Authentication check failed: {e}")
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
        from app.server import app as flask_app
        
        print(f"Starting Trade Analyst server on http://{host}:{port}")
        print("Press Ctrl+C to stop the server")
        
        # Start the server directly
        flask_app.run(host=host, port=port, debug=debug)
        
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

def calc_levels(symbol: str, date: str, format: str = "ai-block"):
    """Calculate R1, S1, VWAP using production-safe real data with no fallbacks"""
    
    try:
        # Import modules
        from app.config import Config
        from app.auth import AuthManager
        from app.production_provider import ProductionDataProvider
        from app.guardrails import require, fail_fast, create_provenance_data, emit_provenance
        import asyncio
        from datetime import datetime
        
        print(f"[DEBUG] production_calc_levels: symbol={symbol}, date={date}, format={format}")
        
        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            fail_fast("E-INVALID-DATE", f"Invalid date format: {date}. Use YYYY-MM-DD")
        
        async def calculate_with_real_data():
            # Initialize configuration and provider
            config = Config()
            auth_manager = AuthManager(config)
            provider = ProductionDataProvider(config, auth_manager)
            
            # Pre-flight check
            print("[DEBUG] Running pre-flight checks...")
            preflight_result = await provider.preflight_check()
            print(f"[DEBUG] Pre-flight result: {preflight_result}")
            
            # Get previous trading session OHLC for pivot calculations
            print(f"[DEBUG] Fetching daily OHLC for {symbol}")
            
            # This will fail until real historical API is implemented
            try:
                ohlc_data = await provider.get_daily_ohlc(symbol, target_date)
                require(ohlc_data is not None, "E-NODATA-DAILY", f"No daily OHLC for {symbol} on {target_date}")
                
                # Extract OHLC values
                H = ohlc_data.high
                L = ohlc_data.low
                C = ohlc_data.close
                
            except SystemExit as e:
                if "E-NODATA-DAILY" in str(e) or "E-STUB-PATH" in str(e):
                    # This is expected until real historical API is implemented
                    print(f"[DEBUG] {e}")
                    print("[DEBUG] Historical API not yet implemented - this is expected")
                    print("[DEBUG] In production, this would require real Schwab historical API")
                    raise  # Re-raise to fail the command
                else:
                    raise
            
            # Get intraday bars for true VWAP calculation
            print(f"[DEBUG] Fetching intraday bars for {symbol}")
            try:
                intraday_bars = await provider.get_intraday_bars(symbol, target_date)
                
                # Calculate true VWAP from intraday bars
                vwap_val = provider.calculate_true_vwap(intraday_bars)
                vwap_method = "intraday_true" if vwap_val is not None else "unavailable"
                
            except SystemExit as e:
                if "E-NODATA-INTRADAY" in str(e) or "E-STUB-PATH" in str(e):
                    print(f"[DEBUG] {e}")
                    print("[DEBUG] Intraday API not yet implemented")
                    vwap_val = None
                    vwap_method = "unavailable"
                else:
                    raise
            
            # Calculate pivot levels
            pivot = (H + L + C) / 3.0
            r1 = 2 * pivot - L
            s1 = 2 * pivot - H
            
            # Create provenance data
            session_info = provider.create_session_info(target_date)
            provenance = create_provenance_data(
                provider="schwab",
                is_synthetic=False,
                vwap_method=vwap_method,
                provider_request_id=provider.request_id,
                source_session=session_info
            )
            
            return r1, s1, vwap_val, pivot, provenance
        
        # Run calculation
        r1, s1, vwap, pivot, provenance = asyncio.run(calculate_with_real_data())
        
        # Output in requested format with mandatory provenance
        if format.lower() == "ai-block":
            print("[AI_DATA_BLOCK_START]")
            print(f"R1: {r1:.4f}")
            print(f"S1: {s1:.4f}")
            vwap_str = f"{vwap:.4f}" if vwap is not None else "N/A"
            print(f"VWAP: {vwap_str}")
            print("[AI_DATA_BLOCK_END]")
            
            # Emit provenance to STDERR for AI-block format
            emit_provenance("ai-block", **provenance)
            
        elif format.lower() == "json":
            import json
            output = {
                "symbol": symbol,
                "date": date,
                "levels": {
                    "R1": r1,
                    "S1": s1,
                    "VWAP": vwap,
                    "pivot": pivot
                },
                "provenance": provenance
            }
            print(json.dumps(output, indent=2, default=str))
            
        elif format.lower() == "csv":
            print("symbol,date,R1,S1,VWAP,pivot,data_source,is_synthetic,vwap_method")
            vwap_str = f"{vwap:.4f}" if vwap is not None else "N/A"
            print(f"{symbol},{date},{r1:.4f},{s1:.4f},{vwap_str},{pivot:.4f},"
                  f"{provenance['data_source']},{provenance['is_synthetic']},{provenance['vwap_method']}")
        else:
            fail_fast("E-INVALID-FORMAT", f"Unknown format: {format}")
        
        # Exit with non-zero code if VWAP is not available (single-date mode)
        if vwap is None:
            print(f"E-VWAP-UNAVAILABLE: VWAP data not available for {symbol} on {date}", file=sys.stderr)
            sys.exit(1)
            
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] Calculation failed: {e}")
        fail_fast("E-CALC-FAILED", f"Calculation failed: {e}")

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
    
    # Calc-levels command
    calc_parser = subparsers.add_parser("calc-levels", help="Calculate R1, S1, VWAP for a symbol/date")
    calc_parser.add_argument("--symbol", required=True, help="Symbol (e.g., AAPL, NQ)")
    calc_parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    calc_parser.add_argument("--format", default="ai-block", choices=["ai-block", "json", "csv"],
                            help="Output format")
    
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
        # Check authentication before starting server
        if not check_authentication():
            print("Server startup cancelled - authentication required")
            sys.exit(1)
        start_server(args.host, args.port, args.debug)
    elif args.command == "health":
        run_health_check()
    elif args.command == "auth":
        run_auth_flow()
    elif args.command == "export":
        export_data(args.symbol, args.type, args.format)
    elif args.command == "calc-levels":
        calc_levels(args.symbol, args.date, args.format)
    else:
        # Default to server - but check auth first
        print("No command specified, starting server...")
        if not check_authentication():
            print("Server startup cancelled - authentication required")
            sys.exit(1)
        start_server()

if __name__ == "__main__":
    main()
