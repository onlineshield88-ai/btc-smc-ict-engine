import sys
from pathlib import Path
import copy

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine
from core.fvg import detect_fvg_ifvg


def test_fvg():

    print("=" * 60)
    print("FVG TEST")
    print("=" * 60)

    candles, err = engine.get_binance_klines(limit=300)

    assert err is None

    candles = engine.add_indicators(copy.deepcopy(candles))

    old = engine.detect_fvg_ifvg(copy.deepcopy(candles))
    new = detect_fvg_ifvg(copy.deepcopy(candles))

    keys = [
        "fvg_bull",
        "fvg_bear",
        "ifvg_bull",
        "ifvg_bear",
    ]

    mismatch = 0

    for k in keys:

        if old.get(k) != new.get(k):

            mismatch += 1

            print()
            print(k)
            print("ENGINE :", old.get(k))
            print("CORE   :", new.get(k))

    print()

    if mismatch == 0:
        print("IDENTICAL")
    else:
        print("Mismatch:", mismatch)

    assert mismatch == 0


if __name__ == "__main__":
    test_fvg()
