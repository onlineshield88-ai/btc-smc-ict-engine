import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine
from core.analysis import run_analysis_from_candles


def compare(a, b):

    mismatch = 0

    keys = [
        "signal",
        "score",
        "close",
        "atr",
        "rsi",
        "rsi2",
        "wma_fast",
        "wma_slow",
        "bias_1h",
        "bias_4h",
        "volatility_regime",
        "fibo_zone",
        "fibo_direction",
        "fibo_in_ote",
        "plan",
    ]

    print("=" * 60)
    print("COMPARE ENGINE vs CORE")
    print("=" * 60)

    for k in keys:

        if a.get(k) != b.get(k):

            mismatch += 1

            print()
            print(k)
            print("ENGINE :", a.get(k))
            print("CORE   :", b.get(k))

    print()

    if mismatch == 0:
        print("IDENTICAL")
    else:
        print("Mismatch:", mismatch)

    return mismatch


def test_run_analysis():

    entry, _ = engine.get_binance_klines(limit=300)
    h1, _ = engine.get_binance_klines(interval="1h", limit=160)
    h4, _ = engine.get_binance_klines(interval="4h", limit=160)

    old = engine.run_analysis()

    new = run_analysis_from_candles(
        entry,
        h1,
        h4,
    )

    assert compare(old, new) == 0

if __name__ == "__main__":
    test_run_analysis()
