import json
import os
from config import CACHE_FILE



def save(result):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


def load():
    if not os.path.exists(CACHE_FILE):
        return None

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
