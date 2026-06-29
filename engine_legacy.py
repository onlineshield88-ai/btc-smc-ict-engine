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

def _ema(values, period):
    """
    Exponential moving average dengan alpha = 1/period (setara
    pandas .ewm(alpha=1/period, adjust=False).mean()).
    Mengembalikan list sepanjang values, None untuk index yang belum
    punya nilai sebelumnya (index 0 dipakai sebagai seed pertama).
    """
    if not values:
        return []
    alpha = 1.0 / period
    result = [None] * len(values)
    result[0] = values[0]
    for i in range(1, len(values)):
        prev = result[i - 1]
        v = values[i]
        if prev is None or v is None:
            result[i] = v
        else:
            result[i] = alpha * v + (1 - alpha) * prev
    return result


def _wma(values, length):
    """
    Weighted moving average dengan bobot linear 1..length (setara
    pandas .rolling(length).apply(weighted)). None untuk index yang
    belum punya cukup data ke belakang.
    """
    n = len(values)
    result = [None] * n
    weight_sum = length * (length + 1) / 2
    for i in range(length - 1, n):
        window = values[i - length + 1: i + 1]
        if any(v is None for v in window):
            continue
        weighted = sum(w * v for w, v in zip(range(1, length + 1), window))
        result[i] = weighted / weight_sum
    return result


def _rolling_mean(values, window):
    """Rolling mean sederhana (setara pandas .rolling(window).mean())."""
    n = len(values)
    result = [None] * n
    for i in range(window - 1, n):
        chunk = values[i - window + 1: i + 1]
        if any(v is None for v in chunk):
            continue
        result[i] = sum(chunk) / window
    return result


def _tail_mean(values, n_tail):
    """Mean dari n_tail elemen terakhir, mengabaikan None (setara .tail(n).mean())."""
    chunk = [v for v in values[-n_tail:] if v is not None]
    if not chunk:
        return None
    return sum(chunk) / len(chunk)


def is_nan(v):
    """Pengganti pd.isna() untuk float biasa / None."""
    if v is None:
        return True
    try:
        return math.isnan(v)
    except TypeError:
        return False


# =====================================================================
# INDICATORS
# =====================================================================

def add_indicators(candles, atr_period=ATR_PERIOD, wma_fast=9, wma_slow=119, rsi_period=14):
    """
    Tambahkan ATR, WMA9/WMA119, RSI(14), RSI(2) ke tiap dict candle (in-place
    pada list baru, tidak memodifikasi input asli).
    wma_slow default 119 (bukan 21) - filter trend lebih stabil di BTC 15m,
    lebih tahan fake-cross dibanding WMA9/WMA21.
    """
    n = len(candles)
    candles = [dict(c) for c in candles]  # copy shallow, jangan mutate input

    highs  = [c["high"] for c in candles]
    lows   = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    # --- True Range & ATR (Wilder smoothing via EMA alpha=1/period) ---
    true_ranges = []
    for i in range(n):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        true_ranges.append(tr)
    atr_values = _ema(true_ranges, atr_period)

    # --- WMA fast & slow ---
    wma_fast_values = _wma(closes, wma_fast)
    wma_slow_values = _wma(closes, wma_slow)

    # --- RSI(14) & RSI(2), Wilder smoothing ---
    # PENTING: index 0 harus None (bukan 0.0), karena pandas .diff() di index
    # pertama menghasilkan NaN (tidak ada candle sebelumnya untuk dibandingkan).
    # Ini krusial untuk seeding EMA yang benar - kalau index 0 dipaksa jadi 0.0,
    # EMA akan ter-seed dengan nilai salah dan errornya menetap selama puluhan
    # candle sebelum akhirnya teredam (terbukti dari regression test).
    gains = [None]
    losses = [None]
    for i in range(1, n):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    def calc_rsi(gains, losses, period):
        avg_gain = _ema(gains, period)
        avg_loss = _ema(losses, period)
        rsi_vals = []
        for ag, al in zip(avg_gain, avg_loss):
            # Replikasi PERSIS perilaku pandas asli:
            # rs = avg_gain / avg_loss.replace(0, np.nan)  -> avg_loss==0 jadi NaN
            # rsi = 100 - 100/(1+rs)                        -> NaN/0 jadi NaN
            # rsi.fillna(50)                                -> NaN (termasuk dari
            #                                                  avg_loss==0) SELALU jadi 50,
            #                                                  apapun nilai avg_gain saat itu.
            if ag is None or al is None or al == 0:
                rsi_vals.append(50.0)
            else:
                rs = ag / al
                rsi_vals.append(100 - (100 / (1 + rs)))
        return rsi_vals

    rsi_values  = calc_rsi(gains, losses, rsi_period)
    rsi2_values = calc_rsi(gains, losses, 2)

    for i, c in enumerate(candles):
        c["atr"]      = atr_values[i]
        c["wma_fast"] = wma_fast_values[i]
        c["wma_slow"] = wma_slow_values[i]
        c["rsi"]      = rsi_values[i]
        c["rsi2"]     = rsi2_values[i]

    return candles


# =====================================================================
# SWING POINTS
# =====================================================================

def detect_swings(candles, left=2, right=2):
    """Deteksi swing high / swing low fraktal. Identik logikanya dengan versi pandas."""
    candles = [dict(c) for c in candles]
    n = len(candles)
    for c in candles:
        c["swing_high"] = False
        c["swing_low"] = False

    for i in range(left, n - right):
        window_high = [candles[j]["high"] for j in range(i - left, i + right + 1)]
        window_low  = [candles[j]["low"] for j in range(i - left, i + right + 1)]

        max_h = max(window_high)
        if candles[i]["high"] == max_h and window_high.count(max_h) == 1:
            candles[i]["swing_high"] = True

        min_l = min(window_low)
        if candles[i]["low"] == min_l and window_low.count(min_l) == 1:
            candles[i]["swing_low"] = True

    return candles


# =====================================================================
# MARKET STRUCTURE: BOS & CHoCH
# =====================================================================

def detect_structure(candles):
    """Deteksi Break of Structure (BOS) dan Change of Character (CHoCH). Identik dengan versi pandas."""
    candles = [dict(c) for c in candles]
    for c in candles:
        c["bos_bullish"] = False
        c["bos_bearish"] = False
        c["choch_bullish"] = False
        c["choch_bearish"] = False
        c["trend"] = None

    last_swing_high = None
    last_swing_low = None
    trend = None

    for i, c in enumerate(candles):
        if c["swing_high"]:
            last_swing_high = c["high"]
        if c["swing_low"]:
            last_swing_low = c["low"]

        close = c["close"]

        if last_swing_high is not None and close > last_swing_high:
            if trend == "down":
                c["choch_bullish"] = True
            else:
                c["bos_bullish"] = True
            trend = "up"
            last_swing_high = None

        if last_swing_low is not None and close < last_swing_low:
            if trend == "up":
                c["choch_bearish"] = True
            else:
                c["bos_bearish"] = True
            trend = "down"
            last_swing_low = None

        c["trend"] = trend

    return candles


# =====================================================================
# LIQUIDITY SWEEP
# =====================================================================

def detect_sweep(candles, lookback=20):
    """Deteksi liquidity sweep. Identik logikanya dengan versi pandas."""
    candles = [dict(c) for c in candles]
    n = len(candles)
    for c in candles:
        c["sweep_high"] = False
        c["sweep_low"] = False

    for i in range(lookback, n):
        recent = candles[i - lookback:i]
        recent_highs = [c["high"] for c in recent]
        recent_lows  = [c["low"] for c in recent]
        recent_high = max(recent_highs)
        recent_low  = min(recent_lows)

        penetration_high = candles[i]["high"] - recent_high
        penetration_low  = recent_low - candles[i]["low"]
        avg_range = sum(c["high"] - c["low"] for c in recent) / len(recent)

        if (candles[i]["high"] > recent_high and candles[i]["close"] < recent_high
                and penetration_high > avg_range * 0.05):
            candles[i]["sweep_high"] = True

        if (candles[i]["low"] < recent_low and candles[i]["close"] > recent_low
                and penetration_low > avg_range * 0.05):
            candles[i]["sweep_low"] = True

    return candles


# =====================================================================
# VOLATILITY REGIME
# =====================================================================

def get_volatility_regime(candles):
    """
    Klasifikasi rezim volatilitas: HIGH_VOLATILITY / CHOPPY / TRENDING.
    Identik logikanya dengan versi pandas (baseline atr_avg dari 100
    candle terakhir, supaya tidak self-referencing dengan periode choppy
    yang sedang dideteksi).
    """
    n = len(candles)
    if n < 110:
        return "TRENDING"

    atr_now = candles[-1]["atr"]
    atr_tail_100 = [c["atr"] for c in candles[-100:] if c["atr"] is not None]
    if not atr_tail_100:
        return "TRENDING"
    atr_avg = sum(atr_tail_100) / len(atr_tail_100)

    if is_nan(atr_now) or atr_avg == 0:
        return "TRENDING"

    wma_last = candles[-1]["wma_slow"]
    wma_prev = candles[-5]["wma_slow"]
    if wma_last is None or wma_prev is None:
        return "TRENDING"
    wma_slope = abs(wma_last - wma_prev)

    if atr_now > atr_avg * 1.6:
        return "HIGH_VOLATILITY"

    if atr_now < atr_avg * 0.75 and wma_slope < (atr_avg * 0.15):
        return "CHOPPY"

    return "TRENDING"


# =====================================================================
# ORDER BLOCK
# =====================================================================

def detect_orderblock(candles, body_mult=1.5, avg_window=20, max_age=30):
    """Deteksi Order Block tervalidasi impulsive leg. Identik logikanya dengan versi pandas."""
    n = len(candles)
    bodies = [abs(c["close"] - c["open"]) for c in candles]
    avg_body = _rolling_mean(bodies, avg_window)

    bullish_obs = []
    bearish_obs = []

    for i in range(avg_window, n - 1):
        threshold = avg_body[i]
        if threshold is None:
            continue
        threshold *= body_mult

        body_next = abs(candles[i + 1]["close"] - candles[i + 1]["open"])

        is_bearish_candle = candles[i]["close"] < candles[i]["open"]
        is_bullish_candle = candles[i]["close"] > candles[i]["open"]
        next_bullish = candles[i + 1]["close"] > candles[i + 1]["open"]
        next_bearish = candles[i + 1]["close"] < candles[i + 1]["open"]

        if is_bearish_candle and next_bullish and body_next > threshold:
            if n - 1 - i <= max_age:
                bullish_obs.append({
                    "index": i, "high": candles[i]["high"], "low": candles[i]["low"],
                    "age": n - 1 - i
                })

        if is_bullish_candle and next_bearish and body_next > threshold:
            if n - 1 - i <= max_age:
                bearish_obs.append({
                    "index": i, "high": candles[i]["high"], "low": candles[i]["low"],
                    "age": n - 1 - i
                })

    nearest_bull_ob = _nearest_unmitigated(candles, bullish_obs, "bullish")
    nearest_bear_ob = _nearest_unmitigated(candles, bearish_obs, "bearish")

    return nearest_bull_ob, nearest_bear_ob


def _nearest_unmitigated(candles, ob_list, kind):
    """Ambil OB termuda yang belum sepenuhnya termitigasi."""
    last_close = candles[-1]["close"]
    for ob in sorted(ob_list, key=lambda x: x["age"]):
        if kind == "bullish" and last_close > ob["low"]:
            return ob
        if kind == "bearish" and last_close < ob["high"]:
            return ob
    return None


# =====================================================================
# FVG & iFVG
# =====================================================================

def detect_fvg_ifvg(candles, max_age=15, fill_window=20):
    """Deteksi FVG dan iFVG (failed-fill + reverse). Identik logikanya dengan versi pandas."""
    n = len(candles)

    fvg_bull_zones = []
    fvg_bear_zones = []

    for i in range(2, n):
        if candles[i]["low"] > candles[i - 2]["high"]:
            fvg_bull_zones.append({
                "start_idx": i, "top": candles[i]["low"], "bottom": candles[i - 2]["high"],
                "filled": False, "inversed": False, "fill_idx": None
            })

        if candles[i]["high"] < candles[i - 2]["low"]:
            fvg_bear_zones.append({
                "start_idx": i, "top": candles[i - 2]["low"], "bottom": candles[i]["high"],
                "filled": False, "inversed": False, "fill_idx": None
            })

    def process_zone(zone, kind):
        start = zone["start_idx"]
        for j in range(start + 1, min(start + fill_window, n)):
            if kind == "bull" and candles[j]["low"] <= zone["bottom"]:
                zone["filled"] = True
                zone["fill_idx"] = j
                break
            if kind == "bear" and candles[j]["high"] >= zone["top"]:
                zone["filled"] = True
                zone["fill_idx"] = j
                break

        if zone["filled"]:
            for k in range(zone["fill_idx"] + 1, min(zone["fill_idx"] + fill_window, n)):
                if kind == "bull" and candles[k]["close"] < zone["bottom"]:
                    zone["inversed"] = True
                    zone["inverse_idx"] = k
                    break
                if kind == "bear" and candles[k]["close"] > zone["top"]:
                    zone["inversed"] = True
                    zone["inverse_idx"] = k
                    break
        return zone

    fvg_bull_zones = [process_zone(z, "bull") for z in fvg_bull_zones]
    fvg_bear_zones = [process_zone(z, "bear") for z in fvg_bear_zones]

    fresh_bull_fvg = [z for z in fvg_bull_zones if not z["filled"] and (n - 1 - z["start_idx"]) <= max_age]
    fresh_bear_fvg = [z for z in fvg_bear_zones if not z["filled"] and (n - 1 - z["start_idx"]) <= max_age]

    ifvg_bull = [z for z in fvg_bear_zones if z["inversed"] and (n - 1 - z.get("inverse_idx", n)) <= max_age]
    ifvg_bear = [z for z in fvg_bull_zones if z["inversed"] and (n - 1 - z.get("inverse_idx", n)) <= max_age]

    nearest_fvg_bull = sorted(fresh_bull_fvg, key=lambda x: -x["start_idx"])[0] if fresh_bull_fvg else None
    nearest_fvg_bear = sorted(fresh_bear_fvg, key=lambda x: -x["start_idx"])[0] if fresh_bear_fvg else None
    nearest_ifvg_bull = sorted(ifvg_bull, key=lambda x: -x["inverse_idx"])[0] if ifvg_bull else None
    nearest_ifvg_bear = sorted(ifvg_bear, key=lambda x: -x["inverse_idx"])[0] if ifvg_bear else None

    return {
        "fvg_bull": nearest_fvg_bull, "fvg_bear": nearest_fvg_bear,
        "ifvg_bull": nearest_ifvg_bull, "ifvg_bear": nearest_ifvg_bear
    }


# =====================================================================
# FIBONACCI OTE ZONE
# =====================================================================

def get_fibo_ote(candles):
    """Hitung Fibonacci retracement dari leg impulsif terakhir. Identik logikanya dengan versi pandas."""
    swing_high_idxs = [i for i, c in enumerate(candles) if c["swing_high"]]
    swing_low_idxs  = [i for i, c in enumerate(candles) if c["swing_low"]]

    if not swing_high_idxs or not swing_low_idxs:
        return None

    last_high_idx = swing_high_idxs[-1]
    last_low_idx  = swing_low_idxs[-1]

    leg_low  = candles[last_low_idx]["low"]
    leg_high = candles[last_high_idx]["high"]
    direction = "up" if last_low_idx < last_high_idx else "down"

    diff = leg_high - leg_low
    if diff <= 0:
        return None

    if direction == "down":
        level_0   = leg_high
        level_618 = leg_low + diff * 0.382
        level_79  = leg_low + diff * 0.21
        level_1   = leg_low
    else:
        level_0   = leg_low
        level_618 = leg_low + diff * 0.618
        level_79  = leg_low + diff * 0.79
        level_1   = leg_high

    level_05 = leg_low + diff * 0.5

    ote_top = max(level_618, level_79)
    ote_bottom = min(level_618, level_79)

    current_price = candles[-1]["close"]
    midpoint = level_05
    zone = "premium" if current_price > midpoint else "discount"

    return {
        "direction": direction, "leg_low": leg_low, "leg_high": leg_high,
        "ote_top": ote_top, "ote_bottom": ote_bottom,
        "midpoint": midpoint, "zone": zone,
        "in_ote": ote_bottom <= current_price <= ote_top
    }


# =====================================================================
# HTF BIAS
# =====================================================================

def get_htf_bias(htf_candles):
    """Tentukan bias trend timeframe tinggi. Identik logikanya dengan versi pandas."""
    htf_candles = add_indicators(htf_candles)
    htf_candles = detect_swings(htf_candles)
    htf_candles = detect_structure(htf_candles)

    last = htf_candles[-1]
    wma_bias = "bullish" if last["wma_fast"] > last["wma_slow"] else "bearish"
    structure_bias = last["trend"] if last["trend"] else "neutral"

    if wma_bias == "bullish" and structure_bias == "up":
        bias = "bullish"
    elif wma_bias == "bearish" and structure_bias == "down":
        bias = "bearish"
    else:
        bias = "mixed"

    return {"bias": bias, "wma_bias": wma_bias, "structure_bias": structure_bias}


# =====================================================================
# RETEST CONFIRMATION
# =====================================================================

def get_retest_confirmation(candles, direction, ob, fvg_zone, lookback=10):
    """
    Validasi retest ke zona OB/FVG: price harus pernah menjauh dari zona,
    lalu kembali retest, baru bergerak searah sinyal. Identik logikanya
    dengan versi pandas.
    """
    if not ob and not fvg_zone:
        return True

    zone_low, zone_high = None, None
    zone_age = None
    if ob:
        zone_low, zone_high = ob["low"], ob["high"]
        zone_age = ob.get("age")
    elif fvg_zone:
        zone_low = fvg_zone.get("bottom")
        zone_high = fvg_zone.get("top")

    if zone_low is None or zone_high is None:
        return True

    if zone_age is not None and zone_age < 3:
        return False

    window_size = min(lookback, zone_age if zone_age else lookback)
    window = candles[-window_size:] if window_size > 0 else []
    if len(window) < 3:
        return False

    last_close = candles[-1]["close"]

    if direction == "BUY":
        away = any(c["low"] > zone_high for c in window)
        retested = any(c["low"] <= zone_high and c["high"] >= zone_low for c in window)
        back_in_direction = last_close >= zone_low
        return bool(away and retested and back_in_direction)
    else:
        away = any(c["high"] < zone_low for c in window)
        retested = any(c["low"] <= zone_high and c["high"] >= zone_low for c in window)
        back_in_direction = last_close <= zone_high
        return bool(away and retested and back_in_direction)


# =====================================================================
# SCORING ENGINE
# =====================================================================

def calculate_score(candles, ob_bull, ob_bear, fvg_data, fibo, bias_1h, bias_4h):
    """Hitung skor confluence bullish/bearish. Identik logikanya dengan versi pandas."""
    last = candles[-1]
    prev = candles[-2]

    score_bull = 0
    score_bear = 0
    reasons_bull = []
    reasons_bear = []

    recent = candles[-5:]
    if any(c["choch_bullish"] or c["bos_bullish"] for c in recent):
        score_bull += 20
        reasons_bull.append("BOS/CHoCH bullish dalam 5 candle terakhir")
    if any(c["choch_bearish"] or c["bos_bearish"] for c in recent):
        score_bear += 20
        reasons_bear.append("BOS/CHoCH bearish dalam 5 candle terakhir")

    if any(c["sweep_low"] for c in recent):
        score_bull += 15
        reasons_bull.append("Liquidity sweep di bawah (stop hunt) dalam 5 candle terakhir")
    if any(c["sweep_high"] for c in recent):
        score_bear += 15
        reasons_bear.append("Liquidity sweep di atas (stop hunt) dalam 5 candle terakhir")

    price = last["close"]
    atr_now = last["atr"] if not is_nan(last["atr"]) else price * 0.001
    ob_tolerance = atr_now * 0.5

    if ob_bull and (ob_bull["low"] - ob_tolerance) <= price <= (ob_bull["high"] + ob_tolerance):
        score_bull += 15
        reasons_bull.append("Price berada di/dekat zona bullish Order Block")

    ifvg_bull = fvg_data["ifvg_bull"]
    if ifvg_bull and (ifvg_bull["bottom"] - ob_tolerance) <= price <= (ifvg_bull["top"] + ob_tolerance):
        score_bull += 10
        reasons_bull.append("Inverse FVG bullish terkonfirmasi & price masih di zona")

    if ob_bear and (ob_bear["low"] - ob_tolerance) <= price <= (ob_bear["high"] + ob_tolerance):
        score_bear += 15
        reasons_bear.append("Price berada di/dekat zona bearish Order Block")

    ifvg_bear = fvg_data["ifvg_bear"]
    if ifvg_bear and (ifvg_bear["bottom"] - ob_tolerance) <= price <= (ifvg_bear["top"] + ob_tolerance):
        score_bear += 10
        reasons_bear.append("Inverse FVG bearish terkonfirmasi & price masih di zona")

    if fibo:
        if fibo["in_ote"] and fibo["direction"] == "down" and fibo["zone"] == "discount":
            score_bull += 12
            reasons_bull.append("Price di zona OTE Fibo 0.618-0.79 (discount)")
        if fibo["in_ote"] and fibo["direction"] == "up" and fibo["zone"] == "premium":
            score_bear += 12
            reasons_bear.append("Price di zona OTE Fibo 0.618-0.79 (premium)")

    wma_f_last = last["wma_fast"]
    wma_s_last = last["wma_slow"]
    wma_f_prev = prev["wma_fast"]
    wma_s_prev = prev["wma_slow"]
    if None not in (wma_f_last, wma_s_last, wma_f_prev, wma_s_prev):
        if wma_f_last > wma_s_last and wma_f_prev <= wma_s_prev:
            score_bull += 10
            reasons_bull.append("WMA9 cross up WMA119 (trigger momentum)")
        if wma_f_last < wma_s_last and wma_f_prev >= wma_s_prev:
            score_bear += 10
            reasons_bear.append("WMA9 cross down WMA119 (trigger momentum)")

    if 35 <= last["rsi"] <= 55 and last["rsi"] > prev["rsi"]:
        score_bull += 8
        reasons_bull.append(f"RSI rebound dari area netral-rendah ({last['rsi']:.1f})")
    if 45 <= last["rsi"] <= 65 and last["rsi"] < prev["rsi"]:
        score_bear += 8
        reasons_bear.append(f"RSI turun dari area netral-tinggi ({last['rsi']:.1f})")
    if last["rsi"] < 30:
        score_bull += 5
        reasons_bull.append(f"RSI oversold ({last['rsi']:.1f})")
    if last["rsi"] > 70:
        score_bear += 5
        reasons_bear.append(f"RSI overbought ({last['rsi']:.1f})")

    if bias_1h["bias"] == "bullish":
        score_bull += 5
        reasons_bull.append("Bias 1H bullish")
    if bias_4h["bias"] == "bullish":
        score_bull += 5
        reasons_bull.append("Bias 4H bullish")
    if bias_1h["bias"] == "bearish":
        score_bear += 5
        reasons_bear.append("Bias 1H bearish")
    if bias_4h["bias"] == "bearish":
        score_bear += 5
        reasons_bear.append("Bias 4H bearish")

    score_bull = min(score_bull, 80)
    score_bear = min(score_bear, 80)

    return score_bull, score_bear, reasons_bull, reasons_bear


# =====================================================================
# TRADE PLAN - SL/TP DINAMIS (ATR + OB/iFVG + Fibonacci + Volatility Regime)
# =====================================================================

_TP_MULTIPLIERS = {
    "HIGH_VOLATILITY": {"sl": 1.4, "tp1": 1.6, "tp2": 2.4, "tp3": 3.2},
    "CHOPPY":          {"sl": 0.8, "tp1": 1.0, "tp2": 1.6, "tp3": 2.2},
    "TRENDING":        {"sl": 1.1, "tp1": 1.2, "tp2": 2.0, "tp3": 3.0},
}


def build_trade_plan(direction, candles, ob, fvg_zone, fibo, volatility_regime="TRENDING",
                      rr_min=RISK_REWARD_MIN):
    """SL/TP dinamis dengan TP1/TP2/TP3 adaptive volatility regime. Identik logikanya dengan versi pandas."""
    last = candles[-1]
    entry = last["close"]
    atr = last["atr"]

    if is_nan(atr) or atr is None or atr <= 0:
        return None

    mult = _TP_MULTIPLIERS.get(volatility_regime, _TP_MULTIPLIERS["TRENDING"])
    atr_buffer = atr * ATR_SL_MULT

    if direction == "BUY":
        structural_sl_candidates = []
        if ob:
            structural_sl_candidates.append(ob["low"])
        if fvg_zone:
            structural_sl_candidates.append(fvg_zone.get("bottom", entry - atr_buffer))
        if fibo:
            structural_sl_candidates.append(fibo["leg_low"])

        structural_sl = min(structural_sl_candidates) if structural_sl_candidates else entry - atr_buffer
        sl = min(structural_sl - atr_buffer * 0.3, entry - atr * mult["sl"])

        risk = entry - sl
        if risk <= 0:
            return None

        tp1 = entry + (risk * max(mult["tp1"], rr_min))
        tp2 = entry + (risk * mult["tp2"])
        tp3_structural = fibo["leg_high"] if fibo else None
        tp3_rr = entry + (risk * mult["tp3"])
        tp3 = max(tp3_structural, tp3_rr) if tp3_structural else tp3_rr

    else:
        structural_sl_candidates = []
        if ob:
            structural_sl_candidates.append(ob["high"])
        if fvg_zone:
            structural_sl_candidates.append(fvg_zone.get("top", entry + atr_buffer))
        if fibo:
            structural_sl_candidates.append(fibo["leg_high"])

        structural_sl = max(structural_sl_candidates) if structural_sl_candidates else entry + atr_buffer
        sl = max(structural_sl + atr_buffer * 0.3, entry + atr * mult["sl"])

        risk = sl - entry
        if risk <= 0:
            return None

        tp1 = entry - (risk * max(mult["tp1"], rr_min))
        tp2 = entry - (risk * mult["tp2"])
        tp3_structural = fibo["leg_low"] if fibo else None
        tp3_rr = entry - (risk * mult["tp3"])
        tp3 = min(tp3_structural, tp3_rr) if tp3_structural else tp3_rr

    actual_risk = abs(entry - sl)
    reward_tp1 = abs(tp1 - entry)
    rr_tp1 = reward_tp1 / actual_risk if actual_risk > 0 else 0

    return {
        "entry": round(float(entry), 2),
        "stop_loss": round(float(sl), 2),
        "take_profit": round(float(tp1), 2),
        "tp1": round(float(tp1), 2),
        "tp2": round(float(tp2), 2),
        "tp3": round(float(tp3), 2),
        "risk_usd_per_btc": round(float(actual_risk), 2),
        "reward_usd_per_btc": round(float(reward_tp1), 2),
        "risk_reward": round(float(rr_tp1), 2),
        "atr_used": round(float(atr), 2),
        "volatility_regime": volatility_regime,
    }


# =====================================================================
# SIGNAL DECISION
# =====================================================================

def get_signal(score_bull, score_bear, fibo, last_candle):
    """Tentukan sinyal kandidat. Identik logikanya dengan versi pandas."""
    rsi = last_candle["rsi"]

    hard_block_buy = fibo and fibo["zone"] == "premium" and rsi > 75
    hard_block_sell = fibo and fibo["zone"] == "discount" and rsi < 25

    if score_bull >= SCORE_MIN_STRONG and score_bull > score_bear and not hard_block_buy:
        return "BUY STRONG", score_bull
    if score_bull >= SCORE_MIN_LIGHT and score_bull > score_bear and not hard_block_buy:
        return "BUY LIGHT", score_bull
    if score_bear >= SCORE_MIN_STRONG and score_bear > score_bull and not hard_block_sell:
        return "SELL STRONG", score_bear
    if score_bear >= SCORE_MIN_LIGHT and score_bear > score_bull and not hard_block_sell:
        return "SELL LIGHT", score_bear

    return "NO SIGNAL / WAIT", max(score_bull, score_bear)


# =====================================================================
# MAIN ANALYSIS FUNCTION (dipanggil oleh UI maupun service)
# =====================================================================

def run_analysis():
    """
    Jalankan satu siklus analisa lengkap. Return dict berisi semua hasil,
    atau dict dengan key 'error' jika gagal. Identik logikanya dengan
    versi pandas - hanya struktur data internal yang berbeda (list of
    dict, bukan DataFrame).
    """
    entry_candles, err1 = get_binance_klines(interval=TF_ENTRY, limit=LIMIT)
    htf1_candles, err2  = get_binance_klines(interval=TF_BIAS_1, limit=160)
    htf2_candles, err3  = get_binance_klines(interval=TF_BIAS_2, limit=160)

    if entry_candles is None or htf1_candles is None or htf2_candles is None:
        return {"error": err1 or err2 or err3 or "Data tidak lengkap"}

    if len(entry_candles) < 130 or len(htf1_candles) < 130 or len(htf2_candles) < 130:
        return {"error": "Data terlalu sedikit untuk analisa reliable (perlu >=130 candle untuk WMA119)"}

    entry_candles = add_indicators(entry_candles)
    entry_candles = detect_swings(entry_candles)
    entry_candles = detect_structure(entry_candles)
    entry_candles = detect_sweep(entry_candles)

    volatility_regime = get_volatility_regime(entry_candles)

    ob_bull, ob_bear = detect_orderblock(entry_candles)
    fvg_data = detect_fvg_ifvg(entry_candles)
    fibo = get_fibo_ote(entry_candles)

    bias_1h = get_htf_bias(htf1_candles)
    bias_4h = get_htf_bias(htf2_candles)

    score_bull, score_bear, reasons_bull, reasons_bear = calculate_score(
        entry_candles, ob_bull, ob_bear, fvg_data, fibo, bias_1h, bias_4h
    )

    last_candle = entry_candles[-1]
    signal, score = get_signal(score_bull, score_bear, fibo, last_candle)
    reasons = reasons_bull if "BUY" in signal else reasons_bear if "SELL" in signal else []

    retest_ok = True
    if "BUY" in signal:
        relevant_fvg = fvg_data["ifvg_bull"] or fvg_data["fvg_bull"]
        retest_ok = get_retest_confirmation(entry_candles, "BUY", ob_bull, relevant_fvg)
        if not retest_ok:
            reasons = reasons + ["[DITAHAN] Belum ada retest valid ke zona OB/FVG"]
            signal = "NO SIGNAL / WAIT"
    elif "SELL" in signal:
        relevant_fvg = fvg_data["ifvg_bear"] or fvg_data["fvg_bear"]
        retest_ok = get_retest_confirmation(entry_candles, "SELL", ob_bear, relevant_fvg)
        if not retest_ok:
            reasons = reasons + ["[DITAHAN] Belum ada retest valid ke zona OB/FVG"]
            signal = "NO SIGNAL / WAIT"

    plan = None
    if "BUY" in signal:
        relevant_fvg = fvg_data["ifvg_bull"] or fvg_data["fvg_bull"]
        plan = build_trade_plan("BUY", entry_candles, ob_bull, relevant_fvg, fibo, volatility_regime)
    elif "SELL" in signal:
        relevant_fvg = fvg_data["ifvg_bear"] or fvg_data["fvg_bear"]
        plan = build_trade_plan("SELL", entry_candles, ob_bear, relevant_fvg, fibo, volatility_regime)

    atr_val = last_candle["atr"]
    wma_fast_val = last_candle["wma_fast"]
    wma_slow_val = last_candle["wma_slow"]
    rsi2_val = last_candle["rsi2"]

    return {
        "error": None,
        "time": _time_to_str(last_candle["time"]),
        "close": round(float(last_candle["close"]), 2),
        "atr": round(float(atr_val), 2) if not is_nan(atr_val) else None,
        "rsi": round(float(last_candle["rsi"]), 1),
        "rsi2": round(float(rsi2_val), 1) if not is_nan(rsi2_val) else None,
        "wma_fast": round(float(wma_fast_val), 2) if not is_nan(wma_fast_val) else None,
        "wma_slow": round(float(wma_slow_val), 2) if not is_nan(wma_slow_val) else None,
        "volatility_regime": volatility_regime,
        "bias_1h": bias_1h["bias"],
        "bias_4h": bias_4h["bias"],
        "fibo_zone": fibo["zone"] if fibo else None,
        "fibo_direction": fibo["direction"] if fibo else None,
        "fibo_in_ote": fibo["in_ote"] if fibo else None,
        "signal": signal,
        "score": score,
        "reasons": reasons,
        "plan": plan,
    }
