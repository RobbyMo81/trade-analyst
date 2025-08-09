"""Data writers for parquet files with metadata and idempotency"""

import logging
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class ParquetWriter:
    """Handles writing data to parquet files with metadata and idempotency"""
    
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.data_types = ['quotes', 'historical', 'options', 'timesales']
        for data_type in self.data_types:
            (self.base_path / data_type).mkdir(exist_ok=True)
    
    async def write_data(self, 
                        data: Union[List[Dict[str, Any]], pd.DataFrame],
                        data_type: str,
                        symbol: str,
                        timestamp: Optional[datetime] = None,
                        compression: str = 'snappy',
                        partition_cols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Write data to parquet file with metadata
        
        Args:
            data: Data to write (list of dicts or DataFrame)
            data_type: Type of data (quotes, historical, options, timesales)
            symbol: Stock symbol
            timestamp: Optional timestamp for the data
            compression: Compression algorithm
            partition_cols: Optional columns for partitioning
            
        Returns:
            Dict containing write result information
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Convert data to DataFrame if needed
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            if df.empty:
                logger.warning(f"No data to write for {symbol} ({data_type})")
                return {'status': 'skipped', 'reason': 'empty_data'}
            
            # Generate content hash for idempotency
            content_hash = self._generate_content_hash(df)
            
            # Check if we've already written this exact data
            if await self._is_duplicate_data(data_type, symbol, content_hash):
                logger.info(f"Duplicate data detected for {symbol} ({data_type}), skipping write")
                return {
                    'status': 'skipped', 
                    'reason': 'duplicate_data',
                    'hash': content_hash
                }
            
            # Prepare file path
            file_info = self._generate_file_path(data_type, symbol, timestamp)
            file_path = file_info['path']
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata columns
            df = self._add_metadata_columns(df, symbol, timestamp, content_hash)
            
            # Write to parquet
            write_result = await self._write_parquet_file(df, file_path, compression, partition_cols)
            
            # Create/update metadata file
            metadata_result = await self._update_metadata_file(
                data_type, symbol, file_info, df, content_hash, timestamp
            )
            
            logger.info(f"Successfully wrote {len(df)} records to {file_path}")
            
            return {
                'status': 'success',
                'file_path': str(file_path),
                'record_count': len(df),
                'file_size_bytes': file_path.stat().st_size,
                'hash': content_hash,
                'metadata_updated': metadata_result
            }
            
        except Exception as e:
            logger.error(f"Failed to write data for {symbol} ({data_type}): {e}")
            return {
                'status': 'error',
                'error': str(e),
                'symbol': symbol,
                'data_type': data_type
            }
    
    def _generate_content_hash(self, df: pd.DataFrame) -> str:
        """Generate hash of DataFrame content for idempotency"""
        # Convert DataFrame to string representation and hash it
        content_str = df.to_csv(index=False).encode('utf-8')
        return hashlib.sha256(content_str).hexdigest()[:16]
    
    async def _is_duplicate_data(self, data_type: str, symbol: str, content_hash: str) -> bool:
        """Check if data with this hash has already been written"""
        metadata_file = self.base_path / data_type / "metadata.json"
        
        if not metadata_file.exists():
            return False
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check if this hash exists in any file
            for file_info in metadata.get('files', []):
                if file_info.get('symbol') == symbol and file_info.get('content_hash') == content_hash:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicate data: {e}")
            return False
    
    def _generate_file_path(self, data_type: str, symbol: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate file path and related information"""
        # Create date-based directory structure
        date_str = timestamp.strftime('%Y/%m/%d')
        hour_str = timestamp.strftime('%H')
        
        # Generate filename
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{timestamp_str}.parquet"
        
        # Full path
        full_path = self.base_path / data_type / date_str / filename
        
        return {
            'path': full_path,
            'relative_path': str(full_path.relative_to(self.base_path)),
            'date_str': date_str,
            'filename': filename,
            'timestamp_str': timestamp_str
        }
    
    def _add_metadata_columns(self, df: pd.DataFrame, symbol: str, timestamp: datetime, content_hash: str) -> pd.DataFrame:
        """Add metadata columns to DataFrame"""
        df = df.copy()
        
        # Add metadata if not already present
        if 'symbol' not in df.columns:
            df['symbol'] = symbol
        
        if 'write_timestamp' not in df.columns:
            df['write_timestamp'] = timestamp.isoformat()
        
        if 'content_hash' not in df.columns:
            df['content_hash'] = content_hash
        
        # Add data version
        df['data_version'] = '1.0'
        
        return df
    
    async def _write_parquet_file(self, 
                                 df: pd.DataFrame, 
                                 file_path: Path, 
                                 compression: str,
                                 partition_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Write DataFrame to parquet file"""
        try:
            # Convert to pyarrow table
            table = pa.Table.from_pandas(df)
            
            # Write parquet file
            pq.write_table(
                table, 
                file_path,
                compression=compression,
                write_statistics=True,
                use_dictionary=True
            )
            
            return {
                'success': True,
                'compression': compression,
                'columns': list(df.columns)
            }
            
        except Exception as e:
            logger.error(f"Failed to write parquet file {file_path}: {e}")
            raise
    
    async def _update_metadata_file(self, 
                                   data_type: str, 
                                   symbol: str, 
                                   file_info: Dict[str, Any], 
                                   df: pd.DataFrame,
                                   content_hash: str,
                                   timestamp: datetime) -> bool:
        """Update metadata file with new file information"""
        try:
            metadata_file = self.base_path / data_type / "metadata.json"
            
            # Load existing metadata or create new
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    'data_type': data_type,
                    'created_at': timestamp.isoformat(),
                    'schema_version': '1.0',
                    'files': []
                }
            
            # Add new file information
            file_metadata = {
                'symbol': symbol,
                'file_path': file_info['relative_path'],
                'filename': file_info['filename'],
                'timestamp': timestamp.isoformat(),
                'record_count': len(df),
                'content_hash': content_hash,
                'columns': list(df.columns),
                'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
                'file_size_bytes': 0  # Will be updated after file is written
            }
            
            # Update file size if file exists
            full_path = self.base_path / file_info['relative_path']
            if full_path.exists():
                file_metadata['file_size_bytes'] = full_path.stat().st_size
            
            metadata['files'].append(file_metadata)
            metadata['last_updated'] = timestamp.isoformat()
            metadata['total_files'] = len(metadata['files'])
            metadata['total_records'] = sum(f['record_count'] for f in metadata['files'])
            
            # Write updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata file: {e}")
            return False
    
    async def read_data(self, 
                       data_type: str, 
                       symbol: str, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Read data from parquet files
        
        Args:
            data_type: Type of data to read
            symbol: Stock symbol
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with the requested data
        """
        try:
            metadata_file = self.base_path / data_type / "metadata.json"
            
            if not metadata_file.exists():
                logger.warning(f"No metadata file found for {data_type}")
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Find relevant files
            relevant_files = []
            for file_info in metadata['files']:
                if file_info['symbol'] == symbol:
                    file_timestamp = datetime.fromisoformat(file_info['timestamp'])
                    
                    # Apply date filters
                    if start_date and file_timestamp < start_date:
                        continue
                    if end_date and file_timestamp > end_date:
                        continue
                    
                    relevant_files.append(file_info)
            
            if not relevant_files:
                logger.info(f"No files found for {symbol} in date range")
                return None
            
            # Read and combine files
            dataframes = []
            for file_info in relevant_files:
                file_path = self.base_path / file_info['file_path']
                if file_path.exists():
                    df = pd.read_parquet(file_path)
                    dataframes.append(df)
                else:
                    logger.warning(f"File not found: {file_path}")
            
            if not dataframes:
                return None
            
            # Combine all dataframes
            combined_df = pd.concat(dataframes, ignore_index=True)
            
            # Remove duplicates based on content hash
            combined_df = combined_df.drop_duplicates(subset=['content_hash'], keep='first')
            
            logger.info(f"Read {len(combined_df)} records for {symbol} ({data_type})")
            return combined_df
            
        except Exception as e:
            logger.error(f"Failed to read data for {symbol} ({data_type}): {e}")
            return None
    
    async def get_data_summary(self, data_type: str) -> Dict[str, Any]:
        """Get summary information about stored data"""
        try:
            metadata_file = self.base_path / data_type / "metadata.json"
            
            if not metadata_file.exists():
                return {
                    'data_type': data_type,
                    'total_files': 0,
                    'total_records': 0,
                    'symbols': [],
                    'date_range': None
                }
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Calculate summary statistics
            files = metadata.get('files', [])
            symbols = list(set(f['symbol'] for f in files))
            
            if files:
                timestamps = [datetime.fromisoformat(f['timestamp']) for f in files]
                date_range = {
                    'earliest': min(timestamps).isoformat(),
                    'latest': max(timestamps).isoformat()
                }
            else:
                date_range = None
            
            # Calculate storage size
            total_size = sum(f.get('file_size_bytes', 0) for f in files)
            
            return {
                'data_type': data_type,
                'total_files': len(files),
                'total_records': sum(f['record_count'] for f in files),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'symbols': sorted(symbols),
                'symbol_count': len(symbols),
                'date_range': date_range,
                'last_updated': metadata.get('last_updated')
            }
            
        except Exception as e:
            logger.error(f"Failed to get data summary for {data_type}: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_data(self, data_type: str, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up old data files"""
        try:
            cutoff_date = datetime.now() - pd.Timedelta(days=days_to_keep)
            
            metadata_file = self.base_path / data_type / "metadata.json"
            if not metadata_file.exists():
                return {'removed_files': 0, 'freed_bytes': 0}
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            files_to_remove = []
            freed_bytes = 0
            
            for file_info in metadata['files']:
                file_timestamp = datetime.fromisoformat(file_info['timestamp'])
                if file_timestamp < cutoff_date:
                    file_path = self.base_path / file_info['file_path']
                    if file_path.exists():
                        freed_bytes += file_path.stat().st_size
                        file_path.unlink()
                    files_to_remove.append(file_info)
            
            # Update metadata
            metadata['files'] = [f for f in metadata['files'] if f not in files_to_remove]
            metadata['total_files'] = len(metadata['files'])
            metadata['total_records'] = sum(f['record_count'] for f in metadata['files'])
            metadata['last_cleanup'] = datetime.now().isoformat()
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Cleaned up {len(files_to_remove)} old files, freed {freed_bytes / (1024*1024):.2f} MB")
            
            return {
                'removed_files': len(files_to_remove),
                'freed_bytes': freed_bytes,
                'freed_mb': freed_bytes / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {'error': str(e)}


# Example usage
async def main():
    """Example usage of ParquetWriter"""
    writer = ParquetWriter()
    
    # Sample data
    sample_data = [
        {
            'timestamp': '2024-01-01T10:00:00',
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 1000000
        },
        {
            'timestamp': '2024-01-01T10:01:00',
            'open': 151.0,
            'high': 153.0,
            'low': 150.0,
            'close': 152.0,
            'volume': 1100000
        }
    ]
    
    # Write data
    result = await writer.write_data(sample_data, 'historical', 'AAPL')
    print(f"Write result: {result}")
    
    # Read data back
    df = await writer.read_data('historical', 'AAPL')
    print(f"Read {len(df) if df is not None else 0} records")
    
    # Get summary
    summary = await writer.get_data_summary('historical')
    print(f"Data summary: {summary}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
