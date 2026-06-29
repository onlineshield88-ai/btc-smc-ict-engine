def build_trade_plan(direction, candles, ob, fvg_zone, fibo, volatility_regime="TRENDING",
                      rr_min=RISK_REWARD_MIN):
    """SL/TP dinamis dengan TP1/TP2/TP3 adaptive volatility regime. Identik logikanya dengan versi pandas."""
    last = candles[-1]
    entry = last["close"]
    atr = last["atr"]

    if is_nan(atr) or atr is None or atr <= 0:
        return None

    mult = _TP_MULTIPLIERS.get(volatility_regime, _TP_MULTIPLIERS["TRENDING"])
    atr_buffer = atr * ATR_SL_MULT

    if direction == "BUY":
        structural_sl_candidates = []
        if ob:
            structural_sl_candidates.append(ob["low"])
        if fvg_zone:
            structural_sl_candidates.append(fvg_zone.get("bottom", entry - atr_buffer))
        if fibo:
            structural_sl_candidates.append(fibo["leg_low"])

        structural_sl = min(structural_sl_candidates) if structural_sl_candidates else entry - atr_buffer
        sl = min(structural_sl - atr_buffer * 0.3, entry - atr * mult["sl"])

        risk = entry - sl
        if risk <= 0:
            return None

        tp1 = entry + (risk * max(mult["tp1"], rr_min))
        tp2 = entry + (risk * mult["tp2"])
        tp3_structural = fibo["leg_high"] if fibo else None
        tp3_rr = entry + (risk * mult["tp3"])
        tp3 = max(tp3_structural, tp3_rr) if tp3_structural else tp3_rr

    else:
        structural_sl_candidates = []
        if ob:
            structural_sl_candidates.append(ob["high"])
        if fvg_zone:
            structural_sl_candidates.append(fvg_zone.get("top", entry + atr_buffer))
        if fibo:
            structural_sl_candidates.append(fibo["leg_high"])

        structural_sl = max(structural_sl_candidates) if structural_sl_candidates else entry + atr_buffer
        sl = max(structural_sl + atr_buffer * 0.3, entry + atr * mult["sl"])

        risk = sl - entry
        if risk <= 0:
            return None

        tp1 = entry - (risk * max(mult["tp1"], rr_min))
        tp2 = entry - (risk * mult["tp2"])
        tp3_structural = fibo["leg_low"] if fibo else None
        tp3_rr = entry - (risk * mult["tp3"])
        tp3 = min(tp3_structural, tp3_rr) if tp3_structural else tp3_rr

    actual_risk = abs(entry - sl)
    reward_tp1 = abs(tp1 - entry)
    rr_tp1 = reward_tp1 / actual_risk if actual_risk > 0 else 0

    return {
        "entry": round(float(entry), 2),
        "stop_loss": round(float(sl), 2),
        "take_profit": round(float(tp1), 2),
        "tp1": round(float(tp1), 2),
        "tp2": round(float(tp2), 2),
        "tp3": round(float(tp3), 2),
        "risk_usd_per_btc": round(float(actual_risk), 2),
        "reward_usd_per_btc": round(float(reward_tp1), 2),
        "risk_reward": round(float(rr_tp1), 2),
        "atr_used": round(float(atr), 2),
        "volatility_regime": volatility_regime,
    }