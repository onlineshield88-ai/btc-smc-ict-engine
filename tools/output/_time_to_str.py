def _time_to_str(ms_epoch):
    """Konversi epoch ms ke string 'YYYY-MM-DD HH:MM:SS' tanpa pandas/datetime libs eksternal."""
    import datetime
    dt = datetime.datetime.utcfromtimestamp(ms_epoch / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")