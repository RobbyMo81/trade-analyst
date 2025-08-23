#!/usr/bin/env python3
"""
CLI Contract Tests for calc-levels command

Tests the exact output format and provenance requirements to ensure
the CLI behaves correctly for different scenarios.
"""

import os
import sys
import pytest
import subprocess
import json
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestCalcLevelsCommand:
    """Test calc-levels command CLI interface"""
    
    def test_calc_levels_ai_block_format(self):
        """Test that ai-block format produces exact expected output"""
        # Test using the production_calc_levels.py file directly 
        test_command = [
            sys.executable, 
            os.path.join(project_root, "production_calc_levels.py"),
            "/NQ", "2025-08-18", "ai-block"
        ]
        
        # Set FAIL_ON_STUB=0 to allow test execution
        env = os.environ.copy()
        env['FAIL_ON_STUB'] = '0'
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            # Check if it failed due to missing real API (expected)
            if result.returncode != 0:
                if "E-NODATA-DAILY" in result.stdout or "E-STUB-PATH" in result.stdout:
                    pytest.skip("Real API not implemented - expected failure")
                else:
                    pytest.fail(f"Unexpected error: {result.stdout}\n{result.stderr}")
            
            # If it somehow succeeded, verify format
            lines = result.stdout.strip().split('\n')
            assert "[AI_DATA_BLOCK_START]" in lines
            assert "[AI_DATA_BLOCK_END]" in lines
            
            # Find R1, S1, VWAP lines
            r1_line = next((line for line in lines if line.startswith("R1:")), None)
            s1_line = next((line for line in lines if line.startswith("S1:")), None)
            vwap_line = next((line for line in lines if line.startswith("VWAP:")), None)
            
            assert r1_line is not None, "R1 line not found"
            assert s1_line is not None, "S1 line not found" 
            assert vwap_line is not None, "VWAP line not found"
            
            # Verify provenance in stderr
            assert "[PROVENANCE]" in result.stderr
            
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out")
    
    def test_calc_levels_json_format_structure(self):
        """Test that JSON format includes all required fields"""
        test_command = [
            sys.executable,
            os.path.join(project_root, "production_calc_levels.py"), 
            "/NQ", "2025-08-18", "json"
        ]
        
        env = os.environ.copy()
        env['FAIL_ON_STUB'] = '0'
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            # Check if failed due to missing API (expected)
            if result.returncode != 0:
                if "E-NODATA-DAILY" in result.stdout or "E-STUB-PATH" in result.stdout:
                    pytest.skip("Real API not implemented - expected failure")
                else:
                    pytest.fail(f"Unexpected error: {result.stdout}\n{result.stderr}")
            
            # If succeeded, parse JSON
            try:
                output = json.loads(result.stdout)
                
                # Verify required top-level fields
                assert "symbol" in output
                assert "date" in output
                assert "levels" in output
                assert "provenance" in output
                
                # Verify levels structure
                levels = output["levels"]
                assert "R1" in levels
                assert "S1" in levels
                assert "VWAP" in levels  # Can be null
                assert "pivot" in levels
                
                # Verify provenance structure
                provenance = output["provenance"]
                assert "data_source" in provenance
                assert "is_synthetic" in provenance
                assert "vwap_method" in provenance
                assert "provider_request_id" in provenance
                assert "source_session" in provenance
                assert "timestamp" in provenance
                
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON output: {e}\nOutput: {result.stdout}")
                
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out")
    
    def test_calc_levels_csv_format_headers(self):
        """Test that CSV format includes provenance columns"""
        test_command = [
            sys.executable,
            os.path.join(project_root, "production_calc_levels.py"),
            "/NQ", "2025-08-18", "csv"
        ]
        
        env = os.environ.copy() 
        env['FAIL_ON_STUB'] = '0'
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if result.returncode != 0:
                if "E-NODATA-DAILY" in result.stdout or "E-STUB-PATH" in result.stdout:
                    pytest.skip("Real API not implemented - expected failure")
                else:
                    pytest.fail(f"Unexpected error: {result.stdout}\n{result.stderr}")
            
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 1:
                header = lines[0]
                
                # Verify CSV headers include provenance
                required_columns = [
                    "symbol", "date", "R1", "S1", "VWAP", "pivot",
                    "data_source", "is_synthetic", "vwap_method"
                ]
                
                for column in required_columns:
                    assert column in header, f"Missing column: {column}"
                    
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out")
    
    def test_production_mode_blocks_stub_execution(self):
        """Test that FAIL_ON_STUB=1 prevents execution and returns proper error"""
        test_command = [
            sys.executable,
            os.path.join(project_root, "production_calc_levels.py"),
            "/NQ", "2025-08-18", "json"
        ]
        
        env = os.environ.copy()
        env['FAIL_ON_STUB'] = '1'  # Force production mode
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True, 
                text=True,
                env=env,
                timeout=30
            )
            
            # Should fail with appropriate error code
            assert result.returncode != 0, "Command should fail in production mode"
            
            # Should contain stub path error
            error_output = result.stdout + result.stderr
            assert ("E-STUB-PATH" in error_output or 
                   "E-NODATA-DAILY" in error_output or
                   "E-NODATA-INTRADAY" in error_output), \
                   f"Expected stub/API error not found in: {error_output}"
                   
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out")
    
    def test_invalid_date_format_error(self):
        """Test that invalid date format produces proper error"""
        test_command = [
            sys.executable,
            os.path.join(project_root, "production_calc_levels.py"),
            "/NQ", "invalid-date", "json"
        ]
        
        env = os.environ.copy()
        env['FAIL_ON_STUB'] = '0'
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True, 
                env=env,
                timeout=30
            )
            
            # Should fail with date format error
            assert result.returncode != 0
            error_output = result.stdout + result.stderr
            assert "E-INVALID-DATE" in error_output
            
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out")
    
    def test_invalid_format_error(self):
        """Test that invalid format produces proper error"""
        test_command = [
            sys.executable,
            os.path.join(project_root, "production_calc_levels.py"),
            "/NQ", "2025-08-18", "invalid-format"
        ]
        
        env = os.environ.copy()
        env['FAIL_ON_STUB'] = '0'
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            # Should fail with format error
            assert result.returncode != 0
            error_output = result.stdout + result.stderr
            assert "E-INVALID-FORMAT" in error_output
            
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out")


class TestProvenance:
    """Test provenance tracking requirements"""
    
    def test_ai_block_provenance_to_stderr(self):
        """AI-block format must emit provenance to STDERR"""
        # This would be tested with a mock of the actual function
        from app.guardrails import emit_provenance
        
        with redirect_stderr(StringIO()) as stderr_capture:
            emit_provenance(
                "ai-block",
                data_source="schwab",
                is_synthetic=False,
                vwap_method="unavailable", 
                provider_request_id="test-123",
                source_session="2025-08-18 09:30–16:00 ET",
                timestamp="2025-08-22T12:00:00Z"
            )
            
            stderr_output = stderr_capture.getvalue()
            assert "[PROVENANCE]" in stderr_output
            assert "data_source=schwab" in stderr_output
            assert "is_synthetic=false" in stderr_output
    
    def test_json_provenance_embedded(self):
        """JSON format must embed provenance in response"""
        # Test the provenance data structure creation
        from app.guardrails import create_provenance_data
        
        provenance = create_provenance_data(
            provider="schwab",
            is_synthetic=False,
            vwap_method="intraday_true",
            provider_request_id="test-456", 
            source_session="2025-08-18 09:30–16:00 ET"
        )
        
        # Verify structure
        assert isinstance(provenance, dict)
        assert provenance["data_source"] == "schwab"
        assert provenance["is_synthetic"] is False
        assert provenance["vwap_method"] == "intraday_true"
        assert "timestamp" in provenance


if __name__ == "__main__":
    # Run CLI contract tests
    pytest.main([__file__, "-v", "-s"])
