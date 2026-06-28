import urllib.request
import json
import traceback

try:
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=5"
    response = urllib.request.urlopen(url, timeout=10)
    data = json.loads(response.read())
    print("API OK - data:", len(data), "candles")
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
