import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine


def test_run_analysis():
    print("=" * 60)
    print("ENGINE TEST")
    print("=" * 60)

    result = engine.run_analysis()

    assert isinstance(result, dict), "Output bukan dictionary"

    if result.get("error"):
        raise Exception(result["error"])

    required = [
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
        "time",
    ]

    for key in required:
        assert key in result, f"Field '{key}' tidak ada"

    print("Signal :", result["signal"])
    print("Score  :", result["score"])
    print("Price  :", result["close"])
    print("ATR    :", result["atr"])
    print("RSI    :", result["rsi"])
    print("Time   :", result["time"])

    print("\nPASS")


if __name__ == "__main__":
    test_run_analysis()
