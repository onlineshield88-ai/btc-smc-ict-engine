def _nearest_unmitigated(candles, ob_list, kind):
    """Ambil OB termuda yang belum sepenuhnya termitigasi."""
    last_close = candles[-1]["close"]
    for ob in sorted(ob_list, key=lambda x: x["age"]):
        if kind == "bullish" and last_close > ob["low"]:
            return ob
        if kind == "bearish" and last_close < ob["high"]:
            return ob
    return None