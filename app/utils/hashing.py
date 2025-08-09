"""Content hashing utilities for data integrity and deduplication"""

import hashlib
import json
from typing import Any, Dict, List, Union, Optional
import pandas as pd
from datetime import datetime
import pickle
import logging

logger = logging.getLogger(__name__)


def hash_string(data: str, algorithm: str = 'sha256') -> str:
    """
    Hash a string using specified algorithm
    
    Args:
        data: String to hash
        algorithm: Hashing algorithm ('md5', 'sha1', 'sha256', 'sha512')
        
    Returns:
        Hexadecimal hash string
    """
    if algorithm == 'md5':
        hasher = hashlib.md5()
    elif algorithm == 'sha1':
        hasher = hashlib.sha1()
    elif algorithm == 'sha256':
        hasher = hashlib.sha256()
    elif algorithm == 'sha512':
        hasher = hashlib.sha512()
    else:
        raise ValueError(f"Unsupported hashing algorithm: {algorithm}")
    
    hasher.update(data.encode('utf-8'))
    return hasher.hexdigest()


def hash_dict(data: Dict[str, Any], algorithm: str = 'sha256', 
              exclude_keys: Optional[List[str]] = None) -> str:
    """
    Hash a dictionary by converting to deterministic JSON string
    
    Args:
        data: Dictionary to hash
        algorithm: Hashing algorithm
        exclude_keys: Keys to exclude from hashing
        
    Returns:
        Hexadecimal hash string
    """
    if exclude_keys:
        # Create copy without excluded keys
        data_copy = {k: v for k, v in data.items() if k not in exclude_keys}
    else:
        data_copy = data
    
    # Convert to deterministic JSON string
    json_string = json.dumps(data_copy, sort_keys=True, separators=(',', ':'), default=str)
    return hash_string(json_string, algorithm)


def hash_list(data: List[Any], algorithm: str = 'sha256') -> str:
    """
    Hash a list by converting to deterministic JSON string
    
    Args:
        data: List to hash
        algorithm: Hashing algorithm
        
    Returns:
        Hexadecimal hash string
    """
    json_string = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
    return hash_string(json_string, algorithm)


def hash_dataframe(df: pd.DataFrame, algorithm: str = 'sha256',
                   exclude_columns: Optional[List[str]] = None) -> str:
    """
    Hash a pandas DataFrame
    
    Args:
        df: DataFrame to hash
        algorithm: Hashing algorithm
        exclude_columns: Columns to exclude from hashing
        
    Returns:
        Hexadecimal hash string
    """
    if df.empty:
        return hash_string("", algorithm)
    
    # Create copy and exclude specified columns
    df_copy = df.copy()
    if exclude_columns:
        df_copy = df_copy.drop(columns=[col for col in exclude_columns if col in df_copy.columns])
    
    # Sort by all columns to ensure deterministic order
    try:
        df_sorted = df_copy.sort_values(by=list(df_copy.columns))
    except TypeError:
        # If sorting fails (mixed types), use index order
        df_sorted = df_copy
    
    # Convert to JSON with deterministic ordering
    json_string = df_sorted.to_json(orient='records', sort_keys=True, date_format='iso')
    return hash_string(json_string, algorithm)


def hash_file(file_path: str, algorithm: str = 'sha256', chunk_size: int = 8192) -> str:
    """
    Hash a file's contents
    
    Args:
        file_path: Path to file
        algorithm: Hashing algorithm
        chunk_size: Size of chunks to read
        
    Returns:
        Hexadecimal hash string
    """
    if algorithm == 'md5':
        hasher = hashlib.md5()
    elif algorithm == 'sha1':
        hasher = hashlib.sha1()
    elif algorithm == 'sha256':
        hasher = hashlib.sha256()
    elif algorithm == 'sha512':
        hasher = hashlib.sha512()
    else:
        raise ValueError(f"Unsupported hashing algorithm: {algorithm}")
    
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}")
        raise


def create_content_hash(data: Any, algorithm: str = 'sha256') -> str:
    """
    Create a content hash for various data types
    
    Args:
        data: Data to hash (str, dict, list, DataFrame, etc.)
        algorithm: Hashing algorithm
        
    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, str):
        return hash_string(data, algorithm)
    elif isinstance(data, dict):
        return hash_dict(data, algorithm)
    elif isinstance(data, list):
        return hash_list(data, algorithm)
    elif isinstance(data, pd.DataFrame):
        return hash_dataframe(data, algorithm)
    else:
        # For other types, use pickle and hash the bytes
        try:
            pickled_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            hasher = getattr(hashlib, algorithm)()
            hasher.update(pickled_data)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing data type {type(data)}: {e}")
            # Fallback to string representation
            return hash_string(str(data), algorithm)


def generate_trade_hash(trade_data: Dict[str, Any]) -> str:
    """
    Generate a unique hash for trade data
    
    Args:
        trade_data: Trade record dictionary
        
    Returns:
        Unique trade hash
    """
    # Include key fields that make a trade unique
    key_fields = ['symbol', 'timestamp', 'price', 'size', 'exchange']
    
    trade_key = {}
    for field in key_fields:
        if field in trade_data:
            trade_key[field] = trade_data[field]
    
    return hash_dict(trade_key, algorithm='sha256')


def generate_quote_hash(quote_data: Dict[str, Any]) -> str:
    """
    Generate a unique hash for quote data
    
    Args:
        quote_data: Quote record dictionary
        
    Returns:
        Unique quote hash
    """
    # Include key fields that make a quote unique
    key_fields = ['symbol', 'timestamp', 'bid', 'ask', 'bid_size', 'ask_size']
    
    quote_key = {}
    for field in key_fields:
        if field in quote_data:
            quote_key[field] = quote_data[field]
    
    return hash_dict(quote_key, algorithm='sha256')


def generate_ohlc_hash(ohlc_data: Dict[str, Any]) -> str:
    """
    Generate a unique hash for OHLC data
    
    Args:
        ohlc_data: OHLC record dictionary
        
    Returns:
        Unique OHLC hash
    """
    # Include key fields that make an OHLC bar unique
    key_fields = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    ohlc_key = {}
    for field in key_fields:
        if field in ohlc_data:
            ohlc_key[field] = ohlc_data[field]
    
    return hash_dict(ohlc_key, algorithm='sha256')


def generate_option_hash(option_data: Dict[str, Any]) -> str:
    """
    Generate a unique hash for option data
    
    Args:
        option_data: Option record dictionary
        
    Returns:
        Unique option hash
    """
    # Include key fields that make an option quote unique
    key_fields = ['symbol', 'underlying_symbol', 'strike', 'expiration', 
                  'option_type', 'timestamp', 'bid', 'ask']
    
    option_key = {}
    for field in key_fields:
        if field in option_data:
            option_key[field] = option_data[field]
    
    return hash_dict(option_key, algorithm='sha256')


def batch_hash_records(records: List[Dict[str, Any]], 
                      hash_func: callable = create_content_hash) -> List[str]:
    """
    Generate hashes for a batch of records
    
    Args:
        records: List of record dictionaries
        hash_func: Function to use for hashing
        
    Returns:
        List of hash strings
    """
    hashes = []
    for record in records:
        try:
            record_hash = hash_func(record)
            hashes.append(record_hash)
        except Exception as e:
            logger.warning(f"Failed to hash record: {e}")
            hashes.append(None)
    
    return hashes


def find_duplicate_hashes(hashes: List[str]) -> Dict[str, List[int]]:
    """
    Find duplicate hashes and their indices
    
    Args:
        hashes: List of hash strings
        
    Returns:
        Dictionary mapping hash to list of indices
    """
    hash_map = {}
    for i, hash_value in enumerate(hashes):
        if hash_value is not None:
            if hash_value not in hash_map:
                hash_map[hash_value] = []
            hash_map[hash_value].append(i)
    
    # Return only duplicates
    return {h: indices for h, indices in hash_map.items() if len(indices) > 1}


def remove_duplicate_records(records: List[Dict[str, Any]],
                           hash_func: callable = create_content_hash) -> List[Dict[str, Any]]:
    """
    Remove duplicate records based on content hash
    
    Args:
        records: List of record dictionaries
        hash_func: Function to use for hashing
        
    Returns:
        List of unique records
    """
    seen_hashes = set()
    unique_records = []
    
    for record in records:
        try:
            record_hash = hash_func(record)
            if record_hash not in seen_hashes:
                seen_hashes.add(record_hash)
                unique_records.append(record)
        except Exception as e:
            logger.warning(f"Failed to hash record, keeping anyway: {e}")
            unique_records.append(record)
    
    return unique_records


def verify_data_integrity(original_data: Any, stored_hash: str,
                         algorithm: str = 'sha256') -> bool:
    """
    Verify data integrity by comparing hashes
    
    Args:
        original_data: Original data to verify
        stored_hash: Previously computed hash
        algorithm: Hashing algorithm used
        
    Returns:
        True if hashes match (data integrity verified)
    """
    try:
        current_hash = create_content_hash(original_data, algorithm)
        return current_hash == stored_hash
    except Exception as e:
        logger.error(f"Error verifying data integrity: {e}")
        return False


class HashManager:
    """Manager for content hashing operations"""
    
    def __init__(self, algorithm: str = 'sha256'):
        """
        Initialize hash manager
        
        Args:
            algorithm: Default hashing algorithm
        """
        self.algorithm = algorithm
        self.hash_cache = {}
    
    def hash_data(self, data: Any, use_cache: bool = True) -> str:
        """
        Hash data with optional caching
        
        Args:
            data: Data to hash
            use_cache: Whether to use hash cache
            
        Returns:
            Hash string
        """
        if use_cache:
            # Create a simple cache key
            cache_key = str(type(data)) + str(hash(str(data)))
            
            if cache_key in self.hash_cache:
                return self.hash_cache[cache_key]
        
        data_hash = create_content_hash(data, self.algorithm)
        
        if use_cache:
            self.hash_cache[cache_key] = data_hash
        
        return data_hash
    
    def clear_cache(self):
        """Clear the hash cache"""
        self.hash_cache.clear()
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.hash_cache)


class DataIntegrityChecker:
    """Data integrity checker using hashes"""
    
    def __init__(self, algorithm: str = 'sha256'):
        """
        Initialize integrity checker
        
        Args:
            algorithm: Hashing algorithm to use
        """
        self.algorithm = algorithm
        self.integrity_log = []
    
    def store_hash(self, data: Any, identifier: str) -> str:
        """
        Store hash for data with identifier
        
        Args:
            data: Data to hash and store
            identifier: Unique identifier for the data
            
        Returns:
            Generated hash
        """
        data_hash = create_content_hash(data, self.algorithm)
        
        self.integrity_log.append({
            'identifier': identifier,
            'hash': data_hash,
            'timestamp': datetime.now().isoformat(),
            'data_type': str(type(data))
        })
        
        return data_hash
    
    def verify_integrity(self, data: Any, identifier: str) -> bool:
        """
        Verify data integrity against stored hash
        
        Args:
            data: Data to verify
            identifier: Identifier to look up stored hash
            
        Returns:
            True if integrity verified
        """
        # Find stored hash
        stored_entry = None
        for entry in self.integrity_log:
            if entry['identifier'] == identifier:
                stored_entry = entry
                break
        
        if not stored_entry:
            logger.warning(f"No stored hash found for identifier: {identifier}")
            return False
        
        return verify_data_integrity(data, stored_entry['hash'], self.algorithm)
    
    def get_integrity_report(self) -> List[Dict[str, Any]]:
        """Get integrity log report"""
        return self.integrity_log.copy()


# Utility functions for specific data types
def hash_trade_batch(trades: List[Dict[str, Any]]) -> List[str]:
    """Hash a batch of trade records"""
    return batch_hash_records(trades, generate_trade_hash)


def hash_quote_batch(quotes: List[Dict[str, Any]]) -> List[str]:
    """Hash a batch of quote records"""
    return batch_hash_records(quotes, generate_quote_hash)


def hash_ohlc_batch(ohlc_data: List[Dict[str, Any]]) -> List[str]:
    """Hash a batch of OHLC records"""
    return batch_hash_records(ohlc_data, generate_ohlc_hash)


def hash_option_batch(options: List[Dict[str, Any]]) -> List[str]:
    """Hash a batch of option records"""
    return batch_hash_records(options, generate_option_hash)


# Example usage
def example_hashing_usage():
    """Example usage of hashing utilities"""
    
    # Sample data
    trade_data = {
        'symbol': 'AAPL',
        'timestamp': '2024-01-01T10:00:00',
        'price': 150.25,
        'size': 100,
        'exchange': 'NASDAQ'
    }
    
    quote_data = {
        'symbol': 'AAPL',
        'timestamp': '2024-01-01T10:00:00',
        'bid': 150.20,
        'ask': 150.25,
        'bid_size': 1000,
        'ask_size': 800
    }
    
    # Generate hashes
    trade_hash = generate_trade_hash(trade_data)
    quote_hash = generate_quote_hash(quote_data)
    
    print(f"Trade hash: {trade_hash}")
    print(f"Quote hash: {quote_hash}")
    
    # Hash manager example
    hash_manager = HashManager()
    
    data_hash = hash_manager.hash_data(trade_data)
    print(f"Managed hash: {data_hash}")
    print(f"Cache size: {hash_manager.get_cache_size()}")
    
    # Integrity checker example
    integrity_checker = DataIntegrityChecker()
    
    stored_hash = integrity_checker.store_hash(trade_data, "trade_001")
    is_valid = integrity_checker.verify_integrity(trade_data, "trade_001")
    
    print(f"Stored hash: {stored_hash}")
    print(f"Integrity verified: {is_valid}")
    
    # Duplicate detection
    trades = [trade_data, trade_data.copy(), quote_data]  # One duplicate
    unique_trades = remove_duplicate_records(trades)
    print(f"Original count: {len(trades)}, Unique count: {len(unique_trades)}")


if __name__ == "__main__":
    example_hashing_usage()
