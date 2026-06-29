"""
Indicators Module

Helper functions dipindahkan dari engine.py.
JANGAN ubah algoritma.
"""

import math

__all__ = [
    "is_nan",
    "_tail_mean",
    "_rolling_mean",
    "_wma",
    "_ema",
    "add_indicators",
]


def is_nan(v):
    """Pengganti pd.isna() untuk float biasa / None."""
    if v is None:
        return True
    try:
        return math.isnan(v)
    except TypeError:
        return False


def _tail_mean(values, n_tail):
    """Mean dari n_tail elemen terakhir, mengabaikan None (setara .tail(n).mean())."""
    chunk = [v for v in values[-n_tail:] if v is not None]
    if not chunk:
        return None
    return sum(chunk) / len(chunk)


def _rolling_mean(values, window):
    """Rolling mean sederhana (setara pandas .rolling(window).mean())."""
    n = len(values)
    result = [None] * n
    for i in range(window - 1, n):
        chunk = values[i - window + 1: i + 1]
        if any(v is None for v in chunk):
            continue
        result[i] = sum(chunk) / window
    return result


def _wma(values, length):
    """
    Weighted moving average dengan bobot linear 1..length (setara
    pandas .rolling(length).apply(weighted)). None untuk index yang
    belum punya cukup data ke belakang.
    """
    n = len(values)
    result = [None] * n
    weight_sum = length * (length + 1) / 2
    for i in range(length - 1, n):
        window = values[i - length + 1: i + 1]
        if any(v is None for v in window):
            continue
        weighted = sum(w * v for w, v in zip(range(1, length + 1), window))
        result[i] = weighted / weight_sum
    return result


def _ema(values, period):
    """
    Exponential moving average dengan alpha = 1/period (setara
    pandas .ewm(alpha=1/period, adjust=False).mean()).
    Mengembalikan list sepanjang values, None untuk index yang belum
    punya nilai sebelumnya (index 0 dipakai sebagai seed pertama).
    """
    if not values:
        return []
    alpha = 1.0 / period
    result = [None] * len(values)
    result[0] = values[0]
    for i in range(1, len(values)):
        prev = result[i - 1]
        v = values[i]
        if prev is None or v is None:
            result[i] = v
        else:
            result[i] = alpha * v + (1 - alpha) * prev
    return result


def add_indicators(
    candles,
    atr_period=14,
    wma_fast=9,
    wma_slow=119,
    rsi_period=14,
):
    """
    Tambahkan ATR, WMA9/WMA119, RSI(14), RSI(2) ke tiap dict candle (in-place
    pada list baru, tidak memodifikasi input asli).
    wma_slow default 119 (bukan 21) - filter trend lebih stabil di BTC 15m,
    lebih tahan fake-cross dibanding WMA9/WMA21.
    """
    n = len(candles)
    candles = [dict(c) for c in candles]  # copy shallow, jangan mutate input

    highs  = [c["high"] for c in candles]
    lows   = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    # --- True Range & ATR (Wilder smoothing via EMA alpha=1/period) ---
    true_ranges = []
    for i in range(n):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        true_ranges.append(tr)
    atr_values = _ema(true_ranges, atr_period)

    # --- WMA fast & slow ---
    wma_fast_values = _wma(closes, wma_fast)
    wma_slow_values = _wma(closes, wma_slow)

    # --- RSI(14) & RSI(2), Wilder smoothing ---
    # PENTING: index 0 harus None (bukan 0.0), karena pandas .diff() di index
    # pertama menghasilkan NaN (tidak ada candle sebelumnya untuk dibandingkan).
    # Ini krusial untuk seeding EMA yang benar - kalau index 0 dipaksa jadi 0.0,
    # EMA akan ter-seed dengan nilai salah dan errornya menetap selama puluhan
    # candle sebelum akhirnya teredam (terbukti dari regression test).
    gains = [None]
    losses = [None]
    for i in range(1, n):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    def calc_rsi(gains, losses, period):
        avg_gain = _ema(gains, period)
        avg_loss = _ema(losses, period)
        rsi_vals = []
        for ag, al in zip(avg_gain, avg_loss):
            # Replikasi PERSIS perilaku pandas asli:
            # rs = avg_gain / avg_loss.replace(0, np.nan)  -> avg_loss==0 jadi NaN
            # rsi = 100 - 100/(1+rs)                        -> NaN/0 jadi NaN
            # rsi.fillna(50)                                -> NaN (termasuk dari
            #                                                  avg_loss==0) SELALU jadi 50,
            #                                                  apapun nilai avg_gain saat itu.
            if ag is None or al is None or al == 0:
                rsi_vals.append(50.0)
            else:
                rs = ag / al
                rsi_vals.append(100 - (100 / (1 + rs)))
        return rsi_vals

    rsi_values  = calc_rsi(gains, losses, rsi_period)
    rsi2_values = calc_rsi(gains, losses, 2)

    for i, c in enumerate(candles):
        c["atr"]      = atr_values[i]
        c["wma_fast"] = wma_fast_values[i]
        c["wma_slow"] = wma_slow_values[i]
        c["rsi"]      = rsi_values[i]
        c["rsi2"]     = rsi2_values[i]

    return candles