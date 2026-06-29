def _tail_mean(values, n_tail):
    """Mean dari n_tail elemen terakhir, mengabaikan None (setara .tail(n).mean())."""
    chunk = [v for v in values[-n_tail:] if v is not None]
    if not chunk:
        return None
    return sum(chunk) / len(chunk)