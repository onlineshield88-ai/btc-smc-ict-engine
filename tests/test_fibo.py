import sys
from pathlib import Path
import copy

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine
from core.fibo import get_fibo_ote
from core.structure import detect_swings


def test_fibo():

    print("=" * 60)
    print("FIBONACCI TEST")
    print("=" * 60)

    candles, err = engine.get_binance_klines(limit=300)

    assert err is None

    candles = engine.add_indicators(copy.deepcopy(candles))

    candles_engine = engine.detect_swings(copy.deepcopy(candles))
    candles_core   = detect_swings(copy.deepcopy(candles))

    old = engine.get_fibo_ote(candles_engine)
    new = get_fibo_ote(candles_core)

    print("ENGINE:")
    print(old)

    print()

    print("CORE:")
    print(new)

    print()

    assert old == new

    print("IDENTICAL")


if __name__ == "__main__":
    test_fibo()
