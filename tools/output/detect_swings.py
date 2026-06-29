def detect_swings(candles, left=2, right=2):
    """Deteksi swing high / swing low fraktal. Identik logikanya dengan versi pandas."""
    candles = [dict(c) for c in candles]
    n = len(candles)
    for c in candles:
        c["swing_high"] = False
        c["swing_low"] = False

    for i in range(left, n - right):
        window_high = [candles[j]["high"] for j in range(i - left, i + right + 1)]
        window_low  = [candles[j]["low"] for j in range(i - left, i + right + 1)]

        max_h = max(window_high)
        if candles[i]["high"] == max_h and window_high.count(max_h) == 1:
            candles[i]["swing_high"] = True

        min_l = min(window_low)
        if candles[i]["low"] == min_l and window_low.count(min_l) == 1:
            candles[i]["swing_low"] = True

    return candles