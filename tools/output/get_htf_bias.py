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