def calculate_score(candles, ob_bull, ob_bear, fvg_data, fibo, bias_1h, bias_4h):
    """Hitung skor confluence bullish/bearish. Identik logikanya dengan versi pandas."""
    last = candles[-1]
    prev = candles[-2]

    score_bull = 0
    score_bear = 0
    reasons_bull = []
    reasons_bear = []

    recent = candles[-5:]
    if any(c["choch_bullish"] or c["bos_bullish"] for c in recent):
        score_bull += 20
        reasons_bull.append("BOS/CHoCH bullish dalam 5 candle terakhir")
    if any(c["choch_bearish"] or c["bos_bearish"] for c in recent):
        score_bear += 20
        reasons_bear.append("BOS/CHoCH bearish dalam 5 candle terakhir")

    if any(c["sweep_low"] for c in recent):
        score_bull += 15
        reasons_bull.append("Liquidity sweep di bawah (stop hunt) dalam 5 candle terakhir")
    if any(c["sweep_high"] for c in recent):
        score_bear += 15
        reasons_bear.append("Liquidity sweep di atas (stop hunt) dalam 5 candle terakhir")

    price = last["close"]
    atr_now = last["atr"] if not is_nan(last["atr"]) else price * 0.001
    ob_tolerance = atr_now * 0.5

    if ob_bull and (ob_bull["low"] - ob_tolerance) <= price <= (ob_bull["high"] + ob_tolerance):
        score_bull += 15
        reasons_bull.append("Price berada di/dekat zona bullish Order Block")

    ifvg_bull = fvg_data["ifvg_bull"]
    if ifvg_bull and (ifvg_bull["bottom"] - ob_tolerance) <= price <= (ifvg_bull["top"] + ob_tolerance):
        score_bull += 10
        reasons_bull.append("Inverse FVG bullish terkonfirmasi & price masih di zona")

    if ob_bear and (ob_bear["low"] - ob_tolerance) <= price <= (ob_bear["high"] + ob_tolerance):
        score_bear += 15
        reasons_bear.append("Price berada di/dekat zona bearish Order Block")

    ifvg_bear = fvg_data["ifvg_bear"]
    if ifvg_bear and (ifvg_bear["bottom"] - ob_tolerance) <= price <= (ifvg_bear["top"] + ob_tolerance):
        score_bear += 10
        reasons_bear.append("Inverse FVG bearish terkonfirmasi & price masih di zona")

    if fibo:
        if fibo["in_ote"] and fibo["direction"] == "down" and fibo["zone"] == "discount":
            score_bull += 12
            reasons_bull.append("Price di zona OTE Fibo 0.618-0.79 (discount)")
        if fibo["in_ote"] and fibo["direction"] == "up" and fibo["zone"] == "premium":
            score_bear += 12
            reasons_bear.append("Price di zona OTE Fibo 0.618-0.79 (premium)")

    wma_f_last = last["wma_fast"]
    wma_s_last = last["wma_slow"]
    wma_f_prev = prev["wma_fast"]
    wma_s_prev = prev["wma_slow"]
    if None not in (wma_f_last, wma_s_last, wma_f_prev, wma_s_prev):
        if wma_f_last > wma_s_last and wma_f_prev <= wma_s_prev:
            score_bull += 10
            reasons_bull.append("WMA9 cross up WMA119 (trigger momentum)")
        if wma_f_last < wma_s_last and wma_f_prev >= wma_s_prev:
            score_bear += 10
            reasons_bear.append("WMA9 cross down WMA119 (trigger momentum)")

    if 35 <= last["rsi"] <= 55 and last["rsi"] > prev["rsi"]:
        score_bull += 8
        reasons_bull.append(f"RSI rebound dari area netral-rendah ({last['rsi']:.1f})")
    if 45 <= last["rsi"] <= 65 and last["rsi"] < prev["rsi"]:
        score_bear += 8
        reasons_bear.append(f"RSI turun dari area netral-tinggi ({last['rsi']:.1f})")
    if last["rsi"] < 30:
        score_bull += 5
        reasons_bull.append(f"RSI oversold ({last['rsi']:.1f})")
    if last["rsi"] > 70:
        score_bear += 5
        reasons_bear.append(f"RSI overbought ({last['rsi']:.1f})")

    if bias_1h["bias"] == "bullish":
        score_bull += 5
        reasons_bull.append("Bias 1H bullish")
    if bias_4h["bias"] == "bullish":
        score_bull += 5
        reasons_bull.append("Bias 4H bullish")
    if bias_1h["bias"] == "bearish":
        score_bear += 5
        reasons_bear.append("Bias 1H bearish")
    if bias_4h["bias"] == "bearish":
        score_bear += 5
        reasons_bear.append("Bias 4H bearish")

    score_bull = min(score_bull, 80)
    score_bear = min(score_bear, 80)

    return score_bull, score_bear, reasons_bull, reasons_bear