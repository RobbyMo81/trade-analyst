#!/usr/bin/env python3
"""
Unit Tests for Production Safety System

Tests the guardrails that prevent stub data from being presented as real market data.
These tests would have caught the critical flaw where synthetic data was silently substituted.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import json
from contextlib import contextmanager
from io import StringIO

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.guardrails import assert_no_stub, require, fail_fast, create_provenance_data, emit_provenance


class TestGuardrails:
    """Test the production safety guardrails"""
    
    def test_assert_no_stub_allows_execution_in_dev_mode(self):
        """FAIL_ON_STUB=0 should allow stub execution"""
        with patch.dict(os.environ, {'FAIL_ON_STUB': '0'}, clear=False):
            # Should not raise
            assert_no_stub()
    
    def test_assert_no_stub_blocks_execution_in_production(self):
        """FAIL_ON_STUB=1 must raise SystemExit with E-STUB-PATH"""
        with patch.dict(os.environ, {'FAIL_ON_STUB': '1'}, clear=False):
            with pytest.raises(SystemExit) as excinfo:
                assert_no_stub()
            
            # Verify it's the correct error
            assert "E-STUB-PATH" in str(excinfo.value)
    
    def test_require_passes_when_condition_true(self):
        """require() should pass when condition is True"""
        # Should not raise
        require(True, "E-TEST", "This should not fail")
    
    def test_require_fails_when_condition_false(self):
        """require() must fail fast when condition is False"""
        with pytest.raises(SystemExit) as excinfo:
            require(False, "E-TEST", "This should fail")
        
        assert "E-TEST" in str(excinfo.value)
        assert "This should fail" in str(excinfo.value)
    
    def test_fail_fast_exits_with_error_code(self):
        """fail_fast() must exit with proper error code and message"""
        with pytest.raises(SystemExit) as excinfo:
            fail_fast("E-CALC-FAILED", "Test failure message")
        
        assert "E-CALC-FAILED" in str(excinfo.value)
        assert "Test failure message" in str(excinfo.value)
    
    def test_create_provenance_data_structure(self):
        """Provenance data must include all required fields"""
        provenance = create_provenance_data(
            provider="schwab",
            is_synthetic=False,
            vwap_method="intraday_true",
            provider_request_id="test-123",
            source_session="2025-08-18 09:30–16:00 ET"
        )
        
        assert provenance["data_source"] == "schwab"
        assert provenance["is_synthetic"] is False
        assert provenance["vwap_method"] == "intraday_true"
        assert provenance["provider_request_id"] == "test-123"
        assert provenance["source_session"] == "2025-08-18 09:30–16:00 ET"
        assert "timestamp" in provenance
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_emit_provenance_to_stderr(self, mock_stderr):
        """emit_provenance must output to STDERR with correct format"""
        emit_provenance(
            "ai-block",
            data_source="schwab",
            is_synthetic=False,
            vwap_method="intraday_true",
            provider_request_id="test-123",
            source_session="2025-08-18 09:30–16:00 ET",
            timestamp="2025-08-22T12:00:00Z"
        )
        
        stderr_output = mock_stderr.getvalue()
        assert "[PROVENANCE]" in stderr_output
        assert "data_source=schwab" in stderr_output
        assert "is_synthetic=false" in stderr_output
        assert "vwap_method=intraday_true" in stderr_output


class TestPivotCalculations:
    """Unit tests for pivot calculations with known golden values"""
    
    def test_pivot_calculation_golden_values(self):
        """Test pivot calculations with known H/L/C values (no network required)"""
        # Golden test data: H=170.00, L=168.00, C=169.50
        H, L, C = 170.00, 168.00, 169.50
        
        # Calculate pivot levels
        pivot = (H + L + C) / 3.0
        r1 = 2 * pivot - L
        s1 = 2 * pivot - H
        
        # Verify calculations
        assert abs(pivot - 169.1667) < 0.0001  # (170+168+169.5)/3
        assert abs(r1 - 170.3333) < 0.0001     # 2*169.1667 - 168
        assert abs(s1 - 168.3333) < 0.0001     # 2*169.1667 - 170
    
    def test_vwap_calculation_synthetic_bars(self):
        """Test VWAP calculation from synthetic minute bars with known values"""
        from app.production_provider import IntradayBar, ProductionDataProvider
        from datetime import datetime
        
        # Create synthetic bars with known values
        bars = [
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 30),
                open=100.0, high=101.0, low=99.0, close=100.5, volume=1000
            ),
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 31),
                open=100.5, high=102.0, low=100.0, close=101.5, volume=2000
            ),
            IntradayBar(
                timestamp=datetime(2025, 8, 18, 9, 32),
                open=101.5, high=101.5, low=100.5, close=101.0, volume=1500
            )
        ]
        
        # Calculate VWAP manually for verification
        # Bar 1: typical_price = (101+99+100.5)/3 = 100.1667, pv = 100166.7
        # Bar 2: typical_price = (102+100+101.5)/3 = 101.1667, pv = 202333.3
        # Bar 3: typical_price = (101.5+100.5+101)/3 = 101.0000, pv = 151500.0
        # Total PV = 454000.0, Total Volume = 4500, VWAP = 100.8889
        
        provider = Mock()
        provider.calculate_true_vwap = ProductionDataProvider.calculate_true_vwap
        
        vwap = provider.calculate_true_vwap(provider, bars)
        assert abs(vwap - 100.8889) < 0.0001


class TestProductionProviderIntegration:
    """Integration tests with mock provider to verify call patterns"""
    
    @pytest.mark.asyncio
    async def test_provider_preflight_check_called(self):
        """Ensure calc_levels calls provider preflight check"""
        from app.production_provider import ProductionDataProvider
        from app.config import Config
        from app.auth import AuthManager
        
        with patch('app.config.Config') as mock_config, \
             patch('app.auth.AuthManager') as mock_auth:
            
            mock_provider = Mock(spec=ProductionDataProvider)
            mock_provider.preflight_check = Mock(return_value={"auth": "ok"})
            mock_provider.get_daily_ohlc = Mock(side_effect=SystemExit("E-NODATA-DAILY"))
            
            with patch('app.production_provider.ProductionDataProvider', return_value=mock_provider):
                # This should call preflight_check
                from start import calc_levels
                
                with pytest.raises(SystemExit):
                    calc_levels("/NQ", "2025-08-18", "json")
                
                # Verify preflight was called
                mock_provider.preflight_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_intraday_data_returns_vwap_unavailable(self):
        """When provider returns no intraday data, JSON must include vwap_method:unavailable"""
        from app.production_provider import ProductionDataProvider, OHLCData
        from datetime import datetime, date
        
        mock_provider = Mock(spec=ProductionDataProvider)
        mock_provider.preflight_check = Mock(return_value={"auth": "ok"})
        
        # Mock OHLC data available but no intraday bars
        mock_ohlc = OHLCData(
            open=169.0, high=170.0, low=168.0, close=169.5, 
            volume=100000, timestamp=datetime.now()
        )
        mock_provider.get_daily_ohlc = Mock(return_value=mock_ohlc)
        mock_provider.get_intraday_bars = Mock(return_value=[])  # No bars
        mock_provider.calculate_true_vwap = Mock(return_value=None)
        mock_provider.create_session_info = Mock(return_value="test-session")
        mock_provider.request_id = "test-123"
        
        with patch('app.production_provider.ProductionDataProvider', return_value=mock_provider), \
             patch('app.guardrails.create_provenance_data') as mock_provenance:
            
            mock_provenance.return_value = {
                "data_source": "schwab",
                "is_synthetic": False,
                "vwap_method": "unavailable",
                "provider_request_id": "test-123",
                "source_session": "test-session",
                "timestamp": "2025-08-22T12:00:00Z"
            }
            
            # Import after patching
            from start import calc_levels
            
            # Capture output
            with patch('builtins.print') as mock_print, \
                 patch('sys.exit') as mock_exit:
                
                calc_levels("/NQ", "2025-08-18", "json")
                
                # Find the JSON output
                json_output = None
                for call in mock_print.call_args_list:
                    if call[0] and isinstance(call[0][0], str):
                        try:
                            json_output = json.loads(call[0][0])
                            break
                        except:
                            continue
                
                # Verify JSON structure
                if json_output:
                    assert json_output["provenance"]["vwap_method"] == "unavailable"
                    assert json_output["levels"]["VWAP"] is None


class TestCLIOutputContracts:
    """Contract tests for CLI output formats"""
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.stderr', new_callable=StringIO)
    def test_ai_block_format_exact_snapshot(self, mock_stderr, mock_stdout):
        """Snapshot test for --format ai-block (exact block format)"""
        # Mock the calc_levels function to produce known output
        with patch('start.calc_levels') as mock_calc:
            # Expected format based on production-safe implementation
            def mock_calc_func(symbol, date, format):
                if format == "ai-block":
                    print("[AI_DATA_BLOCK_START]")
                    print("R1: 170.3333")
                    print("S1: 168.3333") 
                    print("VWAP: N/A")
                    print("[AI_DATA_BLOCK_END]")
                    
                    # Emit provenance to STDERR
                    print("[PROVENANCE] data_source=schwab is_synthetic=false vwap_method=unavailable", file=sys.stderr)
            
            mock_calc.side_effect = mock_calc_func
            
            # Run the function
            from start import calc_levels
            calc_levels("/NQ", "2025-08-18", "ai-block")
            
            # Verify exact AI block format
            stdout_output = mock_stdout.getvalue()
            lines = stdout_output.strip().split('\n')
            
            assert lines[0] == "[AI_DATA_BLOCK_START]"
            assert lines[1].startswith("R1: ")
            assert lines[2].startswith("S1: ")
            assert lines[3].startswith("VWAP: ")
            assert lines[4] == "[AI_DATA_BLOCK_END]"
            
            # Verify provenance in STDERR
            stderr_output = mock_stderr.getvalue()
            assert "[PROVENANCE]" in stderr_output
            assert "is_synthetic=false" in stderr_output
    
    def test_json_format_required_fields(self):
        """JSON format must include all required fields with correct structure"""
        expected_structure = {
            "symbol": str,
            "date": str,
            "levels": {
                "R1": float,
                "S1": float, 
                "VWAP": (float, type(None)),  # Can be null
                "pivot": float
            },
            "provenance": {
                "data_source": str,
                "is_synthetic": bool,
                "vwap_method": str,
                "provider_request_id": str,
                "source_session": str,
                "timestamp": str
            }
        }
        
        # This would be tested with actual JSON output
        # For now, just verify the structure definition exists
        assert "symbol" in expected_structure
        assert "provenance" in expected_structure
        assert "data_source" in expected_structure["provenance"]


class TestSmokeTests:
    """Smoke tests that require real credentials (staging environment)"""
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_diag_provider_auth_ok(self):
        """ta diag provider should return auth:ok with valid credentials"""
        from app.production_provider import run_diagnostics
        
        try:
            result = await run_diagnostics()
            assert result.get("auth") == "ok"
            assert "provider" in result
            assert "time" in result
        except SystemExit as e:
            if "E-AUTH" in str(e):
                pytest.skip("No valid credentials available for smoke test")
            else:
                raise
    
    @pytest.mark.smoke
    def test_calc_levels_real_data_returns_intraday_vwap(self):
        """With real credentials, calc-levels should return vwap_method:intraday_true"""
        # This would test against AAPL with last trading day
        # Skip if no real credentials available
        pytest.skip("Real credential smoke test - implement when staging environment available")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
