import asyncio
import json
import pandas as pd
from pathlib import Path
from app.writers import ParquetWriter

async def _write_and_check(tmp_path: Path):
    base = tmp_path / 'data_store'
    writer = ParquetWriter(base_path=str(base))
    df = pd.DataFrame({'timestamp':['2024-01-01T00:00:00'],'open':[1.0],'high':[1.5],'low':[0.9],'close':[1.2],'volume':[100]})
    res1 = await writer.write_data(df, data_type='historical', symbol='AAPL')
    assert res1['status'] == 'success'
    meta_file = base / 'historical' / 'metadata.json'
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text())
    assert meta['total_files'] == 1
    # duplicate write
    res2 = await writer.write_data(df, data_type='historical', symbol='AAPL')
    assert res2['status'] == 'skipped' and res2['reason'] == 'duplicate_data'
    meta_after = json.loads(meta_file.read_text())
    assert meta_after['total_files'] == 1


def test_parquet_writer_metadata(tmp_path):
    asyncio.run(_write_and_check(tmp_path))
