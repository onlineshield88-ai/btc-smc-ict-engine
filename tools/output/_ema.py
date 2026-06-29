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