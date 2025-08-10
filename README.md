# Schwab Data Exporter — TO1 (Credential & OAuth Foundation)

This MVP implements **credential management**, **callback hygiene**, **runtime orchestration**, and **OAuth scaffolding**
for the Charles Schwab Trader API — aligned with the approved Task Order #1 (TO1).

> ⚠️ This project **does not** call Schwab endpoints yet. OAuth endpoints and scopes are parameterized in `config.toml`.
> Fill them in once you create the app on the Schwab Developer Portal and register your **Redirect URI** verbatim.

A comprehensive financial data analysis and processing application built with Python, Flask, and modern async patterns.

## Features

- **Real-time Data Collection**: Quotes, historical data, options, and time & sales
- **Multiple Data Sources**: Support for Polygon, Alpha Vantage, IEX, and other providers
- **OAuth Authentication**: Secure API access with token management
- **Data Validation**: Comprehensive schema validation and data integrity checks
- **Parquet Storage**: Efficient data storage with compression and metadata
- **Health Monitoring**: Built-in health checks and system monitoring
- **RESTful API**: Flask-based web server with callback endpoints
- **Async Processing**: High-performance async data processing
- **Comprehensive Logging**: Structured logging with rotation and performance tracking
- **Metrics Exporters Demo**: Synthetic demo exporters wire IV metrics, Put/Call ratios, and bid/ask trade classification for rapid integration (replace synthetic data with live provider fetches).

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Git (for cloning the repository)

### Installation

1. **Clone the repository**:
   
   ```bash
   git clone <repository-url>
   cd trade-analyst
   ```

2. **Run the setup script**:
   
   **Windows**:
   
   ```cmd
   start.bat
   ```
   
   **Linux/macOS**:
   
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
   
   Or use Python directly:
   
   ```bash
   python start.py setup
   python start.py install
   ```

3. **Configure the application**:
   
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Start the application**:
   
   ```bash
   python start.py server
   ```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Authentication
OAUTH_CLIENT_ID=your_oauth_client_id
OAUTH_CLIENT_SECRET=your_oauth_client_secret

# Data Sources
POLYGON_API_KEY=your_polygon_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
IEX_API_KEY=your_iex_api_key

# Application
APP_ENVIRONMENT=development
APP_DEBUG=false
FLASK_HOST=localhost
FLASK_PORT=8080
```

### Configuration File

Edit `config.toml` to customize application behavior:

```toml
 
[app]
version = "1.0.0"
environment = "development"

[logging]
level = "INFO"
file_path = "logs/app.log"

[storage]
base_path = "data"
format = "parquet"
compression = "gzip"
```

## Usage

### Command Line Interface

The application provides a comprehensive CLI:

```bash
# Start the web server
python start.py server --host localhost --port 8080

# Run health checks
python start.py health

# Authenticate with OAuth
python start.py auth

# Export data
python start.py export --symbol AAPL --type historical --format csv

# Install dependencies
python start.py install

# Setup environment
python start.py setup
```

### Web Interface

Once the server is running, access:

- **Health Check**: `http://localhost:8080/health`
- **OAuth Callback**: `http://localhost:8080/callback`

### Python API

```python
from app.quotes import QuotesInterface
from app.historical import HistoricalInterface
from app.config import Config

# Initialize configuration
config = Config("config.toml")

# Create data interfaces
quotes = QuotesInterface(config)
historical = HistoricalInterface(config)

# Fetch data
quote_data = await quotes.get_quote("AAPL")
ohlc_data = await historical.get_historical("AAPL", "1D", "2024-01-01", "2024-01-31")
```

### Metrics & Time & Sales Exporter Demo

Synthetic demo exporters show how to hook metrics prior to wiring real Schwab endpoints:

PowerShell:
 
```powershell
python -c "import json; from app.config import load_config; from app.exporters import build_options_stats, build_timesales_metrics; cfg=load_config(); print(json.dumps(build_options_stats(cfg),indent=2)); print(json.dumps(build_timesales_metrics(cfg),indent=2))"
```

Outputs include keys like `iv_rank`, `iv_percentile`, `put_call_ratio`, and `% at bid/ask/mid` metrics with a confidence summary.

Replace synthetic data by supplying real DataFrames:
 
```python
stats = build_options_stats(cfg, iv_series=real_iv_series, chain=real_option_chain_df)
ts_metrics = build_timesales_metrics(cfg, trades=real_trades_df, quotes=real_quotes_df)
```text

These can then be merged into your parquet writers / downstream analytics.

## Project Structure

 
```text
trade-analyst/
├── app/
│   ├── __init__.py
│   ├── main.py              # CLI interface
│   ├── appstart.py          # Application orchestration
│   ├── auth.py              # OAuth authentication
│   ├── config.py            # Configuration management
│   ├── quotes.py            # Quotes data interface
│   ├── historical.py        # Historical data interface
│   ├── options.py           # Options data interface
│   ├── timesales.py         # Time & sales interface
│   ├── server.py            # Flask web server
│   ├── systeminit.py        # System initialization
│   ├── healthcheck.py       # Health monitoring
│   ├── callback_checker.py  # OAuth callbacks
│   ├── error_handlers.py    # Error handling
│   ├── logging.py           # Logging configuration
│   ├── writers.py           # Data writers
│   ├── schemas/             # Data schemas
│   │   ├── __init__.py
│   │   ├── quotes.py
│   │   ├── ohlc.py
│   │   ├── options.py
│   │   └── timesales.py
│   └── utils/               # Utility modules
│       ├── __init__.py
│       ├── validators.py    # Data validation
│       ├── types.py         # Type definitions
│       ├── hashing.py       # Content hashing
│       └── timeutils.py     # Time utilities
├── tests/
│   ├── test_validators.py   # Validator tests
│   └── test_schema_lint.py  # Schema tests
├── data/                    # Data storage
├── logs/                    # Application logs
├── tokens/                  # OAuth tokens
├── config.toml              # Main configuration
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── start.py                 # Main startup script
├── start.bat               # Windows startup script
├── start.sh                # Unix startup script
├── Dockerfile              # Docker configuration
└── README.md               # This file
 
```text

## Data Interfaces

### Quotes Interface

```python
from app.quotes import QuotesInterface

quotes = QuotesInterface(config)
quote_data = await quotes.get_quote("AAPL")
batch_data = await quotes.get_quotes(["AAPL", "MSFT", "GOOGL"])
```

### Historical Interface

```python
from app.historical import HistoricalInterface

historical = HistoricalInterface(config)
daily_data = await historical.get_historical("AAPL", "1D", "2024-01-01", "2024-01-31")
minute_data = await historical.get_historical("AAPL", "1m", "2024-01-01", "2024-01-01")
```

### Options Interface

```python
from app.options import OptionsInterface

options = OptionsInterface(config)
option_chain = await options.get_option_chain("AAPL", "2024-01-19")
option_quote = await options.get_option_quote("AAPL240119C00150000")
```

### Time & Sales Interface

```python
from app.timesales import TimeSalesInterface

timesales = TimeSalesInterface(config)
trades = await timesales.get_timesales("AAPL", "2024-01-01T09:30:00", "2024-01-01T16:00:00")
```

## Data Storage

The application uses Parquet format for efficient data storage:

- **Compression**: GZIP compression for space efficiency
- **Partitioning**: Data partitioned by symbol, date, or expiration
- **Metadata**: Rich metadata including data source and processing info
- **Integrity**: Content hashing for data integrity verification

## Authentication

OAuth 2.0 flow with automatic token refresh:

1. **Initial Authentication**: Run `python start.py auth`
2. **Automatic Refresh**: Tokens refreshed automatically before expiry
3. **Secure Storage**: Tokens stored securely in `tokens/` directory

### Token Encryption & Key Management

Tokens are encrypted at rest using Fernet. The key is sourced from the `TOKEN_ENC_KEY` environment variable.

Token handling policy:

1. Provide a 32-byte urlsafe base64 key (Fernet.generate_key()).
2. Rotate keys by:
   - Decrypting existing cache with old key.
   - Re-encrypting and writing with new key before redeploy.
3. In dev, if `TOKEN_ENC_KEY` is absent an ephemeral key is generated (tokens will not persist across restarts).
4. Never commit keys. Use secret stores (GitHub Actions secrets, environment manager, Key Vault, etc.).
5. Plan rotation cadence (e.g., quarterly or on incident) and document rotation execution in change log.

Rotation helper (conceptual): maintain old key available until next successful refresh cycle then remove.

## Monitoring & Health Checks

Built-in health monitoring:

- **System Health**: Memory, disk space, response times
- **Data Source Health**: API connectivity and rate limits
- **Authentication Health**: Token validity and refresh status
- **Storage Health**: Disk space and write permissions

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test files
pytest tests/test_validators.py
pytest tests/test_schema_lint.py
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/

# Sort imports
isort app/ tests/
```

### Adding New Data Sources

1. Create a new interface class inheriting from base patterns
2. Add configuration in `config.toml`
3. Implement required methods for data fetching
4. Add authentication if required
5. Update health checks

## Docker Deployment

```bash
# Build image
docker build -t trade-analyst .

# Run container
docker run -d \
  --name trade-analyst \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  trade-analyst

# Check logs
docker logs trade-analyst

# Health check
curl http://localhost:8080/health
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Run `python start.py install` to install dependencies
2. **Configuration Errors**: Check `config.toml` and `.env` files
3. **Authentication Errors**: Verify API keys and run `python start.py auth`
4. **Storage Errors**: Check disk space and permissions in `data/` directory

### Logging

Logs are written to:

- **Console**: Real-time application output
- **File**: `logs/app.log` with rotation
- **Structured**: JSON format for easy parsing

### Performance

For optimal performance:

- Use async interfaces for concurrent operations
- Enable caching in configuration
- Monitor memory usage with health checks
- Use appropriate batch sizes for data processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks
5. Submit a pull request

## License

[Your License Here]

## Support

For support and questions:

- **Documentation**: Check this README and inline comments
- **Issues**: Use the GitHub issue tracker
- **Health Checks**: Run `python start.py health` for diagnostics
