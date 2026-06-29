import sys
from pathlib import Path
import copy

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine

from core.trend import (
    get_htf_bias,
    get_retest_confirmation,
)

from core.structure import (
    detect_swings,
    detect_structure,
)

from core.indicators import add_indicators


def test_trend():

    print("=" * 60)
    print("TREND TEST")
    print("=" * 60)

    #########################################################
    # HTF BIAS
    #########################################################

    candles, err = engine.get_binance_klines(interval="1h", limit=300)

    assert err is None

    old = engine.get_htf_bias(copy.deepcopy(candles))
    new = get_htf_bias(copy.deepcopy(candles))

    print("HTF BIAS")
    print("ENGINE :", old)
    print("CORE   :", new)

    assert old == new

    #########################################################
    # RETEST
    #########################################################

    candles, err = engine.get_binance_klines(limit=300)

    assert err is None

    candles = add_indicators(copy.deepcopy(candles))
    candles = detect_swings(candles)
    candles = detect_structure(candles)

    ob_bull, ob_bear = engine.detect_orderblock(copy.deepcopy(candles))
    fvg = engine.detect_fvg_ifvg(copy.deepcopy(candles))

    old_buy = engine.get_retest_confirmation(
        copy.deepcopy(candles),
        "BUY",
        ob_bull,
        fvg["fvg_bull"],
    )

    new_buy = get_retest_confirmation(
        copy.deepcopy(candles),
        "BUY",
        ob_bull,
        fvg["fvg_bull"],
    )

    assert old_buy == new_buy

    old_sell = engine.get_retest_confirmation(
        copy.deepcopy(candles),
        "SELL",
        ob_bear,
        fvg["fvg_bear"],
    )

    new_sell = get_retest_confirmation(
        copy.deepcopy(candles),
        "SELL",
        ob_bear,
        fvg["fvg_bear"],
    )

    assert old_sell == new_sell

    print()
    print("RETEST BUY :", old_buy)
    print("RETEST SELL:", old_sell)

    print()
    print("IDENTICAL")


if __name__ == "__main__":
    test_trend()
