import pandas as pd
from app.timesales import classify_trades, percent_at_bid_ask

def test_classify_trades_nbbo():
    trades = pd.DataFrame({
        'dt_utc':["2024-01-01T00:00:00Z","2024-01-01T00:00:01Z","2024-01-01T00:00:02Z"],
        'price':[100.0,100.5,100.2],
        'size':[10,20,30]
    })
    quotes = pd.DataFrame({
        'dt_utc':["2024-01-01T00:00:00Z","2024-01-01T00:00:01Z","2024-01-01T00:00:02Z"],
        'bid':[99.9,100.0,100.1],
        'ask':[100.4,100.6,100.3]
    })
    out = classify_trades(trades, quotes)
    assert 'label' in out.columns and out['label'].notna().all()
    a,b,m = percent_at_bid_ask(out)
    assert round(a+b+m,2) == 100.00

def test_classify_trades_tick_fallback():
    trades = pd.DataFrame({
        'dt_utc':["2024-01-01T00:00:00Z","2024-01-01T00:00:01Z"],
        'price':[100.0,100.5],
        'size':[10,20]
    })
    out = classify_trades(trades, quotes=None)
    assert set(out['confidence'].unique()) == {'tick'}
