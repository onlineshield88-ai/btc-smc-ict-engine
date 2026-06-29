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