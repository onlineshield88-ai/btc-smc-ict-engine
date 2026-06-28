import os
import time

import db
import cache
import heartbeat
import engine


def get_status():

    cache_data = cache.load()

    cache_file = "latest_analysis.json"

    cache_exists = os.path.exists(cache_file)

    cache_age = None

    if cache_exists:
        cache_age = int(time.time() - os.path.getmtime(cache_file))

    stats = db.get_stats()

    hb = heartbeat.read()

    return {
        "engine": "running",
        "backend": "running",
        "version": engine.ENGINE_VERSION,
        "symbol": engine.SYMBOL,
        "timeframe": engine.TF_ENTRY,
        "database_records": stats["total"],
        "open_signals": stats["open"],
        "cache_exists": cache_exists,
        "cache_age_seconds": cache_age,
        "last_analysis": cache_data["time"] if cache_data else None,
        "heartbeat": hb
    }
