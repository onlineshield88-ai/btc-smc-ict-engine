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