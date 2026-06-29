"""
Analysis Module

Berisi:

- _time_to_str()
- get_signal()
- run_analysis()

Orchestrator utama engine.

Seluruh implementasi dipindahkan langsung dari engine.py.

JANGAN ubah algoritma.
"""

from datetime import datetime

from core.data import (
    get_binance_klines,
    TF_ENTRY,
    TF_BIAS_1,
    TF_BIAS_2,
    LIMIT,
)


SCORE_MIN_LIGHT = 40
SCORE_MIN_STRONG = 55

from core.indicators import (
    add_indicators,
    is_nan,
)

from core.structure import (
    detect_swings,
    detect_structure,
    detect_sweep,
    get_volatility_regime,
)

from core.orderblock import detect_orderblock

from core.fvg import detect_fvg_ifvg

from core.fibo import get_fibo_ote

from core.trend import (
    get_htf_bias,
    get_retest_confirmation,
)

from core.scoring import calculate_score

from core.risk import build_trade_plan

__all__ = [
    "_time_to_str",
    "get_signal",
    "run_analysis",
]


def _time_to_str(ms_epoch):
    """Konversi epoch ms ke string 'YYYY-MM-DD HH:MM:SS' tanpa pandas/datetime libs eksternal."""
    import datetime
    dt = datetime.datetime.utcfromtimestamp(ms_epoch / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_signal(score_bull, score_bear, fibo, last_candle):
    """Tentukan sinyal kandidat. Identik logikanya dengan versi pandas."""
    rsi = last_candle["rsi"]

    hard_block_buy = fibo and fibo["zone"] == "premium" and rsi > 75
    hard_block_sell = fibo and fibo["zone"] == "discount" and rsi < 25

    if score_bull >= SCORE_MIN_STRONG and score_bull > score_bear and not hard_block_buy:
        return "BUY STRONG", score_bull
    if score_bull >= SCORE_MIN_LIGHT and score_bull > score_bear and not hard_block_buy:
        return "BUY LIGHT", score_bull
    if score_bear >= SCORE_MIN_STRONG and score_bear > score_bull and not hard_block_sell:
        return "SELL STRONG", score_bear
    if score_bear >= SCORE_MIN_LIGHT and score_bear > score_bull and not hard_block_sell:
        return "SELL LIGHT", score_bear

    return "NO SIGNAL / WAIT", max(score_bull, score_bear)


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
        return {"error": "Data tidak lengkap"}

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

