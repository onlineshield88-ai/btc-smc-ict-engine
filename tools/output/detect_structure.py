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