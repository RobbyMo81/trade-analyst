#!/usr/bin/env python3
"""
Integration Tests for calc-levels Provider Integration

Tests that the calc-levels command properly integrates with the ProductionDataProvider
and handles various provider response scenarios correctly.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, date
import json

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.production_provider import ProductionDataProvider, OHLCData, IntradayBar


class TestProviderIntegration:
    """Test calc-levels integration with ProductionDataProvider"""
    
    @pytest.mark.asyncio
    async def test_calc_levels_calls_preflight_check(self):
        """Verify calc-levels calls provider.preflight_check()"""
        
        # Mock the provider and its methods
        mock_provider = Mock(spec=ProductionDataProvider)
        mock_provider.preflight_check = AsyncMock(return_value={"auth": "ok"})
        mock_provider.get_daily_ohlc = AsyncMock(side_effect=SystemExit("E-NODATA-DAILY"))
        mock_provider.get_intraday_bars = AsyncMock(return_value=[])
        mock_provider.calculate_true_vwap = Mock(return_value=None)
        mock_provider.create_session_info = Mock(return_value="test-session")
        mock_provider.request_id = "test-123"
        
        with patch('app.config.Config'), \
             patch('app.auth.AuthManager'), \
             patch('app.production_provider.ProductionDataProvider', return_value=mock_provider), \
             patch('app.guardrails.fail_fast', side_effect=SystemExit("E-INVALID-DATE")):
            
            # Import after patching
            from start import calc_levels
            
            # Call should trigger preflight check before failing on date parsing
            with pytest.raises(SystemExit):
                calc_levels("/NQ", "invalid-date", "json")
            
            # Even though it failed, preflight should not have been called yet due to date parsing
            # Let's test with valid date
            with pytest.raises(SystemExit):
                calc_levels("/NQ", "2025-08-18", "json")
            
            # Now preflight should have been called
            mock_provider.preflight_check.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_provider_ohlc_available_intraday_missing(self):
        """Test scenario: OHLC data available but no intraday bars"""
        
        # Create mock OHLC data
        mock_ohlc = OHLCData(
            open=169.0,
            high=170.0, 
            low=168.0,
            close=169.5,
            volume=100000,
            timestamp=datetime(2025, 8, 18, 16, 0)
        )
        
        mock_provider = Mock(spec=ProductionDataProvider)
        mock_provider.preflight_check = AsyncMock(return_value={"auth": "ok"})
        mock_provider.get_daily_ohlc = AsyncMock(return_value=mock_ohlc)
        mock_provider.get_intraday_bars = AsyncMock(return_value=[])  # No bars
        mock_provider.calculate_true_vwap = Mock(return_value=None)
        mock_provider.create_session_info = Mock(return_value="2025-08-18 09:30–16:00 ET")
        mock_provider.request_id = "test-123"
        
        with patch('app.config.Config'), \
             patch('app.auth.AuthManager'), \
             patch('app.production_provider.ProductionDataProvider', return_value=mock_provider), \
             patch('app.guardrails.create_provenance_data') as mock_provenance, \
             patch('app.guardrails.emit_provenance') as mock_emit:
            
            mock_provenance.return_value = {
                "data_source": "schwab",
                "is_synthetic": False,
                "vwap_method": "unavailable",
                "provider_request_id": "test-123", 
                "source_session": "2025-08-18 09:30–16:00 ET",
                "timestamp": "2025-08-22T12:00:00Z"
            }
            
            from start import calc_levels
            
            # Capture output
            with patch('builtins.print') as mock_print, \
                 patch('sys.exit') as mock_exit:
                
                calc_levels("/NQ", "2025-08-18", "json")
                
                # Verify provider methods were called
                mock_provider.get_daily_ohlc.assert_called_once()
                mock_provider.get_intraday_bars.assert_called_once()
                mock_provider.calculate_true_vwap.assert_called_once_with([])
                
                # Verify VWAP unavailable exit
                mock_exit.assert_called_once_with(1)
                
                # Find JSON output and verify structure
                json_calls = [call for call in mock_print.call_args_list 
                             if call[0] and isinstance(call[0][0], str)]
                
                json_output = None
                for call in json_calls:
                    try:
                        json_output = json.loads(call[0][0])
                        break
                    except (json.JSONDecodeError, IndexError):
                        continue
                
                if json_output:
                    assert json_output["levels"]["VWAP"] is None
                    assert json_output["provenance"]["vwap_method"] == "unavailable"
    
    @pytest.mark.asyncio
    async def test_provider_both_data_available(self):
        """Test scenario: Both OHLC and intraday data available"""
        
        # Mock OHLC data
        mock_ohlc = OHLCData(
            open=169.0, high=170.0, low=168.0, close=169.5,
            volume=100000, timestamp=datetime(2025, 8, 18, 16, 0)
        )
        
        # Mock intraday bars
        mock_bars = [
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 30),
                open=169.0, high=169.5, low=168.8, close=169.2, volume=1000
            ),
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 31), 
                open=169.2, high=169.8, low=169.0, close=169.6, volume=1500
            )
        ]
        
        mock_provider = Mock(spec=ProductionDataProvider)
        mock_provider.preflight_check = AsyncMock(return_value={"auth": "ok"})
        mock_provider.get_daily_ohlc = AsyncMock(return_value=mock_ohlc)
        mock_provider.get_intraday_bars = AsyncMock(return_value=mock_bars)
        mock_provider.calculate_true_vwap = Mock(return_value=169.35)  # Calculated VWAP
        mock_provider.create_session_info = Mock(return_value="2025-08-18 09:30–16:00 ET")
        mock_provider.request_id = "test-456"
        
        with patch('app.config.Config'), \
             patch('app.auth.AuthManager'), \
             patch('app.production_provider.ProductionDataProvider', return_value=mock_provider), \
             patch('app.guardrails.create_provenance_data') as mock_provenance, \
             patch('app.guardrails.emit_provenance'):
            
            mock_provenance.return_value = {
                "data_source": "schwab",
                "is_synthetic": False,
                "vwap_method": "intraday_true",
                "provider_request_id": "test-456",
                "source_session": "2025-08-18 09:30–16:00 ET", 
                "timestamp": "2025-08-22T12:00:00Z"
            }
            
            from start import calc_levels
            
            # Should not exit since VWAP is available
            with patch('builtins.print') as mock_print, \
                 patch('sys.exit') as mock_exit:
                
                calc_levels("/NQ", "2025-08-18", "json")
                
                # Should NOT exit with error since VWAP is available
                mock_exit.assert_not_called()
                
                # Verify provider calls
                mock_provider.calculate_true_vwap.assert_called_once_with(mock_bars)
                
                # Find and verify JSON output
                json_output = None
                for call in mock_print.call_args_list:
                    if call[0] and isinstance(call[0][0], str):
                        try:
                            json_output = json.loads(call[0][0])
                            break
                        except:
                            continue
                
                if json_output:
                    assert json_output["levels"]["VWAP"] == 169.35
                    assert json_output["provenance"]["vwap_method"] == "intraday_true"
    
    @pytest.mark.asyncio
    async def test_provider_auth_failure(self):
        """Test provider authentication failure scenario"""
        
        mock_provider = Mock(spec=ProductionDataProvider)
        mock_provider.preflight_check = AsyncMock(side_effect=SystemExit("E-AUTH: Authentication failed"))
        
        with patch('app.config.Config'), \
             patch('app.auth.AuthManager'), \
             patch('app.production_provider.ProductionDataProvider', return_value=mock_provider):
            
            from start import calc_levels
            
            with pytest.raises(SystemExit) as excinfo:
                calc_levels("/NQ", "2025-08-18", "json")
            
            assert "E-AUTH" in str(excinfo.value)
    
    def test_provider_calls_with_correct_symbol_translation(self):
        """Test that provider receives properly translated futures symbols"""
        
        mock_provider = Mock(spec=ProductionDataProvider)
        mock_provider.preflight_check = AsyncMock(return_value={"auth": "ok"})
        mock_provider.get_daily_ohlc = AsyncMock(side_effect=SystemExit("E-NODATA-DAILY"))
        
        with patch('app.config.Config'), \
             patch('app.auth.AuthManager'), \
             patch('app.production_provider.ProductionDataProvider', return_value=mock_provider):
            
            from start import calc_levels
            
            with pytest.raises(SystemExit):
                calc_levels("/NQ", "2025-08-18", "json")
            
            # Verify the symbol was passed correctly (should be translated by provider internally)
            mock_provider.get_daily_ohlc.assert_called_once()
            call_args = mock_provider.get_daily_ohlc.call_args
            symbol_arg = call_args[0][0]  # First positional argument
            
            # The symbol passed should be the original format - provider handles translation
            assert symbol_arg == "/NQ"


class TestVWAPCalculation:
    """Test VWAP calculation scenarios"""
    
    def test_vwap_calculation_with_real_bars(self):
        """Test VWAP calculation with realistic intraday bars"""
        
        bars = [
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 30),
                open=4200.0, high=4205.0, low=4198.0, close=4203.0, volume=100
            ),
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 31),
                open=4203.0, high=4208.0, low=4201.0, close=4206.0, volume=150  
            ),
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 32),
                open=4206.0, high=4206.0, low=4202.0, close=4204.0, volume=120
            )
        ]
        
        # Calculate expected VWAP manually:
        # Bar 1: typical = (4205+4198+4203)/3 = 4202.0, pv = 420200
        # Bar 2: typical = (4208+4201+4206)/3 = 4205.0, pv = 630750  
        # Bar 3: typical = (4206+4202+4204)/3 = 4204.0, pv = 504480
        # Total PV = 1555430, Total Volume = 370, VWAP = 4204.135
        
        provider = ProductionDataProvider(Mock(), Mock())
        vwap = provider.calculate_true_vwap(bars)
        
        expected_vwap = 1555430.0 / 370.0  # ≈ 4204.135
        assert vwap is not None, "VWAP should not be None with valid bars"
        assert abs(vwap - expected_vwap) < 0.001
    
    def test_vwap_calculation_empty_bars(self):
        """Test VWAP calculation with no bars returns None"""
        provider = ProductionDataProvider(Mock(), Mock())
        vwap = provider.calculate_true_vwap([])
        assert vwap is None
    
    def test_vwap_calculation_zero_volume(self):
        """Test VWAP calculation with zero total volume"""
        bars = [
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 30),
                open=4200.0, high=4205.0, low=4198.0, close=4203.0, volume=0
            )
        ]
        
        provider = ProductionDataProvider(Mock(), Mock())
        vwap = provider.calculate_true_vwap(bars)
        assert vwap is None


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])
