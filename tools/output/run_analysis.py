def run_analysis():
    """
    Jalankan satu siklus analisa lengkap. Return dict berisi semua hasil,
    atau dict dengan key 'error' jika gagal. Identik logikanya dengan
    versi pandas - hanya struktur data internal yang berbeda (list of
    dict, bukan DataFrame).
    """
    entry_candles, err1 = get_binance_klines(interval=TF_ENTRY, limit=LIMIT)
    htf1_candles, err2  = get_binance_klines(interval=TF_BIAS_1, limit=160)
    htf2_candles, err3  = get_binance_klines(interval=TF_BIAS_2, limit=160)

    if entry_candles is None or htf1_candles is None or htf2_candles is None:
        return {"error": err1 or err2 or err3 or "Data tidak lengkap"}

    if len(entry_candles) < 130 or len(htf1_candles) < 130 or len(htf2_candles) < 130:
        return {"error": "Data terlalu sedikit untuk analisa reliable (perlu >=130 candle untuk WMA119)"}

    entry_candles = add_indicators(entry_candles)
    entry_candles = detect_swings(entry_candles)
    entry_candles = detect_structure(entry_candles)
    entry_candles = detect_sweep(entry_candles)

    volatility_regime = get_volatility_regime(entry_candles)

    ob_bull, ob_bear = detect_orderblock(entry_candles)
    fvg_data = detect_fvg_ifvg(entry_candles)
    fibo = get_fibo_ote(entry_candles)

    bias_1h = get_htf_bias(htf1_candles)
    bias_4h = get_htf_bias(htf2_candles)

    score_bull, score_bear, reasons_bull, reasons_bear = calculate_score(
        entry_candles, ob_bull, ob_bear, fvg_data, fibo, bias_1h, bias_4h
    )

    last_candle = entry_candles[-1]
    signal, score = get_signal(score_bull, score_bear, fibo, last_candle)
    reasons = reasons_bull if "BUY" in signal else reasons_bear if "SELL" in signal else []

    retest_ok = True
    if "BUY" in signal:
        relevant_fvg = fvg_data["ifvg_bull"] or fvg_data["fvg_bull"]
        retest_ok = get_retest_confirmation(entry_candles, "BUY", ob_bull, relevant_fvg)
        if not retest_ok:
            reasons = reasons + ["[DITAHAN] Belum ada retest valid ke zona OB/FVG"]
            signal = "NO SIGNAL / WAIT"
    elif "SELL" in signal:
        relevant_fvg = fvg_data["ifvg_bear"] or fvg_data["fvg_bear"]
        retest_ok = get_retest_confirmation(entry_candles, "SELL", ob_bear, relevant_fvg)
        if not retest_ok:
            reasons = reasons + ["[DITAHAN] Belum ada retest valid ke zona OB/FVG"]
            signal = "NO SIGNAL / WAIT"

    plan = None
    if "BUY" in signal:
        relevant_fvg = fvg_data["ifvg_bull"] or fvg_data["fvg_bull"]
        plan = build_trade_plan("BUY", entry_candles, ob_bull, relevant_fvg, fibo, volatility_regime)
    elif "SELL" in signal:
        relevant_fvg = fvg_data["ifvg_bear"] or fvg_data["fvg_bear"]
        plan = build_trade_plan("SELL", entry_candles, ob_bear, relevant_fvg, fibo, volatility_regime)

    atr_val = last_candle["atr"]
    wma_fast_val = last_candle["wma_fast"]
    wma_slow_val = last_candle["wma_slow"]
    rsi2_val = last_candle["rsi2"]

    return {
        "error": None,
        "time": _time_to_str(last_candle["time"]),
        "close": round(float(last_candle["close"]), 2),
        "atr": round(float(atr_val), 2) if not is_nan(atr_val) else None,
        "rsi": round(float(last_candle["rsi"]), 1),
        "rsi2": round(float(rsi2_val), 1) if not is_nan(rsi2_val) else None,
        "wma_fast": round(float(wma_fast_val), 2) if not is_nan(wma_fast_val) else None,
        "wma_slow": round(float(wma_slow_val), 2) if not is_nan(wma_slow_val) else None,
        "volatility_regime": volatility_regime,
        "bias_1h": bias_1h["bias"],
        "bias_4h": bias_4h["bias"],
        "fibo_zone": fibo["zone"] if fibo else None,
        "fibo_direction": fibo["direction"] if fibo else None,
        "fibo_in_ote": fibo["in_ote"] if fibo else None,
        "signal": signal,
        "score": score,
        "reasons": reasons,
        "plan": plan,
    }