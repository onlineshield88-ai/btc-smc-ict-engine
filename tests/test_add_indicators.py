import sys
from pathlib import Path
import copy

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine
from core.indicators import add_indicators


def test_add_indicators():

    print("=" * 60)
    print("COMPARE add_indicators()")
    print("=" * 60)

    candles, err = engine.get_binance_klines(limit=300)

    assert err is None, err

    src = copy.deepcopy(candles)

    old_result = engine.add_indicators(copy.deepcopy(src))
    new_result = add_indicators(copy.deepcopy(src))

    assert len(old_result) == len(new_result)

    fields = [
        "atr",
        "wma_fast",
        "wma_slow",
        "rsi",
        "rsi2",
    ]

    mismatch = 0

    for i in range(len(old_result)):

        for f in fields:

            a = old_result[i][f]
            b = new_result[i][f]

            if a is None and b is None:
                continue

            if a is None or b is None:
                mismatch += 1
                print(f"Mismatch {i} {f}: {a} != {b}")
                continue

            if abs(a-b) > 1e-9:
                mismatch += 1
                print(f"Mismatch {i} {f}: {a} != {b}")

    print()

    if mismatch == 0:
        print("IDENTICAL")
    else:
        print("Mismatch:", mismatch)

    assert mismatch == 0


if __name__ == "__main__":
    test_add_indicators()
