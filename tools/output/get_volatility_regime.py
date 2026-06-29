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