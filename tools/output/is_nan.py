def is_nan(v):
    """Pengganti pd.isna() untuk float biasa / None."""
    if v is None:
        return True
    try:
        return math.isnan(v)
    except TypeError:
        return False