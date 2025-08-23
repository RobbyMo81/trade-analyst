# Go/No-Go Plan: Remove Historical API Blocker

## Status Analysis

### ✅ Confirmed Working
- **Authentication**: `auth: "ok"` - Schwab API credentials validated
- **Connectivity**: Provider diagnostics returning proper timestamps and request_ids
- **Error Taxonomy**: 17 E-* codes with structured handling
- **Production Safety**: `FAIL_ON_STUB=1` blocking all synthetic data
- **Schema Validation**: JSON Schema 2020-12 compliant levels.v1 format

### ❓ Still Unproven (Blockers)
- **Daily OHLC**: `get_daily_ohlc()` returns `E-NODATA-DAILY` - no real implementation
- **Minute Bars**: `get_intraday_bars()` returns `E-NODATA-INTRADAY` - no real implementation  
- **True VWAP**: Cannot compute session-bounded VWAP without minute bars
- **End-to-End**: `calc-levels` fails before reaching calculation logic

## Minimal Implementation Plan (Deterministic)

### Step 1: Wire Historical Daily OHLC (15 minutes)

**File**: `app/production_provider.py` - `get_daily_ohlc()` method

**Change**: Replace stub detection with real Schwab API call

```python
async def get_daily_ohlc(self, symbol: str, target_date: date) -> Optional[OHLCData]:
    """Get daily OHLC data for the previous trading session."""
    try:
        translated_symbol = translate_root_to_front_month(symbol).upper()
        logger.info(f"Fetching daily OHLC for {translated_symbol}")
        
        # Calculate date range (previous trading day)
        end_date = target_date
        start_date = target_date - timedelta(days=3)  # Account for weekends
        
        # Call real Schwab historical API
        historical_data = await self.client.get_price_history(
            symbol=translated_symbol,
            period_type='day',
            period=1,
            frequency_type='daily',
            frequency=1,
            start_date=start_date,
            end_date=end_date,
            need_extended_hours_data=False
        )
        
        if historical_data and 'candles' in historical_data and historical_data['candles']:
            candle = historical_data['candles'][-1]  # Most recent day
            return OHLCData(
                open=candle['open'],
                high=candle['high'], 
                low=candle['low'],
                close=candle['close'],
                volume=int(candle['volume']),
                timestamp=datetime.fromtimestamp(candle['datetime'] / 1000)
            )
        else:
            fail_no_daily_data(translated_symbol, str(target_date), self.request_id)
            
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Failed to get daily OHLC for {symbol}: {e}")
        fail_no_daily_data(translated_symbol, str(target_date), self.request_id)
```

### Step 2: Wire Intraday Minute Bars (15 minutes)

**File**: `app/production_provider.py` - `get_intraday_bars()` method

**Change**: Replace stub detection with real Schwab API call

```python
async def get_intraday_bars(self, symbol: str, target_date: date, session: str = "rth") -> List[IntradayBar]:
    """Get intraday minute bars for VWAP calculation."""
    try:
        translated_symbol = translate_root_to_front_month(symbol).upper()
        logger.info(f"Fetching intraday bars for {translated_symbol} on {target_date}")
        
        # Call real Schwab intraday API
        intraday_data = await self.client.get_price_history(
            symbol=translated_symbol,
            period_type='day',
            period=1,
            frequency_type='minute',
            frequency=1,
            start_date=target_date,
            end_date=target_date,
            need_extended_hours_data=(session != "rth")
        )
        
        if intraday_data and 'candles' in intraday_data:
            bars = []
            for candle in intraday_data['candles']:
                bars.append(IntradayBar(
                    timestamp=datetime.fromtimestamp(candle['datetime'] / 1000),
                    open=candle['open'],
                    high=candle['high'],
                    low=candle['low'], 
                    close=candle['close'],
                    volume=int(candle['volume'])
                ))
            return bars
        else:
            fail_no_intraday_data(translated_symbol, str(target_date), session, True, self.request_id)
            
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Failed to get intraday bars for {symbol}: {e}")
        return []
```

### Step 3: Session-Bounded VWAP (Already Implemented)

**Status**: ✅ **Already Complete** - `calculate_true_vwap()` method exists and tested

### Step 4: Provenance Capture (Already Implemented)

**Status**: ✅ **Already Complete** - Comprehensive provenance in `create_provenance_data()`

## Implementation Priority

### 🚨 **CRITICAL PATH (30 minutes total)**
1. **Step 1**: Wire daily OHLC (15 min) - Unlocks Phase 2
2. **Step 2**: Wire intraday bars (15 min) - Unlocks true VWAP

### 📋 **Verification Plan**
```bash
# Test daily OHLC
python ta_production.py calc-levels --symbol /NQ --date 2025-08-21 --format json
# Expected: R1/S1/Pivot calculated from real OHLC

# Test true VWAP  
python ta_production.py calc-levels --symbol /NQ --date 2025-08-21 --format levels.v1
# Expected: VWAP calculated from minute bars, not OHLC average
```

### 🎯 **Success Criteria**
- ✅ `auth: "ok"` (already confirmed)
- ✅ Daily OHLC sourced from Schwab historical API
- ✅ Minute bars sourced from Schwab intraday API  
- ✅ True VWAP computed from minute bars within session window
- ✅ Provenance includes provider, request_id, coverage metrics

## Go/No-Go Decision

**Current Blocker**: Historical API implementation (2 methods, ~30 minutes)

**Readiness After Implementation**: 
- Phase 0: ✅ Complete (100%)
- Phase 1: ✅ Complete (100%)  
- Phase 2: ✅ Ready for testing with real data
- Phases 3-6: ✅ Unblocked for progression

**Recommendation**: 🟢 **GO** - Minimal changes, maximum impact, deterministic outcome
