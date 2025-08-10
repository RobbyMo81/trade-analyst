"""Exporter demo modules wiring metrics & time & sales classification.

These are demonstration exporters showing how to hook:
  * IV rank / percentile
  * Put/Call Ratios (volume & open interest)
  * % traded at bid / ask / mid & classification confidence

They currently operate on synthetic data if no real provider feed is wired yet.
Replace the synthetic data builders with real provider fetches (e.g. SchwabClient) once live.
"""

from .options_stats import build_options_stats
from .timesales_stats import build_timesales_metrics

__all__ = ["build_options_stats", "build_timesales_metrics"]
