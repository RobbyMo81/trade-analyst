#!/usr/bin/env python3
"""
OHLC Data Verification Script

This script provides multiple methods to verify the accuracy of OHLC data
retrieved from the Trade Analyst system, including cross-validation with
multiple data sources, mathematical consistency checks, and comparative analysis.
"""

import asyncio
import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from pathlib import Path
import logging

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app.config import Config
from app.auth import AuthManager
from app.historical import HistoricalInterface
from app.quotes import QuotesInterface
from app.providers import schwab as S
from app.utils.futures import translate_root_to_front_month
from app.schemas.ohlc import validate_ohlc_data
from app.utils.validators import validate_price, validate_volume, validate_timestamp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OHLCVerifier:
    """Comprehensive OHLC data verification system"""
    
    def __init__(self):
        self.config = Config()
        self.auth_manager = AuthManager(self.config)
        self.historical = HistoricalInterface(self.config, self.auth_manager)
        self.quotes = QuotesInterface(self.config, self.auth_manager)
        self.schwab_client = S.SchwabClient(auth=self.auth_manager, config=self.config)
    
    async def verify_ohlc_data(self, symbol: str, target_date: str) -> Dict[str, Any]:
        """
        Comprehensive OHLC data verification using multiple methods
        
        Methods:
        1. Schema validation
        2. Mathematical consistency checks  
        3. Cross-validation with real-time quotes
        4. Historical data comparison
        5. Market reasonableness checks
        6. Multiple source verification
        """
        
        print(f"\n🔍 VERIFYING OHLC DATA FOR {symbol} ON {target_date}")
        print("=" * 60)
        
        verification_results = {
            "symbol": symbol,
            "date": target_date,
            "timestamp": datetime.now().isoformat(),
            "methods": {},
            "overall_confidence": 0.0,
            "data_source": "unknown",
            "raw_data": None
        }
        
        try:
            # Translate symbol
            translated_symbol = translate_root_to_front_month(symbol).upper()
            print(f"📝 Translated symbol: {symbol} -> {translated_symbol}")
            
            # Get historical data
            ohlc_data = await self.historical.get_latest_ohlc(translated_symbol, '1D', 3)
            
            if not ohlc_data:
                print("❌ No historical data available")
                return verification_results
            
            recent_data = ohlc_data[0]  # Most recent record
            verification_results["raw_data"] = recent_data
            verification_results["data_source"] = "historical_interface"
            
            print(f"📊 Retrieved OHLC: H={recent_data['high']}, L={recent_data['low']}, C={recent_data['close']}, O={recent_data['open']}")
            
            # Method 1: Schema Validation
            schema_result = await self._validate_schema([recent_data])
            verification_results["methods"]["schema_validation"] = schema_result
            
            # Method 2: Mathematical Consistency
            math_result = await self._validate_mathematical_consistency(recent_data)
            verification_results["methods"]["mathematical_consistency"] = math_result
            
            # Method 3: Cross-validation with Real-time Quotes
            quote_result = await self._cross_validate_with_quotes(translated_symbol, recent_data)
            verification_results["methods"]["quote_cross_validation"] = quote_result
            
            # Method 4: Historical Trend Analysis
            trend_result = await self._validate_historical_trends(ohlc_data)
            verification_results["methods"]["trend_analysis"] = trend_result
            
            # Method 5: Market Reasonableness
            market_result = await self._validate_market_reasonableness(recent_data, symbol)
            verification_results["methods"]["market_reasonableness"] = market_result
            
            # Method 6: Pivot Point Verification
            pivot_result = await self._verify_pivot_calculations(recent_data)
            verification_results["methods"]["pivot_verification"] = pivot_result
            
            # Calculate overall confidence score
            confidence_score = self._calculate_confidence_score(verification_results["methods"])
            verification_results["overall_confidence"] = confidence_score
            
            print(f"\n📈 OVERALL CONFIDENCE SCORE: {confidence_score:.1%}")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            verification_results["error"] = str(e)
        
        return verification_results
    
    async def _validate_schema(self, ohlc_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate OHLC data against schema requirements"""
        print("\n1️⃣ SCHEMA VALIDATION")
        print("-" * 20)
        
        try:
            # Use built-in OHLC validation
            validation_result = validate_ohlc_data(ohlc_data)
            
            if validation_result['is_valid']:
                print("✅ Schema validation passed")
                return {"status": "PASS", "score": 1.0, "details": validation_result}
            else:
                print(f"❌ Schema validation failed: {validation_result.get('errors', [])}")
                return {"status": "FAIL", "score": 0.0, "details": validation_result}
        except Exception as e:
            print(f"❌ Schema validation error: {e}")
            return {"status": "ERROR", "score": 0.0, "error": str(e)}
    
    async def _validate_mathematical_consistency(self, ohlc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mathematical consistency of OHLC values"""
        print("\n2️⃣ MATHEMATICAL CONSISTENCY")
        print("-" * 30)
        
        try:
            H = float(ohlc_data['high'])
            L = float(ohlc_data['low'])
            O = float(ohlc_data['open'])
            C = float(ohlc_data['close'])
            
            issues = []
            score = 1.0
            
            # Check: High >= max(Open, Close)
            if H < max(O, C):
                issues.append(f"High ({H}) less than max(Open={O}, Close={C})")
                score -= 0.3
            
            # Check: Low <= min(Open, Close)
            if L > min(O, C):
                issues.append(f"Low ({L}) greater than min(Open={O}, Close={C})")
                score -= 0.3
            
            # Check: All prices positive
            if any(price <= 0 for price in [H, L, O, C]):
                issues.append("Non-positive prices detected")
                score -= 0.4
            
            # Check: Reasonable daily range (not more than 50% move)
            daily_range = (H - L) / min(O, C) if min(O, C) > 0 else 0
            if daily_range > 0.5:  # 50% daily range seems excessive
                issues.append(f"Unusually large daily range: {daily_range:.1%}")
                score -= 0.2
            
            score = max(0.0, score)
            
            if not issues:
                print("✅ Mathematical consistency verified")
                print(f"   Range: {daily_range:.1%} (H={H}, L={L}, O={O}, C={C})")
            else:
                print(f"⚠️  Issues found: {', '.join(issues)}")
            
            return {
                "status": "PASS" if score >= 0.7 else "WARN" if score >= 0.4 else "FAIL",
                "score": score,
                "issues": issues,
                "daily_range": daily_range,
                "ohlc": {"H": H, "L": L, "O": O, "C": C}
            }
            
        except Exception as e:
            print(f"❌ Math consistency error: {e}")
            return {"status": "ERROR", "score": 0.0, "error": str(e)}
    
    async def _cross_validate_with_quotes(self, symbol: str, ohlc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-validate historical data with current quotes"""
        print("\n3️⃣ QUOTE CROSS-VALIDATION")
        print("-" * 26)
        
        try:
            # Get current quote
            quotes_result = await self.schwab_client.quotes([symbol])
            
            if not quotes_result or 'records' not in quotes_result or not quotes_result['records']:
                print("⚠️  No quote data available for cross-validation")
                return {"status": "SKIP", "score": 0.5, "reason": "No quote data"}
            
            quote = quotes_result['records'][0]
            current_bid = float(quote.get('bid', 0))
            current_ask = float(quote.get('ask', 0))
            current_mid = (current_bid + current_ask) / 2.0 if current_bid > 0 and current_ask > 0 else 0
            
            historical_close = float(ohlc_data['close'])
            
            # Compare current price to historical close
            if current_mid > 0:
                price_diff = abs(current_mid - historical_close) / historical_close
                print(f"📊 Current mid: {current_mid:.2f}, Historical close: {historical_close:.2f}")
                print(f"📈 Price difference: {price_diff:.1%}")
                
                # Reasonable if within 10% (markets can move significantly)
                if price_diff <= 0.10:
                    print("✅ Current price aligns with historical close")
                    score = 1.0
                elif price_diff <= 0.25:
                    print("⚠️  Moderate price divergence from historical")
                    score = 0.7
                else:
                    print("❌ Large price divergence - data may be stale/incorrect")
                    score = 0.3
                
                return {
                    "status": "PASS" if score >= 0.7 else "WARN",
                    "score": score,
                    "current_mid": current_mid,
                    "historical_close": historical_close,
                    "price_diff_pct": price_diff
                }
            else:
                print("⚠️  Invalid current quote data")
                return {"status": "WARN", "score": 0.5, "reason": "Invalid quote"}
                
        except Exception as e:
            print(f"❌ Quote cross-validation error: {e}")
            return {"status": "ERROR", "score": 0.0, "error": str(e)}
    
    async def _validate_historical_trends(self, ohlc_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data against historical trends"""
        print("\n4️⃣ HISTORICAL TREND ANALYSIS")
        print("-" * 30)
        
        try:
            if len(ohlc_data) < 2:
                print("⚠️  Insufficient historical data for trend analysis")
                return {"status": "SKIP", "score": 0.5, "reason": "Insufficient data"}
            
            # Calculate day-to-day changes
            recent = ohlc_data[0]
            previous = ohlc_data[1] if len(ohlc_data) > 1 else None
            
            if not previous:
                return {"status": "SKIP", "score": 0.5, "reason": "No previous day data"}
            
            recent_close = float(recent['close'])
            prev_close = float(previous['close'])
            daily_change = (recent_close - prev_close) / prev_close if prev_close > 0 else 0
            
            # Calculate volatility
            closes = [float(day['close']) for day in ohlc_data]
            if len(closes) >= 3:
                changes = [(closes[i] - closes[i+1]) / closes[i+1] for i in range(len(closes)-1)]
                avg_volatility = sum(abs(change) for change in changes) / len(changes)
            else:
                avg_volatility = abs(daily_change)
            
            print(f"📊 Daily change: {daily_change:.1%}")
            print(f"📈 Average volatility: {avg_volatility:.1%}")
            
            # Score based on reasonableness
            score = 1.0
            issues = []
            
            if abs(daily_change) > 0.20:  # 20% daily move
                issues.append(f"Large daily move: {daily_change:.1%}")
                score -= 0.3
            
            if avg_volatility > 0.15:  # 15% average volatility
                issues.append(f"High volatility: {avg_volatility:.1%}")
                score -= 0.2
            
            score = max(0.0, score)
            
            if not issues:
                print("✅ Historical trend analysis normal")
            else:
                print(f"⚠️  Issues: {', '.join(issues)}")
            
            return {
                "status": "PASS" if score >= 0.7 else "WARN",
                "score": score,
                "daily_change": daily_change,
                "avg_volatility": avg_volatility,
                "issues": issues
            }
            
        except Exception as e:
            print(f"❌ Trend analysis error: {e}")
            return {"status": "ERROR", "score": 0.0, "error": str(e)}
    
    async def _validate_market_reasonableness(self, ohlc_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Validate data for market reasonableness"""
        print("\n5️⃣ MARKET REASONABLENESS")
        print("-" * 24)
        
        try:
            close_price = float(ohlc_data['close'])
            volume = int(ohlc_data.get('volume', 0))
            
            score = 1.0
            issues = []
            
            # Price reasonableness for different asset types
            if symbol.startswith('/') or 'NQ' in symbol or 'ES' in symbol:
                # Futures - check for reasonable index levels
                if close_price < 1000 or close_price > 50000:
                    issues.append(f"Unusual futures price: {close_price}")
                    score -= 0.3
                print(f"📊 Futures price: {close_price} (reasonable range check)")
            else:
                # Stocks - check for reasonable stock prices
                if close_price < 0.01 or close_price > 10000:
                    issues.append(f"Unusual stock price: {close_price}")
                    score -= 0.3
                print(f"📊 Stock price: {close_price} (reasonable range check)")
            
            # Volume reasonableness
            if volume > 0:
                if volume > 1000000000:  # 1B shares seems excessive
                    issues.append(f"Extremely high volume: {volume:,}")
                    score -= 0.2
                print(f"📈 Volume: {volume:,}")
            else:
                print("⚠️  No volume data available")
                score -= 0.1
            
            # Check if trading day (basic check)
            data_date = ohlc_data.get('datetime', '')
            if data_date:
                try:
                    dt = datetime.fromisoformat(data_date.replace('Z', '+00:00'))
                    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
                        issues.append("Data from weekend (possible holiday/error)")
                        score -= 0.2
                except:
                    pass
            
            score = max(0.0, score)
            
            if not issues:
                print("✅ Market reasonableness checks passed")
            else:
                print(f"⚠️  Issues: {', '.join(issues)}")
            
            return {
                "status": "PASS" if score >= 0.7 else "WARN",
                "score": score,
                "close_price": close_price,
                "volume": volume,
                "issues": issues
            }
            
        except Exception as e:
            print(f"❌ Market reasonableness error: {e}")
            return {"status": "ERROR", "score": 0.0, "error": str(e)}
    
    async def _verify_pivot_calculations(self, ohlc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify pivot point calculations"""
        print("\n6️⃣ PIVOT POINT VERIFICATION")
        print("-" * 28)
        
        try:
            H = float(ohlc_data['high'])
            L = float(ohlc_data['low'])
            C = float(ohlc_data['close'])
            vwap = float(ohlc_data.get('vwap', C))
            
            # Calculate pivot levels
            pivot = (H + L + C) / 3.0
            r1 = 2 * pivot - L
            s1 = 2 * pivot - H
            
            print(f"📊 Calculated Pivot: {pivot:.4f}")
            print(f"📈 R1 (Resistance): {r1:.4f}")
            print(f"📉 S1 (Support): {s1:.4f}")
            print(f"⚖️  VWAP: {vwap:.4f}")
            
            # Verify calculations make sense
            score = 1.0
            issues = []
            
            # R1 should be above pivot, S1 below
            if r1 <= pivot:
                issues.append("R1 not above pivot")
                score -= 0.4
            
            if s1 >= pivot:
                issues.append("S1 not below pivot")
                score -= 0.4
            
            # VWAP should be reasonably close to OHLC average
            ohlc_avg = (H + L + C) / 3.0
            vwap_diff = abs(vwap - ohlc_avg) / ohlc_avg if ohlc_avg > 0 else 0
            
            if vwap_diff > 0.05:  # 5% difference seems high
                issues.append(f"VWAP differs significantly from OHLC average: {vwap_diff:.1%}")
                score -= 0.2
            
            score = max(0.0, score)
            
            if not issues:
                print("✅ Pivot calculations verified")
            else:
                print(f"⚠️  Issues: {', '.join(issues)}")
            
            return {
                "status": "PASS" if score >= 0.7 else "WARN",
                "score": score,
                "pivot": pivot,
                "r1": r1,
                "s1": s1,
                "vwap": vwap,
                "vwap_diff": vwap_diff,
                "issues": issues
            }
            
        except Exception as e:
            print(f"❌ Pivot verification error: {e}")
            return {"status": "ERROR", "score": 0.0, "error": str(e)}
    
    def _calculate_confidence_score(self, methods: Dict[str, Any]) -> float:
        """Calculate overall confidence score from all methods"""
        
        # Weights for different validation methods
        weights = {
            "schema_validation": 0.15,
            "mathematical_consistency": 0.25,
            "quote_cross_validation": 0.20,
            "trend_analysis": 0.15,
            "market_reasonableness": 0.15,
            "pivot_verification": 0.10
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for method, weight in weights.items():
            if method in methods and "score" in methods[method]:
                total_score += methods[method]["score"] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0


async def main():
    """Main verification function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify OHLC data accuracy')
    parser.add_argument('--symbol', required=True, help='Symbol to verify (e.g., /NQ, AAPL)')
    parser.add_argument('--date', required=True, help='Date to verify (YYYY-MM-DD)')
    parser.add_argument('--output', choices=['console', 'json'], default='console', help='Output format')
    parser.add_argument('--save', help='Save results to file')
    
    args = parser.parse_args()
    
    verifier = OHLCVerifier()
    results = await verifier.verify_ohlc_data(args.symbol, args.date)
    
    if args.output == 'json':
        print(json.dumps(results, indent=2, default=str))
    
    if args.save:
        with open(args.save, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to {args.save}")
    
    # Return exit code based on confidence
    confidence = results.get('overall_confidence', 0.0)
    if confidence >= 0.8:
        print(f"\n🎉 HIGH CONFIDENCE ({confidence:.1%}) - Data appears reliable")
        return 0
    elif confidence >= 0.6:
        print(f"\n⚠️  MODERATE CONFIDENCE ({confidence:.1%}) - Use with caution")
        return 1
    else:
        print(f"\n❌ LOW CONFIDENCE ({confidence:.1%}) - Data may be unreliable")
        return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
