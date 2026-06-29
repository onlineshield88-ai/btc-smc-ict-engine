"""
Order Block Module

Seluruh implementasi dipindahkan langsung dari engine.py.
Jangan ubah algoritma.
"""

from core.indicators import (
    _rolling_mean,
)

__all__ = [
    "detect_orderblock",
    "_nearest_unmitigated",
]


def detect_orderblock(candles, body_mult=1.5, avg_window=20, max_age=30):
    """Deteksi Order Block tervalidasi impulsive leg. Identik logikanya dengan versi pandas."""
    n = len(candles)
    bodies = [abs(c["close"] - c["open"]) for c in candles]
    avg_body = _rolling_mean(bodies, avg_window)

    bullish_obs = []
    bearish_obs = []

    for i in range(avg_window, n - 1):
        threshold = avg_body[i]
        if threshold is None:
            continue
        threshold *= body_mult

        body_next = abs(candles[i + 1]["close"] - candles[i + 1]["open"])

        is_bearish_candle = candles[i]["close"] < candles[i]["open"]
        is_bullish_candle = candles[i]["close"] > candles[i]["open"]
        next_bullish = candles[i + 1]["close"] > candles[i + 1]["open"]
        next_bearish = candles[i + 1]["close"] < candles[i + 1]["open"]

        if is_bearish_candle and next_bullish and body_next > threshold:
            if n - 1 - i <= max_age:
                bullish_obs.append({
                    "index": i, "high": candles[i]["high"], "low": candles[i]["low"],
                    "age": n - 1 - i
                })

        if is_bullish_candle and next_bearish and body_next > threshold:
            if n - 1 - i <= max_age:
                bearish_obs.append({
                    "index": i, "high": candles[i]["high"], "low": candles[i]["low"],
                    "age": n - 1 - i
                })

    nearest_bull_ob = _nearest_unmitigated(candles, bullish_obs, "bullish")
    nearest_bear_ob = _nearest_unmitigated(candles, bearish_obs, "bearish")

    return nearest_bull_ob, nearest_bear_ob


def _nearest_unmitigated(candles, ob_list, kind):
    """Ambil OB termuda yang belum sepenuhnya termitigasi."""
    last_close = candles[-1]["close"]
    for ob in sorted(ob_list, key=lambda x: x["age"]):
        if kind == "bullish" and last_close > ob["low"]:
            return ob
        if kind == "bearish" and last_close < ob["high"]:
            return ob
    return None
