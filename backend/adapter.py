import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import engine
import cache
import db
from backend import settings
from backend.mapper import map_dashboard, map_analysis, map_history




def get_dashboard():
    result = cache.load()

    if result is None:
        result = engine.run_analysis()

    return map_dashboard(result, engine)



def get_analysis():
    result = cache.load()

    if result is None:
        result = engine.run_analysis()

    return map_analysis(result)



def get_history(limit=50):

    rows = db.get_history(limit)

    return map_history(rows)



def get_settings():
    return settings.get_settings()

