"""Time & Sales classification utilities."""
from .bidask_classifier import classify_trades, percent_at_bid_ask
import pandas as _pd

def aggregate_trade_classification_confidence(df: _pd.DataFrame, size_col: str = 'size') -> str:
	if df is None or df.empty or 'confidence' not in df.columns:
		return 'unknown'
	if size_col not in df.columns:
		sizes = _pd.Series(1, index=df.index)
	else:
		sizes = _pd.to_numeric(df[size_col], errors='coerce').fillna(0)
	weights = sizes.groupby(df['confidence']).sum()
	if weights.empty:
		return 'unknown'
	if len(weights) == 1:
		return str(weights.index[0])
	# Mixed (some nbbo some tick)
	return 'mixed'

__all__ = ["classify_trades", "percent_at_bid_ask", "aggregate_trade_classification_confidence"]
