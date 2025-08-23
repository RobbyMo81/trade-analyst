# Request for Proposal (RFP)
## Schwab Historical API Integration for Production-Safe calc-levels

**Project:** Trade Analyst - Real Historical Data Integration  
**Date:** August 22, 2025  
**Version:** 1.0  
**Priority:** High (Production Safety Dependency)

---

## Executive Summary

The Trade Analyst system currently blocks historical OHLC and intraday data requests in production mode to prevent synthetic stub data from being presented as real market information. This RFP outlines the requirements for implementing real Schwab API integration to enable the `calc-levels` command with authentic market data while maintaining production safety standards.

## Current State Analysis

### What Works Today ✅
- **Real-time quotes**: `/NQU25` returns live bid/ask data ($23,187.25/$23,188.25)
- **Authentication**: Schwab OAuth tokens functional via existing `SchwabClient`
- **Production safety**: `FAIL_ON_STUB=1` blocks synthetic data execution
- **Provider diagnostics**: `ta diag provider` returns auth status
- **Provenance tracking**: Metadata structure ready for real data sources

### What's Blocked (By Design) ❌
- **Historical OHLC**: `E-NODATA-DAILY` - No daily candles API
- **Intraday bars**: `E-NODATA-INTRADAY` - No minute bars API  
- **calc-levels command**: Cannot calculate R1/S1/VWAP without historical data

### Critical Requirements Met 🔒
- **No synthetic fallbacks**: System fails explicitly rather than providing fake data
- **Mandatory provenance**: All outputs must include data source authenticity
- **Error handling**: Proper exit codes and error messages

---

## Technical Requirements

### 1. Schwab API Endpoints to Implement

#### 1.1 Historical OHLC Data
**Endpoint:** `GET /marketdata/v1/pricehistory`  
**Purpose:** Daily OHLC candles for pivot calculations (R1, S1)

**Required Parameters:**
```json
{
  "symbol": "/NQU25",
  "periodType": "day",
  "period": 5,
  "frequencyType": "daily",
  "frequency": 1,
  "endDate": "2025-08-22",
  "needExtendedHoursData": false
}
```

**Expected Response Structure:**
```json
{
  "candles": [
    {
      "open": 23150.00,
      "high": 23245.75, 
      "low": 23120.25,
      "close": 23187.50,
      "volume": 125000,
      "datetime": 1724284800000
    }
  ],
  "symbol": "/NQU25",
  "empty": false
}
```

#### 1.2 Intraday Minute Bars
**Endpoint:** `GET /marketdata/v1/pricehistory`  
**Purpose:** Minute-level bars for true VWAP calculation

**Required Parameters:**
```json
{
  "symbol": "/NQU25",
  "periodType": "day",
  "period": 1,
  "frequencyType": "minute",
  "frequency": 1,
  "startDate": "2025-08-22",
  "endDate": "2025-08-22",
  "needExtendedHoursData": false
}
```

### 2. Implementation Architecture

#### 2.1 ProductionDataProvider Enhancement
**File:** `app/production_provider.py`

**Current Stub Methods to Replace:**
```python
# BEFORE (Intentionally Blocked)
async def get_daily_ohlc(self, symbol: str, target_date: date) -> Optional[OHLCData]:
    fail_fast("E-NODATA-DAILY", f"Daily OHLC API not yet implemented for {translated_symbol}")

# AFTER (Real Implementation Required)
async def get_daily_ohlc(self, symbol: str, target_date: date) -> Optional[OHLCData]:
    """Get real daily OHLC from Schwab API"""
    # Implementation required here
```

#### 2.2 Data Structure Mapping
**Type-Safe Conversion Required:**

```python
# Schwab API Response -> OHLCData
@dataclass
class OHLCData:
    open: float
    high: float  
    low: float
    close: float
    volume: int
    timestamp: datetime

# Schwab API Response -> IntradayBar  
@dataclass  
class IntradayBar:
    timestamp: datetime
    open: float
    high: float
    low: float 
    close: float
    volume: int
```

### 3. Error Handling Requirements

#### 3.1 Network/API Errors
**Required Error Codes:**
- `E-NETWORK`: Connection timeout, DNS resolution failure
- `E-RATE-LIMIT`: API quota exceeded (120 requests/minute)
- `E-AUTH-EXPIRED`: Token expired during API call
- `E-MARKET-CLOSED`: Data not available for requested date
- `E-SYMBOL-INVALID`: Symbol not found or invalid format

#### 3.2 Data Quality Validation
**Required Validations:**
- OHLC values must be positive numbers
- High >= Low, High >= Open, High >= Close
- Low <= Open, Low <= Close  
- Volume must be non-negative integer
- Timestamps must be valid market hours

#### 3.3 Graceful Degradation
**Fallback Strategy:**
- If historical OHLC fails: Return error, DO NOT calculate R1/S1
- If intraday bars fail: Set `VWAP: null`, `vwap_method: "unavailable"`
- If both fail: Exit with proper error code, DO NOT use synthetic data

### 4. Integration Points

#### 4.1 SchwabClient Enhancement
**File:** `app/providers/schwab.py`

**New Methods Required:**
```python
class SchwabClient:
    async def get_price_history(
        self,
        symbol: str,
        period_type: str,
        period: int,
        frequency_type: str,
        frequency: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Call Schwab price history endpoint"""
        # Implementation required
```

#### 4.2 Symbol Translation
**File:** `app/utils/futures.py`

**Current Function:** `translate_root_to_front_month()`
- `/NQ` → `NQU25` (September 2025 contract)
- Must handle contract rollover dates
- Must validate Schwab symbol format

#### 4.3 Authentication Integration
**Requirements:**
- Use existing `AuthManager.get_access_token()`
- Handle token refresh automatically
- Implement proper OAuth2 Bearer token headers
- Support rate limiting and backoff

---

## Functional Requirements

### 5. calc-levels Command Behavior

#### 5.1 Success Case
**Command:** `python ta_production.py calc-levels --symbol /NQ --date 2025-08-22 --format json`

**Expected Output:**
```json
{
  "symbol": "/NQ",
  "date": "2025-08-22",
  "levels": {
    "R1": 23245.75,
    "S1": 23129.25,
    "VWAP": 23187.42,
    "pivot": 23187.50
  },
  "provenance": {
    "data_source": "schwab_api",
    "is_synthetic": false,
    "vwap_method": "intraday_true",
    "provider_request_id": "req-abc-123",
    "source_session": "2025-08-22 09:30–16:00 ET",
    "timestamp": "2025-08-22T12:00:00.000Z"
  }
}
```

#### 5.2 Partial Data Case (No Intraday)
**Scenario:** Historical OHLC available, but no intraday bars

**Expected Behavior:**
- Calculate R1, S1, pivot from OHLC ✅
- Set VWAP to `null` ✅
- Set `vwap_method: "unavailable"` ✅
- Exit with code 1 (VWAP unavailable) ✅
- Emit error to STDERR: `E-VWAP-UNAVAILABLE` ✅

#### 5.3 No Data Case
**Scenario:** No historical data available for date

**Expected Behavior:**
- Exit immediately with `E-NODATA-DAILY`
- DO NOT attempt calculations
- DO NOT return synthetic data

### 6. Pre-flight Integration

#### 6.1 Enhanced Diagnostics
**Command:** `python ta_production.py diag provider`

**Enhanced Output Required:**
```json
{
  "auth": "ok",
  "provider": "schwab_api",
  "quota": {
    "remaining": 95,
    "limit": 120,
    "reset_time": "2025-08-22T12:01:00Z"
  },
  "endpoints": {
    "quotes": "ok",
    "price_history": "ok",
    "market_hours": "ok"
  },
  "time": "2025-08-22T12:00:00.000Z",
  "request_id": "diag-456-def"
}
```

---

## Technical Implementation Plan

### Phase 1: Core API Integration (Week 1-2)
1. **Schwab API Client Enhancement**
   - Implement `get_price_history()` method
   - Add proper error handling and retries
   - Implement rate limiting

2. **Data Structure Mapping**
   - Schwab response → `OHLCData` conversion
   - Schwab response → `IntradayBar` list conversion
   - Timestamp handling and timezone conversion

3. **ProductionDataProvider Implementation**
   - Replace stub `get_daily_ohlc()` with real API call
   - Replace stub `get_intraday_bars()` with real API call
   - Maintain production safety (no fallbacks)

### Phase 2: Error Handling & Validation (Week 2-3)
1. **Comprehensive Error Handling**
   - Network errors, timeouts, rate limits
   - Invalid symbols, market closed scenarios
   - Token expiration during long requests

2. **Data Quality Validation**
   - OHLC data sanity checks
   - Volume and timestamp validation
   - Market hours verification

3. **Graceful Degradation**
   - Partial data scenarios (OHLC without intraday)
   - Proper error codes and messages
   - User-friendly error descriptions

### Phase 3: Testing & Validation (Week 3-4)
1. **Unit Tests**
   - API response parsing
   - Error handling scenarios
   - Data validation logic

2. **Integration Tests**
   - End-to-end calc-levels flow
   - Real API call mocking
   - Production safety verification

3. **Live Testing**
   - Real market data validation
   - Performance testing with rate limits
   - Error scenario testing

---

## Quality Assurance Requirements

### 7. Testing Strategy

#### 7.1 Unit Tests Required
```python
# File: tests/test_schwab_api_integration.py

def test_daily_ohlc_parsing():
    """Test Schwab API response parsing to OHLCData"""

def test_intraday_bars_parsing():
    """Test Schwab API response parsing to IntradayBar list"""

def test_api_error_handling():
    """Test all error scenarios (network, auth, rate limit)"""

def test_data_validation():
    """Test OHLC data quality validation"""
```

#### 7.2 Integration Tests Required
```python  
# File: tests/test_calc_levels_real_api.py

def test_calc_levels_success_with_real_data():
    """Test full calc-levels flow with mocked real API data"""

def test_calc_levels_partial_data():
    """Test OHLC available but no intraday bars"""

def test_calc_levels_no_data():
    """Test proper failure when no data available"""
```

#### 7.3 Contract Tests Required
```python
# File: tests/test_schwab_api_contract.py

def test_price_history_request_format():
    """Verify API request matches Schwab specification"""

def test_price_history_response_parsing():
    """Verify response parsing handles all Schwab response fields"""
```

### 8. Performance Requirements

#### 8.1 Response Time Targets
- **Single calc-levels request:** < 3 seconds total
- **Historical OHLC API call:** < 1 second  
- **Intraday bars API call:** < 2 seconds
- **Total with both calls:** < 2.5 seconds (parallel execution)

#### 8.2 Rate Limiting Compliance
- **Schwab API Limit:** 120 requests/minute
- **Implementation:** Exponential backoff on 429 responses
- **Monitoring:** Track and log rate limit usage

#### 8.3 Error Recovery
- **Network timeouts:** 3 retry attempts with backoff
- **Auth failures:** Automatic token refresh, 1 retry
- **Rate limits:** Wait for reset time, then retry

---

## Security & Compliance Requirements

### 9. Data Security

#### 9.1 Token Management
- Use existing secure token storage
- Automatic token refresh before expiration
- No token logging in production

#### 9.2 API Security
- HTTPS only for all API calls
- Proper User-Agent headers
- Request signing if required

#### 9.3 Data Privacy
- No storage of historical market data
- No logging of sensitive price information
- Compliance with market data redistribution rules

### 10. Production Readiness

#### 10.1 Monitoring & Logging
```python
# Required log levels and messages
logger.info(f"Fetching OHLC for {symbol} on {date}")
logger.warning(f"Rate limit approaching: {remaining}/120")
logger.error(f"API call failed: {error_code} - {message}")
```

#### 10.2 Configuration
```toml
# config.toml additions required
[schwab_api]
base_url = "https://api.schwabapi.com"
timeout_seconds = 10
max_retries = 3
rate_limit_buffer = 5  # Leave 5 requests buffer
```

#### 10.3 Circuit Breaker
- Implement circuit breaker pattern
- Disable API calls after 5 consecutive failures
- Auto-recovery after 5 minutes

---

## Acceptance Criteria

### 11. Definition of Done

#### 11.1 Functional Acceptance
- [ ] `calc-levels --symbol /NQ --date 2025-08-22 --format json` returns real data
- [ ] VWAP calculated from actual minute bars (not synthetic)
- [ ] R1/S1 calculated from actual daily OHLC (not synthetic)
- [ ] Proper error handling for all failure scenarios
- [ ] Production safety maintained (no synthetic fallbacks)

#### 11.2 Technical Acceptance  
- [ ] All unit tests passing (>95% coverage)
- [ ] All integration tests passing
- [ ] Performance requirements met (<3s total response)
- [ ] Rate limiting compliance verified
- [ ] Error scenarios properly handled

#### 11.3 Production Acceptance
- [ ] `ta diag provider` shows API endpoints status
- [ ] Production deployment succeeds
- [ ] Real market data validation passes
- [ ] No synthetic data leakage detected
- [ ] Provenance tracking includes real API sources

---

## Risk Assessment

### 12. Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schwab API changes | High | Version pinning, contract tests |
| Rate limiting issues | Medium | Proper backoff, monitoring |  
| Network connectivity | Medium | Retry logic, circuit breaker |
| Data quality issues | High | Validation, sanity checks |
| Token expiration | Low | Auto-refresh, monitoring |

### 13. Project Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| API documentation incomplete | Medium | Schwab developer support |
| Market data licensing | High | Legal review, compliance |
| Performance degradation | Medium | Load testing, optimization |
| Security vulnerabilities | High | Security review, pen testing |

---

## Success Metrics

### 14. Key Performance Indicators

#### 14.1 Functional Metrics
- **Data Accuracy:** 100% real market data (0% synthetic)
- **API Success Rate:** >99.5% successful requests
- **Error Handling:** 100% of error scenarios covered
- **Response Time:** <3 seconds for calc-levels requests

#### 14.2 Quality Metrics  
- **Test Coverage:** >95% code coverage
- **Bug Rate:** <1 bug per 1000 lines of code
- **Production Issues:** 0 critical issues in first month

#### 14.3 User Experience Metrics
- **Command Success Rate:** >95% successful calc-levels executions
- **Error Clarity:** 100% of errors have actionable messages
- **Documentation Coverage:** 100% of new features documented

---

## Delivery Timeline

### 15. Project Schedule

**Total Duration:** 4 weeks  
**Team Size:** 1 senior developer  
**Start Date:** August 23, 2025  
**Delivery Date:** September 20, 2025

#### Week 1: Foundation
- [ ] Schwab API client enhancement
- [ ] Basic price history integration
- [ ] Data structure mapping

#### Week 2: Core Implementation  
- [ ] ProductionDataProvider real implementation
- [ ] Error handling framework
- [ ] Basic calc-levels integration

#### Week 3: Quality & Testing
- [ ] Comprehensive error handling
- [ ] Unit and integration tests
- [ ] Performance optimization

#### Week 4: Production Readiness
- [ ] Live API testing
- [ ] Documentation completion
- [ ] Deployment and validation

---

## Approval Required

### 16. Stakeholder Sign-off

**Technical Reviewer:** _________________ Date: _________  
**Security Reviewer:** _________________ Date: _________  
**Product Owner:** _________________ Date: _________

---

**Document Control**  
**File:** `docs/RFP_Schwab_Historical_API_Integration.md`  
**Author:** GitHub Copilot  
**Review Status:** Draft  
**Next Review:** August 30, 2025
