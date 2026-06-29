"""
Structure Module

Market Structure (SMC)

Berisi:

- detect_swings()
- detect_structure()
- detect_sweep()
- get_volatility_regime()

Seluruh implementasi dipindahkan langsung dari engine.py.
"""

from core.indicators import (
    is_nan,
)

__all__ = [
    "detect_swings",
    "detect_structure",
    "detect_sweep",
    "get_volatility_regime",
]


def detect_swings(candles, left=2, right=2):
    """Deteksi swing high / swing low fraktal. Identik logikanya dengan versi pandas."""
    candles = [dict(c) for c in candles]
    n = len(candles)
    for c in candles:
        c["swing_high"] = False
        c["swing_low"] = False

    for i in range(left, n - right):
        window_high = [candles[j]["high"] for j in range(i - left, i + right + 1)]
        window_low  = [candles[j]["low"] for j in range(i - left, i + right + 1)]

        max_h = max(window_high)
        if candles[i]["high"] == max_h and window_high.count(max_h) == 1:
            candles[i]["swing_high"] = True

        min_l = min(window_low)
        if candles[i]["low"] == min_l and window_low.count(min_l) == 1:
            candles[i]["swing_low"] = True

    return candles


def detect_structure(candles):
    """Deteksi Break of Structure (BOS) dan Change of Character (CHoCH). Identik dengan versi pandas."""
    candles = [dict(c) for c in candles]
    for c in candles:
        c["bos_bullish"] = False
        c["bos_bearish"] = False
        c["choch_bullish"] = False
        c["choch_bearish"] = False
        c["trend"] = None

    last_swing_high = None
    last_swing_low = None
    trend = None

    for i, c in enumerate(candles):
        if c["swing_high"]:
            last_swing_high = c["high"]
        if c["swing_low"]:
            last_swing_low = c["low"]

        close = c["close"]

        if last_swing_high is not None and close > last_swing_high:
            if trend == "down":
                c["choch_bullish"] = True
            else:
                c["bos_bullish"] = True
            trend = "up"
            last_swing_high = None

        if last_swing_low is not None and close < last_swing_low:
            if trend == "up":
                c["choch_bearish"] = True
            else:
                c["bos_bearish"] = True
            trend = "down"
            last_swing_low = None

        c["trend"] = trend

    return candles


def detect_sweep(candles, lookback=20):
    """Deteksi liquidity sweep. Identik logikanya dengan versi pandas."""
    candles = [dict(c) for c in candles]
    n = len(candles)
    for c in candles:
        c["sweep_high"] = False
        c["sweep_low"] = False

    for i in range(lookback, n):
        recent = candles[i - lookback:i]
        recent_highs = [c["high"] for c in recent]
        recent_lows  = [c["low"] for c in recent]
        recent_high = max(recent_highs)
        recent_low  = min(recent_lows)

        penetration_high = candles[i]["high"] - recent_high
        penetration_low  = recent_low - candles[i]["low"]
        avg_range = sum(c["high"] - c["low"] for c in recent) / len(recent)

        if (candles[i]["high"] > recent_high and candles[i]["close"] < recent_high
                and penetration_high > avg_range * 0.05):
            candles[i]["sweep_high"] = True

        if (candles[i]["low"] < recent_low and candles[i]["close"] > recent_low
                and penetration_low > avg_range * 0.05):
            candles[i]["sweep_low"] = True

    return candles


def get_volatility_regime(candles):
    """
    Klasifikasi rezim volatilitas: HIGH_VOLATILITY / CHOPPY / TRENDING.
    Identik logikanya dengan versi pandas (baseline atr_avg dari 100
    candle terakhir, supaya tidak self-referencing dengan periode choppy
    yang sedang dideteksi).
    """
    n = len(candles)
    if n < 110:
        return "TRENDING"

    atr_now = candles[-1]["atr"]
    atr_tail_100 = [c["atr"] for c in candles[-100:] if c["atr"] is not None]
    if not atr_tail_100:
        return "TRENDING"
    atr_avg = sum(atr_tail_100) / len(atr_tail_100)

    if is_nan(atr_now) or atr_avg == 0:
        return "TRENDING"

    wma_last = candles[-1]["wma_slow"]
    wma_prev = candles[-5]["wma_slow"]
    if wma_last is None or wma_prev is None:
        return "TRENDING"
    wma_slope = abs(wma_last - wma_prev)

    if atr_now > atr_avg * 1.6:
        return "HIGH_VOLATILITY"

    if atr_now < atr_avg * 0.75 and wma_slope < (atr_avg * 0.15):
        return "CHOPPY"

    return "TRENDING"
