import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import indicators


def test_helpers():

    print("=" * 60)
    print("INDICATORS TEST")
    print("=" * 60)

    print("is_nan:", indicators.is_nan(None))
    print("_tail_mean:", indicators._tail_mean([1,2,3,4,5],2))
    print("_rolling_mean:", indicators._rolling_mean([1,2,3,4,5],3))
    print("_wma:", indicators._wma([1,2,3,4,5],3))
    print("_ema:", indicators._ema([1,2,3,4,5],3))

    print("\nPASS")


if __name__ == "__main__":
    test_helpers()
