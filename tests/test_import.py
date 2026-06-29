import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine


def test_import():
    assert hasattr(engine, "run_analysis")
    assert hasattr(engine, "add_indicators")
    assert hasattr(engine, "get_binance_klines")


if __name__ == "__main__":
    test_import()
    print("PASS")
