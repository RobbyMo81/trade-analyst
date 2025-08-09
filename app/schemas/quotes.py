"""Quotes data schema definitions and helpers.

Provides validation, normalization, DataFrame creation, and basic metrics
for real-time quote snapshots. Mirrors design of other schema modules.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
import pandas as pd

@dataclass
class QuoteRecord:
    symbol: str
    bid: float
    ask: float
    bid_size: int | None = None
    ask_size: int | None = None
    timestamp: datetime | str | None = None

QUOTE_SCHEMA = {
    'symbol': 'string',
    'bid': 'float64',
    'ask': 'float64',
    'bid_size': 'Int64',
    'ask_size': 'Int64',
    'timestamp': 'datetime64[ns]'
}

REQUIRED_QUOTE_FIELDS = ['symbol', 'bid', 'ask', 'timestamp']
OPTIONAL_QUOTE_FIELDS = ['bid_size', 'ask_size']

def validate_quote_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'record_count': len(data)
    }
    if not data:
        result['errors'].append('No data provided')
        result['is_valid'] = False
        return result
    for i, record in enumerate(data):
        for field in REQUIRED_QUOTE_FIELDS:
            if field not in record or record[field] in (None, ''):
                result['errors'].append(f"Record {i}: Missing required field '{field}'")
                result['is_valid'] = False
        try:
            if 'bid' in record and float(record['bid']) <= 0:
                result['errors'].append(f"Record {i}: Bid must be positive")
                result['is_valid'] = False
            if 'ask' in record and float(record['ask']) <= 0:
                result['errors'].append(f"Record {i}: Ask must be positive")
                result['is_valid'] = False
            if 'bid' in record and 'ask' in record and float(record['bid']) > float(record['ask']):
                result['warnings'].append(f"Record {i}: Bid > Ask spread inversion")
        except (TypeError, ValueError):
            result['errors'].append(f"Record {i}: Non-numeric bid/ask")
            result['is_valid'] = False
        for size_field in ['bid_size', 'ask_size']:
            if size_field in record and record[size_field] is not None:
                try:
                    sz = int(record[size_field])
                    if sz < 0:
                        result['warnings'].append(f"Record {i}: {size_field} negative")
                except (TypeError, ValueError):
                    result['warnings'].append(f"Record {i}: {size_field} not integer")
        if 'timestamp' in record and record['timestamp'] not in (None, ''):
            if not isinstance(record['timestamp'], (str, datetime)):
                result['errors'].append(f"Record {i}: Invalid timestamp type")
                result['is_valid'] = False
    return result

def normalize_quote_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for record in data:
        norm: Dict[str, Any] = {}
        for field in REQUIRED_QUOTE_FIELDS + OPTIONAL_QUOTE_FIELDS:
            if field in record and record[field] is not None:
                if field in ('bid', 'ask'):
                    try:
                        norm[field] = float(record[field])
                    except (TypeError, ValueError):
                        continue
                elif field in ('bid_size', 'ask_size'):
                    try:
                        norm[field] = int(record[field])
                    except (TypeError, ValueError):
                        norm[field] = None
                elif field == 'timestamp':
                    ts = record[field]
                    norm[field] = ts.isoformat() if isinstance(ts, datetime) else ts
                else:
                    norm[field] = record[field]
        normalized.append(norm)
    return normalized

def create_quotes_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    if not data:
        df = pd.DataFrame(columns=list(QUOTE_SCHEMA.keys()))
        return df.astype(QUOTE_SCHEMA)
    df = pd.DataFrame(data)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    for col, dtype in QUOTE_SCHEMA.items():
        target_dtype = 'string' if dtype == 'string' else dtype  # explicit mapping for type checkers
        if col in df.columns:
            try:
                df[col] = df[col].astype(target_dtype)  # type: ignore[arg-type]
            except Exception:
                pass
        else:
            df[col] = pd.Series([None] * len(df), dtype=target_dtype)
    return df

def calculate_quote_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {'record_count': 0, 'unique_symbols': 0}
    metrics: Dict[str, Any] = {
        'record_count': int(len(df)),
        'unique_symbols': int(df['symbol'].nunique()) if 'symbol' in df else 0,
    }
    if {'bid', 'ask'}.issubset(df.columns):
        try:
            spread = df['ask'] - df['bid']
            metrics['spread'] = {
                'mean': float(spread.mean()),
                'min': float(spread.min()),
                'max': float(spread.max())
            }
        except Exception:
            pass
    return metrics

__all__ = [
    'QuoteRecord',
    'QUOTE_SCHEMA',
    'validate_quote_data',
    'normalize_quote_data',
    'create_quotes_dataframe',
    'calculate_quote_metrics'
]
