from pathlib import Path

src = Path("engine.py").read_text(encoding="utf-8")

# Ambil bagian sebelum helper pertama (_ema)
cut = src.find("def _ema(")

if cut == -1:
    raise SystemExit("Tidak menemukan def _ema()")

header = src[:cut].rstrip()

imports = """

# =====================================================
# CORE MODULES
# =====================================================

from core.indicators import (
    is_nan,
    _tail_mean,
    _rolling_mean,
    _wma,
    _ema,
    add_indicators,
)

from core.structure import (
    detect_swings,
    detect_structure,
    detect_sweep,
    get_volatility_regime,
)

from core.orderblock import (
    detect_orderblock,
)

from core.fvg import (
    detect_fvg_ifvg,
)

from core.fibo import (
    get_fibo_ote,
)

from core.trend import (
    get_htf_bias,
    get_retest_confirmation,
)

from core.scoring import (
    calculate_score,
)

from core.risk import (
    build_trade_plan,
)

from core.analysis import (
    get_signal,
    run_analysis,
)
"""

Path("engine_new.py").write_text(
    header + imports + "\n",
    encoding="utf-8"
)

print("=" * 60)
print("engine_new.py created")
print("=" * 60)
