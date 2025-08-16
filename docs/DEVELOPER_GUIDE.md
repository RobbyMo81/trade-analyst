# Trade Analyst Developer Guide

This guide provides comprehensive information for developers working on the Trade Analyst platform, including architecture details, development workflows, testing procedures, and extension guidelines.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Environment](#development-environment)
3. [Code Structure](#code-structure)
4. [Testing Framework](#testing-framework)
5. [API Development](#api-development)
6. [Extension Development](#extension-development)
7. [Deployment Guide](#deployment-guide)

## Architecture Overview

### System Architecture

The Trade Analyst platform follows a modular, layered architecture designed for scalability and maintainability.

```
┌─────────────────────────────────────────────────────────┐
│                  User Interface Layer                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ CLI (ta.py) │  │ REST API    │  │ Web UI      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │AppOrchestra │  │HealthChecker│  │SystemInitial│     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │AuthManager  │  │ SchwabClient│  │ExchangeCalendar   │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Providers   │  │ Writers     │  │ Validators  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │Config Mgmt  │  │ Logging     │  │Token Storage│     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Configuration Management (`app/config.py`)
- TOML-based configuration with environment variable overrides
- Support for multiple environments (dev, prod)
- Secure credential management with encrypted storage
- Provider-specific configuration sections

#### 2. Authentication System (`app/auth.py`)
- OAuth 2.0 + PKCE implementation
- Automatic token refresh with expiry handling
- Encrypted token storage using Fernet
- Support for multiple redirect URIs

#### 3. Provider Abstraction (`app/providers/`)
- Abstract base classes for data providers
- Schwab API client with comprehensive error handling
- Response normalization and validation
- Rate limiting and connection pooling

#### 4. Data Processing Pipeline
- Async processing using aiohttp for HTTP requests
- Schema validation using custom validators
- Futures contract translation with exchange calendar
- Quote normalization and enrichment

### Key Design Patterns

#### 1. Dependency Injection
```python
class SchwabClient:
    def __init__(self, config: Config, auth_manager: AuthManager = None):
        self.config = config
        self.auth_manager = auth_manager or AuthManager(config)
```

#### 2. Factory Pattern
```python
def create_provider(provider_name: str, config: Config):
    if provider_name == 'schwab':
        return SchwabClient(config)
    raise ValueError(f"Unknown provider: {provider_name}")
```

#### 3. Strategy Pattern
```python
class ExportStrategy:
    def export(self, data): pass

class CSVExporter(ExportStrategy):
    def export(self, data):
        # CSV export implementation
        pass

class ParquetExporter(ExportStrategy):
    def export(self, data):
        # Parquet export implementation
        pass
```

## Development Environment

### Setup

#### Prerequisites
```bash
# Required tools
python --version  # 3.8+
git --version     # Any recent version
pip --version     # Latest recommended
```

#### Clone and Setup
```bash
git clone https://github.com/RobbyMo81/trade-analyst.git
cd trade-analyst

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\\Scripts\\activate   # Windows

# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .

# Setup pre-commit hooks
pre-commit install
```

#### Environment Configuration
```bash
# Copy development environment template
cp .env.example .env

# Set development-specific variables
echo "APP_ENVIRONMENT=development" >> .env
echo "FLASK_DEBUG=true" >> .env
```

### Development Workflow

#### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/new-provider

# Make changes
# ... code changes ...

# Run tests
python -m pytest

# Run quality checks
black app/ tests/
flake8 app/ tests/
mypy app/

# Commit changes
git add .
git commit -m "feat: add new data provider"
```

#### 2. Testing Workflow
```bash
# Run all tests
python -m pytest

# Run specific test suite
python -m pytest tests/test_futures_translator.py

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run integration tests
python -m pytest tests/ -m integration
```

#### 3. Quality Assurance
```bash
# Code formatting
black app/ tests/ scripts/

# Import sorting
isort app/ tests/ scripts/

# Linting
flake8 app/ tests/ scripts/

# Type checking
mypy app/

# Security scanning
bandit -r app/

# Dependency checking
safety check
pip-audit
```

## Code Structure

### Directory Layout

```
trade-analyst/
├── app/                        # Main application package
│   ├── __init__.py
│   ├── main.py                # CLI entry point
│   ├── appstart.py           # Application orchestrator
│   ├── config.py             # Configuration management
│   ├── auth.py               # Authentication system
│   ├── healthcheck.py        # Health monitoring
│   ├── systeminit.py         # System initialization
│   ├── server.py             # Flask web server
│   ├── logging.py            # Logging configuration
│   ├── common/               # Common utilities
│   │   ├── __init__.py
│   │   ├── types.py          # Type definitions
│   │   └── exceptions.py     # Custom exceptions
│   ├── providers/            # Data provider implementations
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base classes
│   │   ├── schwab.py         # Schwab API client
│   │   └── mock.py           # Mock provider for testing
│   ├── schemas/              # Data validation schemas
│   │   ├── __init__.py
│   │   ├── quotes.py         # Quote data schemas
│   │   ├── historical.py     # Historical data schemas
│   │   └── options.py        # Options data schemas
│   ├── utils/                # Utility modules
│   │   ├── __init__.py
│   │   ├── futures.py        # Futures contract utilities
│   │   ├── exchange_calendar.py # Exchange calendar
│   │   ├── validators.py     # Data validators
│   │   └── timeutils.py      # Time handling utilities
│   └── exporters/            # Data export modules
│       ├── __init__.py
│       ├── base.py           # Export base classes
│       ├── csv.py            # CSV exporter
│       └── parquet.py        # Parquet exporter
├── tests/                    # Test suite
│   ├── conftest.py          # Test configuration
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── fixtures/            # Test fixtures
├── scripts/                 # Utility scripts
│   ├── debug_token_cache.py # Token debugging
│   ├── print_access_token.py # Token display
│   └── aio_probe.py         # API connectivity testing
├── docs/                    # Documentation
│   ├── USER_GUIDE.md        # User documentation
│   ├── API_REFERENCE.md     # API documentation
│   └── DEPLOYMENT.md        # Deployment guide
├── config.toml              # Main configuration
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── pyproject.toml           # Project metadata
```

### Coding Standards

#### Python Style Guide

We follow PEP 8 with the following additions:

```python
# Line length: 88 characters (Black default)
# Use type hints for all public functions
def get_quotes(symbols: List[str]) -> Dict[str, Any]:
    """Get quotes for multiple symbols."""
    pass

# Use dataclasses for data structures
from dataclasses import dataclass

@dataclass
class QuoteData:
    symbol: str
    price: float
    timestamp: datetime
    
# Use async/await for I/O operations
async def fetch_data(url: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Use context managers for resources
from contextlib import asynccontextmanager

@asynccontextmanager
async def database_connection():
    conn = await create_connection()
    try:
        yield conn
    finally:
        await conn.close()
```

#### Error Handling

```python
# Use custom exceptions
class TradeAnalystError(Exception):
    """Base exception for Trade Analyst."""
    pass

class AuthenticationError(TradeAnalystError):
    """Authentication-related errors."""
    pass

class ProviderError(TradeAnalystError):
    """Data provider errors."""
    pass

# Comprehensive error handling
async def get_quote(symbol: str) -> QuoteData:
    try:
        response = await self.client.get(f"/quotes/{symbol}")
        response.raise_for_status()
        return QuoteData.from_dict(await response.json())
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching quote for {symbol}: {e}")
        raise ProviderError(f"Failed to fetch quote: {e}")
    except KeyError as e:
        logger.error(f"Invalid response format for {symbol}: {e}")
        raise ProviderError(f"Invalid response format: {e}")
```

#### Logging Standards

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General information about operation")
logger.warning("Something unexpected happened")
logger.error("Error occurred, operation failed")
logger.critical("Serious error, program may abort")

# Include context in log messages
logger.info(f"Fetching quotes for {len(symbols)} symbols")
logger.error(f"Authentication failed for user {user_id}: {error}")

# Use structured logging for complex data
logger.info("Quote retrieved", extra={
    'symbol': 'SPY',
    'price': 643.18,
    'timestamp': datetime.utcnow().isoformat()
})
```

## Testing Framework

### Test Organization

#### Unit Tests (`tests/unit/`)
```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.providers.schwab import SchwabClient

class TestSchwabClient:
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.get_schwab_market_base.return_value = "https://api.schwab.com"
        return config
    
    @pytest.fixture
    def mock_auth_manager(self):
        auth = AsyncMock()
        auth.get_access_token.return_value = "mock_token"
        return auth
    
    @pytest.fixture
    def client(self, mock_config, mock_auth_manager):
        return SchwabClient(mock_config, mock_auth_manager)
    
    @pytest.mark.asyncio
    async def test_get_quotes_success(self, client, aioresponses):
        # Setup mock response
        aioresponses.get(
            "https://api.schwab.com/quotes?symbols=SPY",
            payload={"SPY": {"bid": 643.18, "ask": 643.40}}
        )
        
        # Execute
        result = await client.get_quotes(["SPY"])
        
        # Assert
        assert len(result) == 1
        assert result[0]["symbol"] == "SPY"
        assert result[0]["bid"] == 643.18
```

#### Integration Tests (`tests/integration/`)
```python
@pytest.mark.integration
class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_end_to_end_quote_retrieval(self):
        """Test complete quote retrieval workflow."""
        config = Config("config.toml")
        orchestrator = AppOrchestrator(config)
        
        # Initialize system
        assert await orchestrator.startup(dry_run=True)
        
        # Test quote retrieval
        from ta import cmd_quotes
        result = await cmd_quotes(["SPY"])
        
        assert result["validation"]["is_valid"]
        assert len(result["records"]) > 0
```

#### Test Utilities
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import Mock

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'auth': {'token_url': 'https://mock.api.com/token'},
        'providers': {'schwab': {'marketdata_base': 'https://mock.api.com'}}
    }.get(key, default)
    return config

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Custom markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
```

### Running Tests

#### Test Commands
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test
pytest tests/unit/test_schwab_client.py::TestSchwabClient::test_get_quotes

# Run tests matching pattern
pytest -k "test_quote"

# Run tests with specific marker
pytest -m integration

# Run tests in parallel
pytest -n auto
```

#### Test Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --disable-warnings
    --tb=short
    -ra
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    smoke: Smoke tests
asyncio_mode = auto
```

### Mock Strategies

#### HTTP Mocking
```python
import aioresponses

@pytest.fixture
def mock_aiohttp():
    with aioresponses.aioresponses() as m:
        yield m

async def test_api_call(mock_aiohttp):
    mock_aiohttp.get(
        "https://api.schwab.com/quotes?symbols=SPY",
        payload={"SPY": {"last": 643.18}},
        status=200
    )
    
    result = await client.get_quotes(["SPY"])
    assert result[0]["last"] == 643.18
```

#### Database Mocking
```python
@pytest.fixture
def mock_database():
    with patch('app.database.get_connection') as mock:
        mock_conn = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_conn
        yield mock_conn

async def test_database_operation(mock_database):
    mock_database.fetch.return_value = [{"id": 1, "symbol": "SPY"}]
    
    result = await service.get_symbols()
    assert len(result) == 1
    assert result[0]["symbol"] == "SPY"
```

## API Development

### Adding New Data Providers

#### 1. Create Provider Interface
```python
# app/providers/new_provider.py
from .base import BaseProvider
from typing import List, Dict, Any

class NewProvider(BaseProvider):
    """Provider implementation for NewProvider API."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.base_url = config.get_provider_config("newprovider", "base_url")
        self.api_key = config.get_provider_config("newprovider", "api_key")
    
    async def get_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch quotes for given symbols."""
        url = f"{self.base_url}/quotes"
        params = {"symbols": ",".join(symbols), "apikey": self.api_key}
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            return self._normalize_quotes(data)
    
    def _normalize_quotes(self, raw_data: Dict) -> List[Dict[str, Any]]:
        """Convert provider-specific format to standard format."""
        quotes = []
        for symbol, quote_data in raw_data.items():
            quotes.append({
                "symbol": symbol,
                "bid": quote_data.get("bid_price"),
                "ask": quote_data.get("ask_price"),
                "last": quote_data.get("last_price"),
                "timestamp": quote_data.get("timestamp")
            })
        return quotes
```

#### 2. Add Configuration Support
```toml
# config.toml
[providers.newprovider]
base_url = "https://api.newprovider.com/v1"
api_key = "${NEW_PROVIDER_API_KEY}"
timeout = 30
rate_limit = 100
```

#### 3. Register Provider
```python
# app/providers/__init__.py
from .schwab import SchwabClient
from .new_provider import NewProvider

PROVIDERS = {
    "schwab": SchwabClient,
    "newprovider": NewProvider,
}

def create_provider(provider_name: str, config: Config):
    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_name}")
    return PROVIDERS[provider_name](config)
```

#### 4. Add Tests
```python
# tests/unit/test_new_provider.py
import pytest
from app.providers.new_provider import NewProvider

class TestNewProvider:
    @pytest.fixture
    def provider(self, mock_config):
        return NewProvider(mock_config)
    
    @pytest.mark.asyncio
    async def test_get_quotes(self, provider, aioresponses):
        # Test implementation
        pass
```

### Extending Quote Processing

#### 1. Custom Quote Processor
```python
# app/processors/quote_processor.py
from typing import List, Dict, Any
from datetime import datetime

class QuoteProcessor:
    """Process and enrich quote data."""
    
    def __init__(self, config: Config):
        self.config = config
        self.enrichers = self._load_enrichers()
    
    async def process_quotes(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process quotes through enrichment pipeline."""
        processed = []
        
        for quote in quotes:
            # Validate quote data
            if not self._validate_quote(quote):
                continue
            
            # Enrich quote data
            enriched = await self._enrich_quote(quote)
            
            # Add processing metadata
            enriched["processed_at"] = datetime.utcnow().isoformat()
            enriched["processor_version"] = "1.0"
            
            processed.append(enriched)
        
        return processed
    
    def _validate_quote(self, quote: Dict[str, Any]) -> bool:
        """Validate quote data structure."""
        required_fields = ["symbol", "timestamp"]
        return all(field in quote for field in required_fields)
    
    async def _enrich_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich quote with additional data."""
        enriched = quote.copy()
        
        for enricher in self.enrichers:
            enriched = await enricher.enrich(enriched)
        
        return enriched
```

#### 2. Quote Enrichers
```python
# app/enrichers/futures_enricher.py
class FuturesEnricher:
    """Enrich futures quotes with contract information."""
    
    async def enrich(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        symbol = quote["symbol"]
        
        if self._is_futures_contract(symbol):
            quote["contract_info"] = {
                "root": self._extract_root(symbol),
                "expiry_month": self._extract_expiry_month(symbol),
                "expiry_year": self._extract_expiry_year(symbol),
                "days_to_expiry": self._calculate_days_to_expiry(symbol)
            }
        
        return quote
```

## Extension Development

### Plugin Architecture

#### 1. Plugin Interface
```python
# app/plugins/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class Plugin(ABC):
    """Base class for Trade Analyst plugins."""
    
    def __init__(self, config: Config):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data through the plugin."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass
```

#### 2. Example Plugin
```python
# plugins/technical_indicators.py
from app.plugins.base import Plugin
import pandas as pd

class TechnicalIndicatorsPlugin(Plugin):
    """Add technical indicators to quote data."""
    
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        self.window_size = self.config.get("technical_indicators", {}).get("window", 20)
        self.indicators = ["sma", "ema", "rsi"]
        return True
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add technical indicators to quote data."""
        if "historical_data" not in data:
            return data
        
        df = pd.DataFrame(data["historical_data"])
        
        # Calculate indicators
        if "sma" in self.indicators:
            df["sma"] = df["close"].rolling(window=self.window_size).mean()
        
        if "ema" in self.indicators:
            df["ema"] = df["close"].ewm(span=self.window_size).mean()
        
        if "rsi" in self.indicators:
            df["rsi"] = self._calculate_rsi(df["close"])
        
        data["historical_data"] = df.to_dict("records")
        data["indicators_added"] = self.indicators
        
        return data
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
```

#### 3. Plugin Manager
```python
# app/plugins/manager.py
import importlib
from typing import List, Dict, Any

class PluginManager:
    """Manage Trade Analyst plugins."""
    
    def __init__(self, config: Config):
        self.config = config
        self.plugins: List[Plugin] = []
    
    async def load_plugins(self) -> None:
        """Load configured plugins."""
        plugin_configs = self.config.get("plugins", {})
        
        for plugin_name, plugin_config in plugin_configs.items():
            if not plugin_config.get("enabled", False):
                continue
            
            try:
                plugin = await self._load_plugin(plugin_name, plugin_config)
                if await plugin.initialize():
                    self.plugins.append(plugin)
                    logger.info(f"Loaded plugin: {plugin_name}")
                else:
                    logger.error(f"Failed to initialize plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_name}: {e}")
    
    async def _load_plugin(self, name: str, config: Dict[str, Any]) -> Plugin:
        """Load a single plugin."""
        module_path = config.get("module", f"plugins.{name}")
        class_name = config.get("class", f"{name.title()}Plugin")
        
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        
        return plugin_class(self.config)
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data through all loaded plugins."""
        for plugin in self.plugins:
            try:
                data = await plugin.process(data)
            except Exception as e:
                logger.error(f"Error in plugin {plugin.name}: {e}")
        
        return data
    
    async def cleanup(self) -> None:
        """Clean up all plugins."""
        for plugin in self.plugins:
            try:
                await plugin.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin.name}: {e}")
```

### Custom Data Sources

#### 1. Database Integration
```python
# app/datasources/database.py
import asyncpg
from typing import List, Dict, Any

class DatabaseDataSource:
    """Database data source for historical data."""
    
    def __init__(self, config: Config):
        self.config = config
        self.connection_string = config.get("database", "connection_string")
        self.pool = None
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(self.connection_string)
    
    async def get_historical_quotes(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Retrieve historical quotes from database."""
        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT symbol, date, open, high, low, close, volume
                FROM historical_quotes
                WHERE symbol = $1 AND date BETWEEN $2 AND $3
                ORDER BY date
            """, symbol, start_date, end_date)
            
            return [dict(row) for row in rows]
    
    async def store_quotes(self, quotes: List[Dict[str, Any]]) -> None:
        """Store quotes in database."""
        async with self.pool.acquire() as connection:
            await connection.executemany("""
                INSERT INTO quotes (symbol, timestamp, bid, ask, last, volume)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                    bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask,
                    last = EXCLUDED.last,
                    volume = EXCLUDED.volume
            """, [(q["symbol"], q["timestamp"], q["bid"], q["ask"], q["last"], q.get("volume", 0)) for q in quotes])
```

## Deployment Guide

### Production Configuration

#### Environment Setup
```bash
# Production environment variables
export APP_ENVIRONMENT=production
export FLASK_DEBUG=false
export TOKEN_ENC_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export OAUTH_CLIENT_ID=your_production_client_id
export OAUTH_CLIENT_SECRET=your_production_client_secret
```

#### Configuration File
```toml
# config.production.toml
[auth]
authorize_url = "https://api.schwabapi.com/v1/oauth/authorize"
token_url = "https://api.schwabapi.com/v1/oauth/token"
base_url = "https://api.schwabapi.com/v1"

[env.prod]
redirect_uri = "https://your-domain.com/auth/callback"
host = "0.0.0.0"
port = 8080

[logging]
level = "INFO"
rotate_when = "midnight"
backup_count = 30

[runtime]
storage_root = "/var/lib/trade-analyst/data"
token_cache = "/var/lib/trade-analyst/tokens/cache.json"
```

### Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENVIRONMENT=production

# Create application user
RUN useradd --create-home --shell /bin/bash app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /var/lib/trade-analyst/{data,tokens,logs} \
    && chown -R app:app /var/lib/trade-analyst \
    && chown -R app:app /app

# Switch to application user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -m app.main healthcheck || exit 1

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "app.main", "serve-callback", "--host", "0.0.0.0", "--port", "8080"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  trade-analyst:
    build: .
    ports:
      - "8080:8080"
    environment:
      - APP_ENVIRONMENT=production
      - OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}
      - OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET}
      - TOKEN_ENC_KEY=${TOKEN_ENC_KEY}
    volumes:
      - ./data:/var/lib/trade-analyst/data
      - ./logs:/var/lib/trade-analyst/logs
      - ./tokens:/var/lib/trade-analyst/tokens
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - trade-analyst
    restart: unless-stopped
```

### Monitoring and Observability

#### Health Check Endpoint
```python
# app/monitoring/health.py
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class HealthCheck:
    name: str
    status: str
    response_time_ms: float
    details: Dict[str, Any] = None

class HealthMonitor:
    """Comprehensive health monitoring."""
    
    async def check_all(self) -> List[HealthCheck]:
        """Run all health checks."""
        checks = []
        
        # System resources
        checks.append(await self._check_system_resources())
        
        # Database connectivity
        checks.append(await self._check_database())
        
        # API connectivity
        checks.append(await self._check_api_connectivity())
        
        # Token validity
        checks.append(await self._check_authentication())
        
        return checks
```

#### Logging Configuration
```python
# app/logging.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/trade-analyst/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
            'level': 'INFO'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}
```

### Performance Optimization

#### Connection Pooling
```python
# app/utils/connection_pool.py
import asyncio
import aiohttp
from typing import Optional

class ConnectionPool:
    """Manage HTTP connection pools for API clients."""
    
    def __init__(self, max_connections: int = 100, max_keepalive_connections: int = 20):
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_keepalive_connections,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.connector:
            await self.connector.close()
```

#### Caching Strategy
```python
# app/cache/redis_cache.py
import redis.asyncio as redis
import json
from typing import Any, Optional

class RedisCache:
    """Redis-based caching for API responses."""
    
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set cached value with TTL."""
        await self.redis.setex(key, ttl, json.dumps(value))
    
    async def delete(self, key: str) -> None:
        """Delete cached value."""
        await self.redis.delete(key)
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()
```

---

## Contributing

### Development Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Make changes with tests**
4. **Run quality checks**: `make test lint format`
5. **Submit a pull request**

### Code Review Guidelines

- All code must have test coverage
- Follow existing code style and patterns
- Include documentation for new features
- Update relevant documentation
- Ensure all CI checks pass

### Release Process

1. **Version Bump**: Update version in `pyproject.toml`
2. **Changelog**: Update `CHANGELOG.md` with new features and fixes
3. **Tag Release**: Create git tag with version number
4. **Build and Test**: Run full test suite and build packages
5. **Deploy**: Deploy to production environment

---

**Version**: 1.0  
**Last Updated**: August 15, 2025  
**Maintainer**: Trade Analyst Development Team
