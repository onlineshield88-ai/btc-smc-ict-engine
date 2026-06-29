import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import app

client = app.test_client()


def test_dashboard():
    r = client.get("/api/dashboard")
    assert r.status_code == 200

    data = r.get_json()

    assert "signal" in data
    assert "score" in data
    assert "price" in data

    print("Dashboard OK")


def test_analysis():
    r = client.get("/api/analysis")
    assert r.status_code == 200

    data = r.get_json()

    assert "atr" in data
    assert "rsi" in data
    assert "wma9" in data

    print("Analysis OK")


def test_history():
    r = client.get("/api/history")
    assert r.status_code == 200

    data = r.get_json()

    assert isinstance(data, list)

    print("History OK")


def test_settings():
    r = client.get("/api/settings")
    assert r.status_code == 200

    data = r.get_json()

    assert "language" in data

    print("Settings OK")


if __name__ == "__main__":
    test_dashboard()
    test_analysis()
    test_history()
    test_settings()

    print("\nALL API TEST PASSED")
