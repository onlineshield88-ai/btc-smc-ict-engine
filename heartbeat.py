import json
from datetime import datetime

FILE = "heartbeat.json"


def update(status="running"):

    data = {
        "status": status,
        "last_update": datetime.now().isoformat()
    }

    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)


def read():

    try:
        with open(FILE) as f:
            return json.load(f)
    except Exception:
        return None
