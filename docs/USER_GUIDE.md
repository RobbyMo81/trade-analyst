# Trade Analyst User Guide

Welcome to the Trade Analyst platform! This comprehensive guide will walk you through everything you need to know to successfully use the application for financial data collection and analysis.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication Setup](#authentication-setup)
3. [Basic Usage](#basic-usage)
4. [Advanced Features](#advanced-features)
5. [Troubleshooting](#troubleshooting)
6. [API Reference](#api-reference)
7. [Best Practices](#best-practices)

## Getting Started

### System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 500MB free space for application and data
- **Network**: Internet connection for API access

### Installation Steps

#### Step 1: Download and Setup

```bash
# Clone the repository
git clone https://github.com/RobbyMo81/trade-analyst.git
cd trade-analyst

# Install dependencies
python start.py install

# Setup environment
python start.py setup
```

#### Step 2: Verify Installation

```bash
# Check that everything is working
python -m app.main healthcheck
```

You should see output like:
```
✅ All health checks passed
  ✅ system_resources: healthy
  ✅ disk_space: healthy
  ✅ log_files: healthy
  ✅ data_directories: healthy
  ✅ api_connectivity: healthy
  ✅ authentication: healthy
  ✅ database_connectivity: healthy
  ✅ redirect_uri: healthy
  ✅ external_dependencies: healthy
  ✅ schwab_market_server: healthy
```

## Authentication Setup

### Prerequisites

1. **Charles Schwab Developer Account**
   - Visit [Schwab Developer Portal](https://developer.schwab.com/)
   - Create a developer account
   - Register a new application

2. **Application Registration**
   - Choose "Web Application" type
   - Set redirect URI to: `http://127.0.0.1:5000/callback`
   - Note your App Key and Secret Key

### Configuration

#### Step 1: Environment Variables

Copy the environment template and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` file:
```bash
# Required: Your Schwab API credentials
OAUTH_CLIENT_ID=your_schwab_app_key_here
OAUTH_CLIENT_SECRET=your_schwab_secret_key_here

# Optional: Token encryption (recommended for production)
TOKEN_ENC_KEY=your_32_byte_base64_key_here

# Optional: Application settings
APP_ENVIRONMENT=development
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

#### Step 2: Configuration File

The `config.toml` file contains application settings. Key sections:

```toml
[auth]
# OAuth endpoints - usually don't need to change these
authorize_url = "https://api.schwabapi.com/v1/oauth/authorize"
token_url = "https://api.schwabapi.com/v1/oauth/token"
base_url = "https://api.schwabapi.com/v1"
scope = "quotes.read historical.read options.read timesales.read"

# PKCE security settings
pkce = true
pkce_method = "S256"

[env.dev]
# Development environment settings
redirect_uri = "http://127.0.0.1:5000/callback"
host = "127.0.0.1"
port = 5000

[providers.schwab]
# Schwab-specific settings
marketdata_base = "https://api.schwabapi.com/marketdata/v1"
```

#### Step 3: Initial Authentication

```bash
# Start the callback server (in one terminal)
python -m app.main serve-callback

# Initiate authentication (in another terminal)
python -m app.main auth-login
```

Follow the authentication flow:
1. The system will open your browser
2. Log in to your Schwab account
3. Authorize the application
4. The system will automatically save your tokens

## Basic Usage

### Getting Real-Time Quotes

#### Single Symbol

```bash
# Get quote for SPY
python ta.py quotes SPY
```

Output:
```json
{
  "records": [
    {
      "symbol": "SPY",
      "bid": 643.18,
      "ask": 643.4,
      "bid_size": 4,
      "ask_size": 1,
      "timestamp": "2025-08-16T04:01:05.247Z"
    }
  ],
  "validation": {
    "is_valid": true,
    "record_count": 1
  }
}
```

#### Multiple Symbols

```bash
# Get quotes for multiple stocks
python ta.py quotes SPY AAPL MSFT GOOGL
```

#### Futures Contracts

```bash
# Get futures quotes (automatic contract translation)
python ta.py quotes ES NQ
```

The system automatically translates:
- `ES` → `ESU25` (September 2025 E-mini S&P 500)
- `NQ` → `NQU25` (September 2025 E-mini NASDAQ-100)

### System Management

#### Health Monitoring

```bash
# Comprehensive health check
python -m app.main healthcheck

# Check application status
python -m app.main status
```

#### Token Management

```bash
# Check token status
python -m scripts.debug_token_cache --env dev

# Print raw access token (for debugging)
python -m scripts.print_access_token
```

#### Data Export

```bash
# Dry run export (test without actual data export)
python -m app.main export --dry-run --data-type quotes

# Export specific data type
python -m app.main export --data-type historical

# Export all data types
python -m app.main export
```

## Advanced Features

### Futures Contract Translation

The platform includes sophisticated futures contract translation with exchange calendar integration.

#### Supported Contracts

- **ES**: E-mini S&P 500 futures
- **NQ**: E-mini NASDAQ-100 futures

#### How It Works

1. **Root Symbol Recognition**: Detects ES or NQ symbols
2. **Expiry Calculation**: Uses exchange calendar for accurate expiry dates
3. **Holiday Awareness**: Adjusts for market holidays (Good Friday, etc.)
4. **Front Month Selection**: Selects nearest quarterly expiry after current date

#### Examples

```bash
# Input: ES (root symbol)
# Output: ESU25 (September 2025 contract)

# Input: NQ (root symbol)  
# Output: NQU25 (September 2025 contract)
```

#### Month Codes
- **H**: March
- **M**: June  
- **U**: September
- **Z**: December

### Exchange Calendar Features

The platform includes a comprehensive exchange calendar system:

- **Federal Holidays**: New Year's Day, Presidents Day, Good Friday, etc.
- **Market-Specific Holidays**: CME/CBOT specific closures
- **Business Day Calculation**: Accurate weekday/holiday validation
- **Expiry Adjustment**: When third Friday falls on holiday, moves to prior business day

### Custom Configuration

#### Provider Settings

```toml
[providers.schwab]
# Override default market data URL
marketdata_base = "https://api.schwabapi.com/marketdata/v1"

# Additional provider settings
timeout = 30
retry_attempts = 3
```

#### Logging Configuration

```toml
[logging]
level = "INFO"  # DEBUG, INFO, WARNING, ERROR
rotate_when = "midnight"
backup_count = 7
```

#### Runtime Settings

```toml
[runtime]
storage_root = "./data"
token_expiry_warning_minutes = 10
token_cache = "token_cache.json"
```

### API Programming Interface

#### Python Integration

```python
from app.config import Config
from app.providers.schwab import SchwabClient
from app.utils.futures import translate_root_to_front_month

# Initialize configuration
config = Config()

# Futures translation
contract_code = translate_root_to_front_month('ES')
print(f"ES translates to: {contract_code}")

# Direct API access
async def get_quotes():
    client = SchwabClient(config)
    quotes = await client.get_quotes(['SPY', 'AAPL'])
    return quotes
```

#### Custom Scripts

Create custom scripts in the `scripts/` directory:

```python
# scripts/my_custom_script.py
import asyncio
from app.config import Config
from app.providers.schwab import SchwabClient

async def main():
    config = Config()
    client = SchwabClient(config)
    
    symbols = ['SPY', 'QQQ', 'IWM']
    quotes = await client.get_quotes(symbols)
    
    for quote in quotes:
        print(f"{quote['symbol']}: ${quote['last']}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run with: `python -m scripts.my_custom_script`

## Troubleshooting

### Common Issues

#### 1. Authentication Problems

**Symptom**: "Authentication failed" or "Invalid credentials"

**Solutions**:
```bash
# Check token status
python -m scripts.debug_token_cache --env dev

# Verify configuration
python -m app.main status

# Re-authenticate
python -m app.main auth-login
```

**Common Causes**:
- Incorrect App Key or Secret Key in `.env`
- Expired tokens (auto-refresh should handle this)
- Incorrect redirect URI configuration

#### 2. Network Connectivity Issues

**Symptom**: "API connectivity" health check fails

**Solutions**:
```bash
# Test network connectivity
python -m app.main healthcheck

# Check firewall settings
# Ensure ports 80, 443, and 5000 are open

# Test direct API access
python -m scripts.aio_probe
```

#### 3. Quote Retrieval Errors

**Symptom**: "No quotes found" or HTTP 404 errors

**Solutions**:
```bash
# Verify symbol format
python ta.py quotes SPY  # Correct
python ta.py quotes spy  # May fail (case sensitive)

# Check market hours
# Some symbols only trade during market hours

# Test with known symbols
python ta.py quotes SPY QQQ IWM
```

#### 4. Futures Translation Issues

**Symptom**: Futures symbols not translating correctly

**Debug Steps**:
```bash
# Test translation manually
python -c "from app.utils.futures import translate_root_to_front_month; print(translate_root_to_front_month('ES'))"

# Check exchange calendar
python -c "from app.utils.exchange_calendar import get_contract_expiry_date; import datetime; print(get_contract_expiry_date('ES', 2025, 9))"

# Run futures tests
python -m pytest tests/test_futures_translator.py -v
```

### Log Analysis

#### Log Locations
- **Console Output**: Real-time application logs
- **File Logs**: 
  - `logs/trade-analyst.log` - Main application log
  - `logs/trade-analyst-error.log` - Error-specific log
  - `logs/access.log` - API access log
  - `logs/data-collection.log` - Data processing log

#### Common Log Messages

```bash
# Successful authentication
"Authentication tokens available"

# API connectivity
"Testing connection to Schwab API"

# Quote processing
"Quote SPY status 200"
"Batch request for 3 symbols"

# Futures translation
"Translating ES to ESU25"

# Errors
"ERROR - No API providers are available"
"WARNING - Authentication token expires soon"
```

### Performance Optimization

#### Memory Usage
```bash
# Monitor memory usage
python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

#### Response Times
- **Health Checks**: Should complete in < 2 seconds
- **Quote Retrieval**: Typically 15-20 seconds (provider dependent)
- **System Initialization**: < 1 second

#### Optimization Tips
1. **Batch Requests**: Use multiple symbols in single request
2. **Connection Reuse**: The system automatically reuses connections
3. **Token Caching**: Tokens are cached to avoid repeated authentication
4. **Rate Limiting**: Built-in rate limiting prevents API overuse

## API Reference

### Command Line Interface

#### Core Commands

```bash
# Application management
python -m app.main healthcheck           # Run health checks
python -m app.main status               # Show application status
python -m app.main serve-callback       # Start OAuth callback server

# Authentication
python -m app.main auth-login           # Initiate OAuth login

# Data operations
python -m app.main export              # Export data
python ta.py quotes <symbols>          # Get real-time quotes
```

#### Script Utilities

```bash
# Token management
python -m scripts.debug_token_cache    # Check token status
python -m scripts.print_access_token   # Display access token

# Testing utilities
python -m scripts.aio_probe           # Test API connectivity
python -m scripts.callback_server     # Manual callback server
```

### Configuration Reference

#### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OAUTH_CLIENT_ID` | Yes | Schwab App Key | `your_app_key` |
| `OAUTH_CLIENT_SECRET` | Yes | Schwab Secret Key | `your_secret` |
| `TOKEN_ENC_KEY` | No | Token encryption key | `base64_key` |
| `APP_ENVIRONMENT` | No | Environment name | `development` |
| `FLASK_HOST` | No | Callback server host | `127.0.0.1` |
| `FLASK_PORT` | No | Callback server port | `5000` |

#### Configuration Sections

| Section | Purpose | Key Settings |
|---------|---------|--------------|
| `[auth]` | Authentication settings | `authorize_url`, `token_url`, `scope` |
| `[env.dev]` | Development environment | `redirect_uri`, `host`, `port` |
| `[env.prod]` | Production environment | `redirect_uri`, `host`, `port` |
| `[providers.schwab]` | Schwab-specific settings | `marketdata_base` |
| `[logging]` | Logging configuration | `level`, `rotate_when` |
| `[runtime]` | Runtime settings | `storage_root`, `token_cache` |

## Best Practices

### Security

#### Token Management
1. **Use Encryption**: Always set `TOKEN_ENC_KEY` in production
2. **Secure Storage**: Never commit tokens to version control
3. **Key Rotation**: Rotate encryption keys quarterly
4. **Access Control**: Limit access to token files

#### API Usage
1. **Rate Limiting**: Respect API rate limits (built-in protection)
2. **Error Handling**: Always check response status
3. **Token Refresh**: Let the system handle automatic refresh
4. **Secure Connections**: Always use HTTPS endpoints

### Performance

#### Efficient Data Retrieval
```bash
# Good: Batch requests
python ta.py quotes SPY AAPL MSFT GOOGL

# Less efficient: Individual requests
python ta.py quotes SPY
python ta.py quotes AAPL
python ta.py quotes MSFT
python ta.py quotes GOOGL
```

#### Monitoring
1. **Regular Health Checks**: Run weekly health checks
2. **Log Monitoring**: Monitor error logs for issues
3. **Token Expiry**: Monitor token expiry warnings
4. **Disk Space**: Monitor data directory growth

### Development

#### Testing
```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest tests/test_futures_translator.py
python -m pytest tests/test_exchange_calendar.py

# Run with coverage
python -m pytest --cov=app tests/
```

#### Code Quality
```bash
# Format code
black app/ scripts/ tests/

# Check style
flake8 app/ scripts/ tests/

# Type checking
mypy app/
```

### Production Deployment

#### Environment Setup
1. **Use Production Configuration**: Set `APP_ENVIRONMENT=production`
2. **Secure Redirect URI**: Use HTTPS for production redirect URIs
3. **Log Rotation**: Configure proper log rotation
4. **Monitoring**: Set up application monitoring
5. **Backup**: Regular backup of configuration and tokens

#### Scaling Considerations
1. **Connection Pooling**: Built-in connection reuse
2. **Async Processing**: Leverages Python asyncio for performance
3. **Resource Monitoring**: Built-in system resource monitoring
4. **Error Recovery**: Comprehensive error handling and recovery

---

## Support

### Getting Help

1. **Documentation**: Start with this user guide and README
2. **Health Checks**: Run `python -m app.main healthcheck` for diagnostics  
3. **Logs**: Check application logs for error details
4. **Testing**: Run test suites to verify functionality

### Reporting Issues

When reporting issues, please include:
1. **System Information**: OS, Python version
2. **Error Messages**: Complete error messages from logs
3. **Configuration**: Sanitized configuration (remove credentials)
4. **Steps to Reproduce**: Detailed reproduction steps
5. **Health Check Output**: Results of health check command

### Additional Resources

- **Charles Schwab API Documentation**: [developer.schwab.com](https://developer.schwab.com/)
- **Python AsyncIO Documentation**: [docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
- **OAuth 2.0 Specification**: [oauth.net/2/](https://oauth.net/2/)

---

**Version**: 1.0  
**Last Updated**: August 15, 2025  
**Status**: Production Ready ✅
