"""
Trend Module

Berisi:

- get_htf_bias()
- get_retest_confirmation()

Seluruh implementasi dipindahkan langsung dari engine.py.

JANGAN ubah algoritma.
"""

from core.indicators import add_indicators
from core.structure import (
    detect_swings,
    detect_structure,
)

__all__ = [
    "get_htf_bias",
    "get_retest_confirmation",
]


def get_htf_bias(htf_candles):
    """Tentukan bias trend timeframe tinggi. Identik logikanya dengan versi pandas."""
    htf_candles = add_indicators(htf_candles)
    htf_candles = detect_swings(htf_candles)
    htf_candles = detect_structure(htf_candles)

    last = htf_candles[-1]
    wma_bias = "bullish" if last["wma_fast"] > last["wma_slow"] else "bearish"
    structure_bias = last["trend"] if last["trend"] else "neutral"

    if wma_bias == "bullish" and structure_bias == "up":
        bias = "bullish"
    elif wma_bias == "bearish" and structure_bias == "down":
        bias = "bearish"
    else:
        bias = "mixed"

    return {"bias": bias, "wma_bias": wma_bias, "structure_bias": structure_bias}


def get_retest_confirmation(candles, direction, ob, fvg_zone, lookback=10):
    """
    Validasi retest ke zona OB/FVG: price harus pernah menjauh dari zona,
    lalu kembali retest, baru bergerak searah sinyal. Identik logikanya
    dengan versi pandas.
    """
    if not ob and not fvg_zone:
        return True

    zone_low, zone_high = None, None
    zone_age = None
    if ob:
        zone_low, zone_high = ob["low"], ob["high"]
        zone_age = ob.get("age")
    elif fvg_zone:
        zone_low = fvg_zone.get("bottom")
        zone_high = fvg_zone.get("top")

    if zone_low is None or zone_high is None:
        return True

    if zone_age is not None and zone_age < 3:
        return False

    window_size = min(lookback, zone_age if zone_age else lookback)
    window = candles[-window_size:] if window_size > 0 else []
    if len(window) < 3:
        return False

    last_close = candles[-1]["close"]

    if direction == "BUY":
        away = any(c["low"] > zone_high for c in window)
        retested = any(c["low"] <= zone_high and c["high"] >= zone_low for c in window)
        back_in_direction = last_close >= zone_low
        return bool(away and retested and back_in_direction)
    else:
        away = any(c["high"] < zone_low for c in window)
        retested = any(c["low"] <= zone_high and c["high"] >= zone_low for c in window)
        back_in_direction = last_close <= zone_high
        return bool(away and retested and back_in_direction)
