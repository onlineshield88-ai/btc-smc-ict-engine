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