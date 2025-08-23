# levels.v1 JSON Schema Documentation

## Overview

The `levels.v1` format provides a comprehensive, machine-readable output for the `calc-levels` command. This format includes full provenance tracking, quality metrics, and input parameter documentation, making it suitable for automated systems and data pipelines.

## Usage

```bash
# Use levels.v1 format
python ta_production.py calc-levels --symbol /NQ --date 2025-08-22 --format levels.v1

# Alternative format name
python ta_production.py calc-levels --symbol /NQ --date 2025-08-22 --format levels-v1
```

## Schema Definition

The `levels.v1` format follows JSON Schema 2020-12 specification:

- **Schema ID**: `https://trade-analyst/specs/levels.v1.schema.json`
- **Version**: `levels.v1` (constant)
- **Validation**: Built-in schema validation ensures compliance

## Structure

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Must be `"levels.v1"` |
| `symbol` | string | Resolved trading symbol (e.g., `"NQU25"`) |
| `date` | string | Trading session date (`"YYYY-MM-DD"`) |
| `session` | string | Session type: `"rth"` or `"eth"` |
| `pivot_kind` | string | Pivot calculation: `"classic"`, `"fib"`, or `"camarilla"` |
| `levels` | object | Calculated levels (R1, S1, VWAP, pivot) |
| `quality` | object | Data quality metrics |
| `provenance` | object | Data source and authenticity information |
| `input` | object | Input parameters and configuration |

### Levels Object

```json
{
  "levels": {
    "R1": 23245.75,      // Resistance level 1 (number)
    "S1": 23129.25,      // Support level 1 (number) 
    "VWAP": 23187.42,    // Volume-weighted average price (number or null)
    "pivot": 23187.50    // Pivot point (number, optional)
  }
}
```

### Quality Object

```json
{
  "quality": {
    "vwap_method": "intraday_true",    // "intraday_true" or "unavailable"
    "intraday_bar_count": 390,         // Number of intraday bars used
    "bars_expected": 390,              // Expected number of bars (optional)
    "coverage_pct": 100.0,             // Percentage coverage (0-100)
    "data_lag_ms": 850                 // Data retrieval latency (optional)
  }
}
```

### Provenance Object

```json
{
  "provenance": {
    "provider": "schwab",                                  // Data provider
    "provider_request_id": "req-abc-123",                  // Request ID (optional)
    "is_synthetic": false,                                 // Data authenticity flag
    "session_window": "2025-08-22 09:30–16:00 America/New_York",  // Trading session
    "roll_mode": "calendar"                                // Futures roll mode (optional)
  }
}
```

### Input Object

```json
{
  "input": {
    "symbol_raw": "/NQ",             // Original input symbol
    "tz": "America/New_York",        // IANA timezone
    "anchor": null,                  // Anchor time for anchored VWAP (optional)
    "adjust": null,                  // Price adjustment: "none", "split", "split+div" (optional)
    "roll": "calendar",              // Futures roll: "calendar", "volume", "open_interest" (optional)
    "interval": "1min",              // Data interval: "1min", "5min", "15min", "1h", "1d" (optional)
    "precision": 4                   // Decimal places for prices (optional)
  }
}
```

## Complete Example

### Successful Calculation (with VWAP)

```json
{
  "version": "levels.v1",
  "symbol": "NQU25",
  "date": "2025-08-22",
  "session": "rth",
  "pivot_kind": "classic",
  "vwap_kind": "session",
  "input": {
    "symbol_raw": "/NQ",
    "tz": "America/New_York",
    "anchor": null,
    "adjust": null,
    "roll": "calendar",
    "interval": "1min",
    "precision": 4
  },
  "levels": {
    "R1": 23245.75,
    "S1": 23129.25,
    "VWAP": 23187.42,
    "pivot": 23187.50
  },
  "quality": {
    "vwap_method": "intraday_true",
    "intraday_bar_count": 390,
    "bars_expected": 390,
    "coverage_pct": 100.0,
    "data_lag_ms": 850
  },
  "provenance": {
    "provider": "schwab",
    "provider_request_id": "req-abc-123",
    "is_synthetic": false,
    "session_window": "2025-08-22 09:30–16:00 America/New_York",
    "roll_mode": "calendar"
  }
}
```

### VWAP Unavailable Scenario

```json
{
  "version": "levels.v1",
  "symbol": "NQU25", 
  "date": "2025-08-22",
  "session": "rth",
  "pivot_kind": "classic",
  "vwap_kind": "session",
  "input": {
    "symbol_raw": "/NQ",
    "tz": "America/New_York",
    "roll": "calendar",
    "interval": "1min"
  },
  "levels": {
    "R1": 23245.75,
    "S1": 23129.25,
    "VWAP": null,          // null when unavailable
    "pivot": 23187.50
  },
  "quality": {
    "vwap_method": "unavailable",   // Explicitly marked as unavailable
    "intraday_bar_count": 0,
    "bars_expected": 390,
    "coverage_pct": 0.0,
    "data_lag_ms": null
  },
  "provenance": {
    "provider": "schwab", 
    "is_synthetic": false,
    "session_window": "2025-08-22 09:30–16:00 America/New_York"
  }
}
```

## Quality Metrics

### VWAP Methods
- **`intraday_true`**: VWAP calculated from actual minute bars
- **`unavailable`**: No intraday data available (VWAP = null)

### Coverage Calculation
- **RTH 1min**: 390 bars expected (9:30 AM - 4:00 PM ET = 6.5 hours)
- **RTH 5min**: 78 bars expected (390 ÷ 5)
- **Coverage %**: `(actual_bars / expected_bars) × 100`

### Data Lag
- Measures API response time in milliseconds
- Helps identify performance issues
- `null` when measurement unavailable

## Production Safety Features

### Authenticity Tracking
- **`is_synthetic`**: Always `false` for real market data
- **`provider`**: Data source identification
- **`provider_request_id`**: Request traceability

### Error Handling
The system will **fail explicitly** rather than provide synthetic data:
- Exit code 1 if VWAP unavailable
- Error messages to STDERR
- No silent fallbacks to estimated VWAP

### Session Window
- Documents exact trading session used
- Includes timezone for unambiguous timestamps
- Format: `"YYYY-MM-DD HH:MM–HH:MM TIMEZONE"`

## Schema Validation

The implementation includes built-in validation:

```python
from app.schemas.levels_v1 import validate_levels_v1_schema

# Validate output before returning
validate_levels_v1_schema(output)  # Raises ValueError if invalid
```

## Integration with Other Formats

| Format | Use Case | Machine Readable | Provenance |
|--------|----------|------------------|------------|
| `ai-block` | Human-readable display | ❌ | ✅ (STDERR) |
| `json` | Simple API integration | ⚠️ Limited | ✅ |
| `levels.v1` | Full automation/pipeline | ✅ Complete | ✅ Full |
| `csv` | Spreadsheet analysis | ⚠️ Flat | ✅ Inline |

## Future Enhancements

The levels.v1 schema is designed for extensibility:

### Planned Features
- **Fibonacci levels**: `pivot_kind: "fib"` with additional levels
- **Camarilla pivots**: `pivot_kind: "camarilla"` with 8 levels 
- **Anchored VWAP**: `vwap_kind: "anchored"` with anchor time
- **Extended hours**: `session: "eth"` for pre/post market

### Optional Fields
All optional fields can be added without breaking existing consumers:
- `precision`: Price decimal places
- `data_lag_ms`: Performance monitoring
- `bars_expected`: Data completeness assessment
- `roll_mode`: Futures contract roll methodology

## Error Scenarios

### Historical API Not Implemented (Current State)
```bash
$ python ta_production.py calc-levels --symbol /NQ --date 2025-08-22 --format levels.v1
[DEBUG] Historical API not yet implemented - this is expected
E-NODATA-DAILY: Daily OHLC API not yet implemented for NQU25
exit code: 1
```

### Invalid Symbol
```bash
$ python ta_production.py calc-levels --symbol INVALID --date 2025-08-22 --format levels.v1
E-NODATA-DAILY: No daily OHLC for INVALID on 2025-08-22
exit code: 1
```

### Invalid Format
```bash
$ python ta_production.py calc-levels --symbol /NQ --date 2025-08-22 --format invalid
E-INVALID-FORMAT: Unknown format: invalid. Use: ai-block, json, levels.v1, csv
exit code: 1
```

## Implementation Status

- ✅ **Schema Definition**: JSON Schema 2020-12 compliant
- ✅ **Data Structures**: Complete type-safe implementation
- ✅ **Validation**: Built-in schema compliance checking
- ✅ **Testing**: Comprehensive unit tests
- ✅ **Documentation**: Usage examples and specifications
- ⏳ **Real Data**: Pending Schwab historical API implementation

The levels.v1 format is production-ready and will work immediately once the real Schwab historical API integration is completed according to the RFP specifications.
