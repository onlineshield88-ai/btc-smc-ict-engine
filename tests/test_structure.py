import sys
from pathlib import Path
import copy

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine

from core.structure import (
    detect_swings,
    detect_structure,
    detect_sweep,
    get_volatility_regime,
)


def compare_dicts(old, new, fields):

    mismatch = 0

    for i in range(len(old)):

        for f in fields:

            if old[i].get(f) != new[i].get(f):

                mismatch += 1

                print(
                    f"Mismatch candle={i} field={f} "
                    f"{old[i].get(f)} != {new[i].get(f)}"
                )

    return mismatch


def test_structure():

    print("=" * 60)
    print("STRUCTURE TEST")
    print("=" * 60)

    candles, err = engine.get_binance_klines(limit=300)

    assert err is None

    src = copy.deepcopy(candles)

    #######################################
    # SWINGS
    #######################################

    old = engine.add_indicators(copy.deepcopy(src))
    new = engine.add_indicators(copy.deepcopy(src))

    old = engine.detect_swings(old)
    new = detect_swings(new)

    m = compare_dicts(
        old,
        new,
        [
            "swing_high",
            "swing_low",
        ],
    )

    print("detect_swings mismatch:", m)
    assert m == 0

    #######################################
    # STRUCTURE
    #######################################

    old = engine.detect_structure(copy.deepcopy(old))
    new = detect_structure(copy.deepcopy(new))

    m = compare_dicts(
        old,
        new,
        [
            "bos_bullish",
            "bos_bearish",
            "choch_bullish",
            "choch_bearish",
            "trend",
        ],
    )

    print("detect_structure mismatch:", m)
    assert m == 0

    #######################################
    # SWEEP
    #######################################

    old = engine.detect_sweep(copy.deepcopy(old))
    new = detect_sweep(copy.deepcopy(new))

    m = compare_dicts(
        old,
        new,
        [
            "sweep_high",
            "sweep_low",
        ],
    )

    print("detect_sweep mismatch:", m)
    assert m == 0

    #######################################
    # VOLATILITY
    #######################################

    old_vol = engine.get_volatility_regime(old)
    new_vol = get_volatility_regime(new)

    print()

    print("Engine :", old_vol)
    print("Core   :", new_vol)

    assert old_vol == new_vol

    print()
    print("IDENTICAL")


if __name__ == "__main__":
    test_structure()
