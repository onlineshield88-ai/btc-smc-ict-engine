"""
engine.py
================================================================================
Core engine analisa SMC + ICT + WMA + RSI + Fibonacci untuk BTCUSDT Futures.

Ini adalah versi REFACTOR dari smc_ict_hybrid_btcusdt.py (versi CLI) menjadi
importable module, dipakai bersama oleh:
  - main.py   (Kivy UI, untuk tampilan saat app dibuka)
  - service.py (foreground service Android, untuk jalan di background)

Semua logika deteksi (market structure, order block, FVG/iFVG, fibo OTE,
scoring, trade plan) IDENTIK dengan versi yang sudah diuji & dikalibrasi
sebelumnya. Tidak ada perubahan logika - hanya restrukturisasi agar reusable.
================================================================================
"""

import requests
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")


# =====================================================================
# CONFIG (bisa di-override dari UI settings, lihat config.py)
# =====================================================================

SYMBOL          = "BTCUSDT"
TF_ENTRY        = "15m"
TF_BIAS_1       = "1h"
TF_BIAS_2       = "4h"

LIMIT           = 300  # cukup untuk WMA119 (perlu min ~119) + slope lookback + swing detection
RISK_REWARD_MIN = 1.5
ATR_SL_MULT     = 1.2
ATR_PERIOD      = 14

SCORE_MIN_LIGHT  = 40
SCORE_MIN_STRONG = 55

ENGINE_VERSION  = "HYBRID-SMC-ICT-WMA-RSI-FIBO v1.0"


# =====================================================================
# BINANCE FETCH
# =====================================================================

def get_binance_klines(symbol=SYMBOL, interval="15m", limit=LIMIT, futures=True):
    base_url = "https://fapi.binance.com/fapi/v1/klines" if futures \
        else "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    try:
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()

        if isinstance(data, dict) and data.get("code"):
            return None, f"Binance API error: {data}"

        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])

        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = df[col].astype(float)

        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df[["time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
        return df, None

    except Exception as e:
        return None, f"Fetch gagal: {e}"


# =====================================================================
# INDICATORS
# =====================================================================

def add_indicators(df, atr_period=ATR_PERIOD, wma_fast=9, wma_slow=119, rsi_period=14):
    """
    PERUBAHAN v2: wma_slow default diganti dari 21 -> 119.
    WMA9/WMA21 di BTC 15m terlalu sensitif dan sering fake-cross saat choppy.
    WMA9/WMA119 (diadopsi dari smclite v7.6.8) jauh lebih stabil sebagai
    filter trend menengah, sambil WMA9 tetap dipakai sebagai trigger cepat.
    """
    df = df.copy()

    high_low   = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close  = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = true_range.ewm(alpha=1 / atr_period, adjust=False).mean()

    def wma(series, length):
        weights = np.arange(1, length + 1)
        return series.rolling(length).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    df["wma_fast"] = wma(df["close"], wma_fast)
    df["wma_slow"] = wma(df["close"], wma_slow)

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / rsi_period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / rsi_period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    # RSI(2) - dari smclite, dipakai untuk deteksi pump exhaustion (sangat
    # sensitif terhadap overbought/oversold ekstrem jangka pendek)
    rsi2_period = 2
    avg_gain2 = gain.ewm(alpha=1 / rsi2_period, adjust=False).mean()
    avg_loss2 = loss.ewm(alpha=1 / rsi2_period, adjust=False).mean()
    rs2 = avg_gain2 / avg_loss2.replace(0, np.nan)
    df["rsi2"] = 100 - (100 / (1 + rs2))
    df["rsi2"] = df["rsi2"].fillna(50)

    return df


# =====================================================================
# SWING POINTS
# =====================================================================

def detect_swings(df, left=2, right=2):
    df = df.copy()
    df["swing_high"] = False
    df["swing_low"] = False

    n = len(df)
    for i in range(left, n - right):
        window_high = df["high"].iloc[i - left: i + right + 1]
        window_low  = df["low"].iloc[i - left: i + right + 1]

        if df["high"].iloc[i] == window_high.max() and \
           (window_high == window_high.max()).sum() == 1:
            df.loc[df.index[i], "swing_high"] = True

        if df["low"].iloc[i] == window_low.min() and \
           (window_low == window_low.min()).sum() == 1:
            df.loc[df.index[i], "swing_low"] = True

    return df


# =====================================================================
# MARKET STRUCTURE: BOS & CHoCH
# =====================================================================

def detect_structure(df):
    df = df.copy()
    df["bos_bullish"]   = False
    df["bos_bearish"]   = False
    df["choch_bullish"] = False
    df["choch_bearish"] = False
    df["trend"] = None

    last_swing_high = None
    last_swing_low  = None
    trend = None

    for i in range(len(df)):
        if df["swing_high"].iloc[i]:
            last_swing_high = df["high"].iloc[i]
        if df["swing_low"].iloc[i]:
            last_swing_low = df["low"].iloc[i]

        close = df["close"].iloc[i]

        if last_swing_high is not None and close > last_swing_high:
            if trend == "down":
                df.loc[df.index[i], "choch_bullish"] = True
            else:
                df.loc[df.index[i], "bos_bullish"] = True
            trend = "up"
            last_swing_high = None

        if last_swing_low is not None and close < last_swing_low:
            if trend == "up":
                df.loc[df.index[i], "choch_bearish"] = True
            else:
                df.loc[df.index[i], "bos_bearish"] = True
            trend = "down"
            last_swing_low = None

        df.loc[df.index[i], "trend"] = trend

    return df


# =====================================================================
# LIQUIDITY SWEEP
# =====================================================================

def detect_sweep(df, lookback=20):
    df = df.copy()
    df["sweep_high"] = False
    df["sweep_low"]  = False

    for i in range(lookback, len(df)):
        recent = df.iloc[i - lookback:i]
        recent_high = recent["high"].max()
        recent_low  = recent["low"].min()

        penetration_high = df["high"].iloc[i] - recent_high
        penetration_low  = recent_low - df["low"].iloc[i]
        avg_range = (recent["high"] - recent["low"]).mean()

        if (df["high"].iloc[i] > recent_high and df["close"].iloc[i] < recent_high
                and penetration_high > avg_range * 0.05):
            df.loc[df.index[i], "sweep_high"] = True

        if (df["low"].iloc[i] < recent_low and df["close"].iloc[i] > recent_low
                and penetration_low > avg_range * 0.05):
            df.loc[df.index[i], "sweep_low"] = True

    return df


# =====================================================================
# VOLATILITY REGIME (diadopsi dari smclite v7.6.8)
# =====================================================================

def get_volatility_regime(df):
    """
    Klasifikasi rezim volatilitas pasar saat ini berdasarkan ATR relatif
    terhadap rata-rata jangka lebih panjang, dikombinasikan dengan slope WMA119.

    HIGH_VOLATILITY: ATR jauh di atas rata-rata - buffer SL/TP perlu melebar
    CHOPPY: ATR rendah + WMA119 nyaris flat - market sideways, sinyal lebih
            rawan fake-out, buffer SL/TP perlu menyempit
    TRENDING: kondisi normal/sehat untuk mengikuti arah trend

    CATATAN: atr_avg baseline pakai window 100 candle (bukan 50) supaya
    tidak self-referencing - kalau baseline dihitung dari window yang sama
    dengan periode choppy yang sedang dideteksi, baseline itu sendiri ikut
    turun dan rasio tidak pernah benar-benar lolos threshold.
    """
    if len(df) < 110:
        return "TRENDING"

    atr_now = df["atr"].iloc[-1]
    atr_avg = df["atr"].tail(100).mean()

    if pd.isna(atr_now) or pd.isna(atr_avg) or atr_avg == 0:
        return "TRENDING"

    wma_slope = abs(df["wma_slow"].iloc[-1] - df["wma_slow"].iloc[-5])

    if atr_now > atr_avg * 1.6:
        return "HIGH_VOLATILITY"

    if atr_now < atr_avg * 0.75 and wma_slope < (atr_avg * 0.15):
        return "CHOPPY"

    return "TRENDING"


# =====================================================================
# ORDER BLOCK
# =====================================================================

def detect_orderblock(df, body_mult=1.5, avg_window=20, max_age=30):
    df = df.copy()
    avg_body = (df["close"] - df["open"]).abs().rolling(avg_window).mean()

    bullish_obs = []
    bearish_obs = []

    n = len(df)
    for i in range(avg_window, n - 1):
        body_next = abs(df["close"].iloc[i + 1] - df["open"].iloc[i + 1])
        threshold = avg_body.iloc[i] * body_mult
        if pd.isna(threshold):
            continue

        is_bearish_candle = df["close"].iloc[i] < df["open"].iloc[i]
        is_bullish_candle = df["close"].iloc[i] > df["open"].iloc[i]
        next_bullish = df["close"].iloc[i + 1] > df["open"].iloc[i + 1]
        next_bearish = df["close"].iloc[i + 1] < df["open"].iloc[i + 1]

        if is_bearish_candle and next_bullish and body_next > threshold:
            if n - 1 - i <= max_age:
                bullish_obs.append({
                    "index": i, "high": df["high"].iloc[i], "low": df["low"].iloc[i],
                    "age": n - 1 - i
                })

        if is_bullish_candle and next_bearish and body_next > threshold:
            if n - 1 - i <= max_age:
                bearish_obs.append({
                    "index": i, "high": df["high"].iloc[i], "low": df["low"].iloc[i],
                    "age": n - 1 - i
                })

    nearest_bull_ob = _nearest_unmitigated(df, bullish_obs, "bullish")
    nearest_bear_ob = _nearest_unmitigated(df, bearish_obs, "bearish")

    return nearest_bull_ob, nearest_bear_ob


def _nearest_unmitigated(df, ob_list, kind):
    last_close = df["close"].iloc[-1]
    for ob in sorted(ob_list, key=lambda x: x["age"]):
        if kind == "bullish" and last_close > ob["low"]:
            return ob
        if kind == "bearish" and last_close < ob["high"]:
            return ob
    return None


# =====================================================================
# FVG & iFVG
# =====================================================================

def detect_fvg_ifvg(df, max_age=15, fill_window=20):
    df = df.copy()
    n = len(df)

    fvg_bull_zones = []
    fvg_bear_zones = []

    for i in range(2, n):
        if df["low"].iloc[i] > df["high"].iloc[i - 2]:
            fvg_bull_zones.append({
                "start_idx": i, "top": df["low"].iloc[i], "bottom": df["high"].iloc[i - 2],
                "filled": False, "inversed": False, "fill_idx": None
            })

        if df["high"].iloc[i] < df["low"].iloc[i - 2]:
            fvg_bear_zones.append({
                "start_idx": i, "top": df["low"].iloc[i - 2], "bottom": df["high"].iloc[i],
                "filled": False, "inversed": False, "fill_idx": None
            })

    def process_zone(zone, kind):
        start = zone["start_idx"]
        for j in range(start + 1, min(start + fill_window, n)):
            if kind == "bull" and df["low"].iloc[j] <= zone["bottom"]:
                zone["filled"] = True
                zone["fill_idx"] = j
                break
            if kind == "bear" and df["high"].iloc[j] >= zone["top"]:
                zone["filled"] = True
                zone["fill_idx"] = j
                break

        if zone["filled"]:
            for k in range(zone["fill_idx"] + 1, min(zone["fill_idx"] + fill_window, n)):
                if kind == "bull" and df["close"].iloc[k] < zone["bottom"]:
                    zone["inversed"] = True
                    zone["inverse_idx"] = k
                    break
                if kind == "bear" and df["close"].iloc[k] > zone["top"]:
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

def get_fibo_ote(df):
    df = df.copy()
    swing_highs = df[df["swing_high"]]
    swing_lows  = df[df["swing_low"]]

    if len(swing_highs) == 0 or len(swing_lows) == 0:
        return None

    last_high_idx = swing_highs.index[-1]
    last_low_idx  = swing_lows.index[-1]

    leg_low  = df["low"].loc[last_low_idx]
    leg_high = df["high"].loc[last_high_idx]
    direction = "up" if last_low_idx < last_high_idx else "down"

    diff = leg_high - leg_low
    if diff <= 0:
        return None

    levels = {
        "0.0": leg_high if direction == "down" else leg_low,
        "0.5": leg_low + diff * 0.5,
        "0.618": leg_low + diff * 0.382 if direction == "down" else leg_low + diff * 0.618,
        "0.79": leg_low + diff * 0.21 if direction == "down" else leg_low + diff * 0.79,
        "1.0": leg_low if direction == "down" else leg_high,
    }

    ote_top = max(levels["0.618"], levels["0.79"])
    ote_bottom = min(levels["0.618"], levels["0.79"])

    current_price = df["close"].iloc[-1]
    midpoint = levels["0.5"]
    zone = "premium" if current_price > midpoint else "discount"

    return {
        "direction": direction, "leg_low": leg_low, "leg_high": leg_high,
        "ote_top": ote_top, "ote_bottom": ote_bottom,
        "midpoint": midpoint, "zone": zone,
        "in_ote": ote_bottom <= current_price <= ote_top
    }


# =====================================================================
# RETEST CONFIRMATION (versi diperketat - retest ke zona OB/FVG asli)
# =====================================================================

def get_retest_confirmation(df, direction, ob, fvg_zone, lookback=10):
    """
    PERBAIKAN dari smclite v7.6.8: versi smclite hanya cek price vs WMA9
    (parameter high/low di-assign tapi tidak pernah dipakai - dead code).
    Itu tidak benar-benar memverifikasi bahwa price sudah RETEST ke zona
    struktural (OB/FVG) yang menjadi alasan sinyal muncul.

    PERBAIKAN v2 (setelah testing): versi pertama filter ini ternyata
    redundant dengan calculate_score() - scoring sendiri sudah mensyaratkan
    price dekat zona OB sebagai bagian confluence, jadi "price overlap
    dengan zona di N candle terakhir" hampir selalu otomatis benar dan
    filter tidak menambah selektivitas apapun (pass rate >97%, basically
    tidak berfungsi sebagai filter).

    Definisi retest yang benar: candle SUDAH PERNAH MENINGGALKAN zona
    (bergerak impulsif menjauh setelah OB/FVG terbentuk), KEMUDIAN kembali
    menyentuh zona itu sekali lagi (retest), baru kemudian close kembali
    bergerak searah sinyal. Ini independen dari kondisi scoring karena
    mensyaratkan riwayat "menjauh dulu" yang tidak dicek oleh scoring.

    Jika tidak ada OB maupun FVG sama sekali (sinyal murni dari momentum/
    sweep/fibo), retest dianggap valid secara default - tidak ada zona
    konkret untuk diretest.
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

    # Tentukan window candle SETELAH zona terbentuk untuk dicek pola
    # "menjauh lalu retest". Kalau OB/FVG baru terbentuk 1-2 candle lalu,
    # belum ada cukup waktu untuk pola retest sungguhan terjadi - dianggap
    # belum valid (terlalu dini, tunggu cycle berikutnya).
    if zone_age is not None and zone_age < 3:
        return False

    window = df.tail(min(lookback, zone_age if zone_age else lookback))
    if len(window) < 3:
        return False

    last_close = df["close"].iloc[-1]

    if direction == "BUY":
        # Harus pernah ada candle yang close-nya jelas DI ATAS zona
        # (bergerak menjauh ke atas) sebelum candle² terakhir kembali turun
        away = (window["low"] > zone_high).any()
        # Lalu harus ada candle yang kembali masuk/menyentuh zona (retest)
        retested = ((window["low"] <= zone_high) & (window["high"] >= zone_low)).any()
        back_in_direction = last_close >= zone_low
        return bool(away and retested and back_in_direction)
    else:
        away = (window["high"] < zone_low).any()
        retested = ((window["low"] <= zone_high) & (window["high"] >= zone_low)).any()
        back_in_direction = last_close <= zone_high
        return bool(away and retested and back_in_direction)


# =====================================================================
# HTF BIAS
# =====================================================================

def get_htf_bias(df_htf):
    df_htf = add_indicators(df_htf)
    df_htf = detect_swings(df_htf)
    df_htf = detect_structure(df_htf)

    last = df_htf.iloc[-1]
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
# SCORING ENGINE
# =====================================================================

def calculate_score(df, ob_bull, ob_bear, fvg_data, fibo, bias_1h, bias_4h):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    score_bull = 0
    score_bear = 0
    reasons_bull = []
    reasons_bear = []

    recent = df.tail(5)
    if recent["choch_bullish"].any() or recent["bos_bullish"].any():
        score_bull += 20
        reasons_bull.append("BOS/CHoCH bullish dalam 5 candle terakhir")
    if recent["choch_bearish"].any() or recent["bos_bearish"].any():
        score_bear += 20
        reasons_bear.append("BOS/CHoCH bearish dalam 5 candle terakhir")

    if recent["sweep_low"].any():
        score_bull += 15
        reasons_bull.append("Liquidity sweep di bawah (stop hunt) dalam 5 candle terakhir")
    if recent["sweep_high"].any():
        score_bear += 15
        reasons_bear.append("Liquidity sweep di atas (stop hunt) dalam 5 candle terakhir")

    price = last["close"]
    atr_now = last["atr"] if not pd.isna(last["atr"]) else price * 0.001
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

    if last["wma_fast"] > last["wma_slow"] and prev["wma_fast"] <= prev["wma_slow"]:
        score_bull += 10
        reasons_bull.append("WMA9 cross up WMA21 (trigger momentum)")
    if last["wma_fast"] < last["wma_slow"] and prev["wma_fast"] >= prev["wma_slow"]:
        score_bear += 10
        reasons_bear.append("WMA9 cross down WMA21 (trigger momentum)")

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

# Multiplier risk:reward per level TP, disesuaikan dengan volatility regime
# (diadopsi & diadaptasi dari smclite v7.6.8 - versi smclite pakai ini untuk
# SEMUA basis SL/TP; di sini hanya dipakai untuk multi-level TP, SL tetap
# struktural OB/iFVG/Fibo + ATR seperti versi asli engine ini)
_TP_MULTIPLIERS = {
    "HIGH_VOLATILITY": {"sl": 1.4, "tp1": 1.6, "tp2": 2.4, "tp3": 3.2},
    "CHOPPY":          {"sl": 0.8, "tp1": 1.0, "tp2": 1.6, "tp3": 2.2},
    "TRENDING":        {"sl": 1.1, "tp1": 1.2, "tp2": 2.0, "tp3": 3.0},
}


def build_trade_plan(direction, df, ob, fvg_zone, fibo, volatility_regime="TRENDING",
                      rr_min=RISK_REWARD_MIN):
    """
    SEMUA nilai entry/SL/TP dihitung dinamis dari kondisi pasar SAAT INI
    (candle terakhir yang baru ditutup) - tidak ada angka hardcoded.

    Entry = harga close live.
    SL    = kombinasi struktur OB/iFVG/Fibo + buffer ATR yang besarnya
            proporsional terhadap volatilitas pasar saat itu.
    TP1/TP2/TP3 = multi-level take profit (diadopsi dari smclite v7.6.8),
            multiplier risk:reward-nya beradaptasi terhadap volatility_regime:
            HIGH_VOLATILITY melebar (target lebih jauh, sesuai swing besar),
            CHOPPY menyempit (target lebih dekat, hindari overstay di sideways),
            TRENDING di tengah-tengah (kondisi normal).
            take_profit (single, untuk kompatibilitas mundur) = TP1.
    """
    last = df.iloc[-1]
    entry = last["close"]
    atr = last["atr"]

    if pd.isna(atr) or atr <= 0:
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
        "take_profit": round(float(tp1), 2),   # kompatibilitas mundur (UI lama)
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

def get_signal(score_bull, score_bear, fibo, last_row):
    """
    Tentukan sinyal kandidat berdasarkan skor confluence. Ini BELUM final -
    run_analysis() akan memvalidasi lebih lanjut dengan retest filter
    sebelum sinyal benar-benar dianggap actionable.
    """
    rsi = last_row["rsi"]

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
    atau dict dengan key 'error' jika gagal.
    Tidak ada side-effect (print/notify) di sini - itu tanggung jawab caller.

    PIPELINE v2 (update dari hasil komparasi dengan smclite v7.6.8):
    1. Hitung semua indikator & deteksi struktur seperti sebelumnya
    2. Hitung volatility_regime (BARU - diadopsi dari smclite)
    3. Tentukan sinyal KANDIDAT dari scoring confluence (seperti sebelumnya)
    4. Validasi retest filter ke zona OB/FVG (BARU - retest filter yang
       sudah diperbaiki, retest ke struktur asli bukan ke WMA9)
       -> Jika sinyal kandidat ada tapi retest gagal, downgrade ke WAIT
    5. Build trade plan dengan TP1/TP2/TP3 adaptive volatility (BARU)
    """
    df_entry, err1 = get_binance_klines(interval=TF_ENTRY, limit=LIMIT)
    df_1h, err2    = get_binance_klines(interval=TF_BIAS_1, limit=160)
    df_4h, err3    = get_binance_klines(interval=TF_BIAS_2, limit=160)

    if df_entry is None or df_1h is None or df_4h is None:
        return {"error": err1 or err2 or err3 or "Data tidak lengkap"}

    if len(df_entry) < 130 or len(df_1h) < 130 or len(df_4h) < 130:
        return {"error": "Data terlalu sedikit untuk analisa reliable (perlu >=130 candle untuk WMA119)"}

    df_entry = add_indicators(df_entry)
    df_entry = detect_swings(df_entry)
    df_entry = detect_structure(df_entry)
    df_entry = detect_sweep(df_entry)

    volatility_regime = get_volatility_regime(df_entry)

    ob_bull, ob_bear = detect_orderblock(df_entry)
    fvg_data = detect_fvg_ifvg(df_entry)
    fibo = get_fibo_ote(df_entry)

    bias_1h = get_htf_bias(df_1h)
    bias_4h = get_htf_bias(df_4h)

    score_bull, score_bear, reasons_bull, reasons_bear = calculate_score(
        df_entry, ob_bull, ob_bear, fvg_data, fibo, bias_1h, bias_4h
    )

    last_row = df_entry.iloc[-1]
    signal, score = get_signal(score_bull, score_bear, fibo, last_row)
    reasons = reasons_bull if "BUY" in signal else reasons_bear if "SELL" in signal else []

    # --- Retest filter (BARU) ---
    retest_ok = True
    if "BUY" in signal:
        relevant_fvg = fvg_data["ifvg_bull"] or fvg_data["fvg_bull"]
        retest_ok = get_retest_confirmation(df_entry, "BUY", ob_bull, relevant_fvg)
        if not retest_ok:
            reasons = reasons + ["[DITAHAN] Belum ada retest valid ke zona OB/FVG"]
            signal = "NO SIGNAL / WAIT"
    elif "SELL" in signal:
        relevant_fvg = fvg_data["ifvg_bear"] or fvg_data["fvg_bear"]
        retest_ok = get_retest_confirmation(df_entry, "SELL", ob_bear, relevant_fvg)
        if not retest_ok:
            reasons = reasons + ["[DITAHAN] Belum ada retest valid ke zona OB/FVG"]
            signal = "NO SIGNAL / WAIT"

    plan = None
    if "BUY" in signal:
        relevant_fvg = fvg_data["ifvg_bull"] or fvg_data["fvg_bull"]
        plan = build_trade_plan("BUY", df_entry, ob_bull, relevant_fvg, fibo, volatility_regime)
    elif "SELL" in signal:
        relevant_fvg = fvg_data["ifvg_bear"] or fvg_data["fvg_bear"]
        plan = build_trade_plan("SELL", df_entry, ob_bear, relevant_fvg, fibo, volatility_regime)

    return {
        "error": None,
        "time": str(last_row["time"]),
        "close": round(float(last_row["close"]), 2),
        "atr": round(float(last_row["atr"]), 2) if not pd.isna(last_row["atr"]) else None,
        "rsi": round(float(last_row["rsi"]), 1),
        "rsi2": round(float(last_row["rsi2"]), 1) if not pd.isna(last_row["rsi2"]) else None,
        "wma_fast": round(float(last_row["wma_fast"]), 2) if not pd.isna(last_row["wma_fast"]) else None,
        "wma_slow": round(float(last_row["wma_slow"]), 2) if not pd.isna(last_row["wma_slow"]) else None,
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
