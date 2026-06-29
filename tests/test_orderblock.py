import sys
from pathlib import Path
import copy

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine

from core.orderblock import detect_orderblock


def compare_ob(a, b):

    if a is None and b is None:
        return True

    if a is None or b is None:
        return False

    keys = [
        "index",
        "high",
        "low",
        "age",
    ]

    for k in keys:
        if a.get(k) != b.get(k):
            return False

    return True


def test_orderblock():

    print("=" * 60)
    print("ORDERBLOCK TEST")
    print("=" * 60)

    candles, err = engine.get_binance_klines(limit=300)

    assert err is None

    candles = engine.add_indicators(copy.deepcopy(candles))

    old_bull, old_bear = engine.detect_orderblock(copy.deepcopy(candles))
    new_bull, new_bear = detect_orderblock(copy.deepcopy(candles))

    assert compare_ob(old_bull, new_bull), "Bullish Order Block mismatch"
    assert compare_ob(old_bear, new_bear), "Bearish Order Block mismatch"

    print("Bullish OB : IDENTICAL")
    print("Bearish OB : IDENTICAL")
    print()
    print("PASS")


if __name__ == "__main__":
    test_orderblock()
