import pandas as pd
from app.metrics import iv_rank_and_percentile, calculate_put_call_volume_ratio, calculate_put_call_oi_ratio

def test_iv_rank_and_percentile_basic():
    s = pd.Series([0.20, 0.25, 0.30, 0.22])
    rank, pct = iv_rank_and_percentile(s, window=10)
    assert pct is not None and 0 <= pct <= 100

def test_iv_rank_insufficient_history():
    s = pd.Series([0.25])
    rank, pct = iv_rank_and_percentile(s)
    assert rank is None and pct is None

def test_put_call_volume_ratio():
    df = pd.DataFrame({
        'option_type':['call','call','put','put'],
        'volume':[100,200,50,150]
    })
    pcr = calculate_put_call_volume_ratio(df)
    assert pcr == (50+150)/(100+200)

def test_put_call_oi_ratio_calls_zero():
    df = pd.DataFrame({'option_type':['put'], 'open_interest':[100]})
    assert calculate_put_call_oi_ratio(df) is None
