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