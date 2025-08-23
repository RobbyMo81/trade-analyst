# RFP Summary: Schwab Historical API Integration

## Overview
This RFP outlines the plan to implement real Schwab historical API integration to enable the `calc-levels` command with authentic market data while maintaining production safety standards.

## Current Situation
- ✅ **Real-time quotes working**: `/NQU25` returns live data ($23,187.25/$23,188.25)
- ✅ **Production safety active**: `FAIL_ON_STUB=1` blocks synthetic data
- ❌ **Historical APIs blocked**: Intentionally fail to prevent fake data
- ❌ **calc-levels incomplete**: Cannot calculate R1/S1/VWAP without real historical data

## Technical Implementation Required

### 1. Schwab API Endpoints
- **Historical OHLC**: `GET /marketdata/v1/pricehistory` for daily candles (R1/S1 calculation)
- **Intraday Bars**: Same endpoint with minute frequency for true VWAP calculation

### 2. Code Changes Required
- **`app/production_provider.py`**: Replace stub methods with real API calls
- **`app/providers/schwab.py`**: Add `get_price_history()` method
- **Error handling**: Comprehensive network, auth, and data quality validation

### 3. Key Features
- **No synthetic fallbacks**: Fail explicitly if real data unavailable
- **Provenance tracking**: All data tagged with source authenticity
- **Graceful degradation**: OHLC without intraday = R1/S1 only, no VWAP
- **Performance targets**: <3 seconds total response time

## Quality Assurance
- **Unit tests**: API parsing, error handling, data validation
- **Integration tests**: End-to-end calc-levels with mocked real data
- **Live testing**: Real market data validation

## Timeline
- **4 weeks total**
- **Week 1-2**: Core API integration and data mapping
- **Week 3**: Error handling and comprehensive testing
- **Week 4**: Production readiness and deployment

## Success Criteria
- [ ] `calc-levels --symbol /NQ --date 2025-08-22 --format json` returns real market data
- [ ] R1/S1 calculated from actual daily OHLC (not synthetic)
- [ ] VWAP calculated from actual minute bars (not synthetic) 
- [ ] Production safety maintained (no synthetic fallbacks)
- [ ] All error scenarios properly handled with clear messages

## Risk Mitigation
- **API changes**: Version pinning and contract tests
- **Rate limiting**: Proper backoff and monitoring (120 req/min limit)
- **Data quality**: Validation and sanity checks (OHLC relationships)
- **Security**: Existing token management, HTTPS only

This RFP provides a comprehensive roadmap to transform the current production-safe but data-blocked system into a fully functional calc-levels service with real market data.
