"""
engine.py (PURE PYTHON - tanpa pandas/numpy)
================================================================================
Versi ini FUNGSIONAL IDENTIK dengan engine.py v2 (yang pakai pandas/numpy),
tapi ditulis ulang total tanpa dependency tersebut.

ALASAN: pandas/numpy gagal dikompilasi untuk Android NDK saat build APK
(numpy>=2.x memakai fitur C++ std::unordered_map yang tidak kompatibel
dengan clang toolchain Android NDK r25b yang dipakai python-for-android).
Pure Python tidak butuh kompilasi native sama sekali, jadi build APK
otomatis lebih ringan, lebih cepat, dan tidak rawan gagal seperti ini.

STRUKTUR DATA:
Pengganti pd.DataFrame adalah list of dict, satu dict per candle:
    candles = [{"time":..., "open":..., "high":..., "low":..., "close":...,
                "volume":..., "atr":..., "rsi":..., ...}, ...]
Index list = index candle (sama seperti df.iloc[i] sebelumnya).
candles[-1] = candle terakhir/live (sama seperti df.iloc[-1] sebelumnya).

Semua logika SMC/ICT (swing, BOS/CHoCH, OB, FVG/iFVG, Fibo OTE, retest
filter, scoring, volatility regime, trade plan TP1/2/3) IDENTIK secara
matematis dengan versi pandas - hanya cara mengakses data yang berubah.
================================================================================
"""

import json
import math
import urllib.request
import urllib.error
import warnings
warnings.filterwarnings("ignore")


# =====================================================================
# CONFIG
# =====================================================================

SYMBOL          = "BTCUSDT"
TF_ENTRY        = "15m"
TF_BIAS_1       = "1h"
TF_BIAS_2       = "4h"

LIMIT           = 300
RISK_REWARD_MIN = 1.5
ATR_SL_MULT     = 1.2
ATR_PERIOD      = 14

SCORE_MIN_LIGHT  = 40
SCORE_MIN_STRONG = 55

ENGINE_VERSION  = "HYBRID-SMC-ICT-WMA-RSI-FIBO v2.1 (pure-python)"


# =====================================================================
# BINANCE FETCH (urllib bawaan Python, tanpa dependency requests)
# =====================================================================

def get_binance_klines(symbol=SYMBOL, interval="15m", limit=LIMIT, futures=True):
    """
    Ambil data kline dari Binance memakai urllib (stdlib), bukan `requests`.
    Mengembalikan (candles, error) - candles adalah list of dict, error
    adalah None jika sukses atau string pesan error jika gagal.
    """
    base_url = "https://fapi.binance.com/fapi/v1/klines" if futures \
        else "https://api.binance.com/api/v3/klines"
    url = f"{base_url}?symbol={symbol}&interval={interval}&limit={limit}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "btc-smc-ict-engine"})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)

        if isinstance(data, dict) and data.get("code"):
            return None, f"Binance API error: {data}"

        candles = []
        for row in data:
            candles.append({
                "time": int(row[0]),       # ms epoch, dikonversi ke string ISO saat dibutuhkan
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        return candles, None

    except urllib.error.URLError as e:
        return None, f"Fetch gagal (koneksi): {e}"
    except Exception as e:
        return None, f"Fetch gagal: {e}"


def _time_to_str(ms_epoch):
    """Konversi epoch ms ke string 'YYYY-MM-DD HH:MM:SS' tanpa pandas/datetime libs eksternal."""
    import datetime
    dt = datetime.datetime.utcfromtimestamp(ms_epoch / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# =====================================================================
# HELPER: operasi list numerik pengganti pandas/numpy
# =====================================================================

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

