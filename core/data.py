"""
Data Module

Berisi:

- get_binance_klines()

Seluruh implementasi dipindahkan langsung dari engine_legacy.py.

JANGAN ubah algoritma.
"""

import json
import urllib.request
import urllib.error

SYMBOL = "BTCUSDT"

TF_ENTRY = "15m"
TF_BIAS_1 = "1h"
TF_BIAS_2 = "4h"

LIMIT = 300

__all__ = [
    "SYMBOL",
    "TF_ENTRY",
    "TF_BIAS_1",
    "TF_BIAS_2",
    "LIMIT",
    "get_binance_klines",
]


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
