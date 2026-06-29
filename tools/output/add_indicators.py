def add_indicators(candles, atr_period=ATR_PERIOD, wma_fast=9, wma_slow=119, rsi_period=14):
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