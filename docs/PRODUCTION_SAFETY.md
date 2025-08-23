# Production Safety System - User Guide

## Overview

The Trade Analyst system now implements **production safety** to prevent synthetic stub data from being presented as real market information. By default, all stub code paths are **BLOCKED** in production mode (`FAIL_ON_STUB=1`).

## Commands

### Diagnostics

Check provider authentication and connectivity:

```bash
python ta_production.py diag provider
```

**Expected Success Output:**
```json
{
  "auth": "ok",
  "provider": "schwab",
  "quota": "ok", 
  "time": "2025-08-22T12:00:00.000000Z",
  "request_id": "abc-123-def-456"
}
```

### Calculate Levels

Calculate R1, S1, VWAP with mandatory provenance:

```bash
python ta_production.py calc-levels --symbol /NQ --date 2025-08-18 --format json
```

**Expected Success Output (when real APIs implemented):**
```json
{
  "symbol": "/NQ",
  "date": "2025-08-18",
  "levels": {
    "R1": 4235.75,
    "S1": 4198.25, 
    "VWAP": 4217.85,
    "pivot": 4217.00
  },
  "provenance": {
    "data_source": "schwab",
    "is_synthetic": false,
    "vwap_method": "intraday_true",
    "provider_request_id": "req-789",
    "source_session": "2025-08-18 09:30–16:00 ET",
    "timestamp": "2025-08-22T12:00:00.000000Z"
  }
}
```

**AI-Block Format:**
```bash
python ta_production.py calc-levels --symbol /NQ --date 2025-08-18 --format ai-block
```

Output:
```
[AI_DATA_BLOCK_START]
R1: 4235.7500
S1: 4198.2500
VWAP: 4217.8500
[AI_DATA_BLOCK_END]
```

Provenance automatically emitted to STDERR:
```
[PROVENANCE] data_source=schwab is_synthetic=false vwap_method=intraday_true
```

## Error Scenarios

### Authentication Missing/Expired

**Command:**
```bash
python ta_production.py diag provider
```

**Error Output:**
```json
{
  "auth": "failed",
  "provider": "schwab",
  "error": "Missing/expired token; authentication required",
  "time": "2025-08-22T12:00:00.000000Z"
}
```

**Exit Code:** `1`

### No Intraday Data Available

**Command:**
```bash
python ta_production.py calc-levels --symbol /NQ --date 2025-08-18 --format json
```

**Error Output:**
```json
{
  "symbol": "/NQ",
  "date": "2025-08-18", 
  "levels": {
    "R1": 4235.75,
    "S1": 4198.25,
    "VWAP": null,
    "pivot": 4217.00
  },
  "provenance": {
    "data_source": "schwab",
    "is_synthetic": false,
    "vwap_method": "unavailable",
    "provider_request_id": "req-789",
    "source_session": "2025-08-18 09:30–16:00 ET",
    "timestamp": "2025-08-22T12:00:00.000000Z"
  }
}
```

**STDERR:**
```
E-VWAP-UNAVAILABLE: VWAP data not available for /NQ on 2025-08-18
```

**Exit Code:** `1`

### API Not Yet Implemented (Current State)

**Command:**
```bash
python ta_production.py calc-levels --symbol /NQ --date 2025-08-18 --format json
```

**Error Output:**
```
[DEBUG] Running pre-flight checks...
[DEBUG] Pre-flight result: {'auth': 'ok', ...}
[DEBUG] Fetching daily OHLC for /NQ
E-NODATA-DAILY: Daily OHLC API not yet implemented for NQU25
```

**Exit Code:** `1`

### Rate Limit Exceeded

**Error Code:** `E-RATE-LIMIT`
**Message:** `"Rate limit exceeded: 120 requests/minute"`
**Exit Code:** `1`

### Production Safety Block

**Command (with FAIL_ON_STUB=1):**
```bash
FAIL_ON_STUB=1 python ta_production.py calc-levels --symbol /NQ --date 2025-08-18
```

**Error Output:**
```
E-STUB-PATH: stub code path is disabled in this environment
```

**Exit Code:** System terminates immediately

## Environment Variables

- **FAIL_ON_STUB=1** (default): Production mode - blocks all stub execution
- **FAIL_ON_STUB=0**: Development mode - allows controlled stub testing

## Key Features

✅ **No Silent Fallbacks** - System fails explicitly rather than providing fake data  
✅ **Mandatory Provenance** - All outputs include data source and authenticity info  
✅ **Pre-flight Checks** - Authentication validated before data operations  
✅ **True VWAP Only** - VWAP calculated only from intraday minute bars  
✅ **Error Codes** - Standardized error handling with proper exit codes

## Testing

Run production safety tests:

```bash
python tests/verify_production_safety.py
```

Expected output:
```
Production Safety Verification: PASSED
- Guardrails prevent stub execution when FAIL_ON_STUB=1
- Production mode blocks calc_levels from using synthetic data
- Provenance tracking system is functional
- System fails explicitly rather than providing fake data
```
