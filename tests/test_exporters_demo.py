import pytest
from app.config import load_config
from app.exporters import build_options_stats, build_timesales_metrics

def test_build_options_stats_demo():
    cfg = load_config()
    stats = build_options_stats(cfg)
    assert 'iv_rank' in stats and 'put_call_ratio' in stats

def test_build_timesales_metrics_demo():
    cfg = load_config()
    m = build_timesales_metrics(cfg)
    assert set(['pct_at_ask','pct_at_bid','pct_at_mid']).issubset(m.keys())
    assert m['trade_count'] > 0
