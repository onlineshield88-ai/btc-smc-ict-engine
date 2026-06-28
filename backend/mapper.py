def normalize_signal(signal):
    if not signal:
        return "WAIT"

    s = signal.upper()

    if "BUY" in s:
        return "BUY"

    if "SELL" in s:
        return "SELL"

    return "WAIT"


def map_dashboard(result, engine):
    plan = result.get("plan") or {}

    return {
        "symbol": getattr(engine, "SYMBOL", "BTCUSDT"),
        "price": result.get("close"),
        "signal": normalize_signal(result.get("signal")),
        "score": result.get("score"),

        "entry": plan.get("entry"),
        "stop_loss": plan.get("stop_loss"),

        "tp1": plan.get("tp1"),
        "tp2": plan.get("tp2"),
        "tp3": plan.get("tp3"),

        "risk_reward": plan.get("risk_reward"),

        "market_bias": result.get("bias_1h"),

        "volatility": result.get("volatility_regime"),

        "confluence": result.get("reasons", [])
    }


def map_analysis(result):
    return {
        "atr": result.get("atr"),
        "rsi": result.get("rsi"),
        "rsi2": result.get("rsi2"),

        "wma9": result.get("wma_fast"),
        "wma119": result.get("wma_slow"),

        "volatility": result.get("volatility_regime"),

        "bias_h1": result.get("bias_1h"),
        "bias_h4": result.get("bias_4h"),

        # Placeholder sampai engine menyediakan data lebih rinci
        "trend": result.get("bias_4h"),
        "smc_structure": "-",
        "fibonacci": result.get("fibo_zone"),
        "order_block": "-",
        "liquidity_sweep": "-",
        "fair_value_gap": "-",
        "premium": "YES" if result.get("fibo_zone") == "premium" else "NO",
        "discount": "YES" if result.get("fibo_zone") == "discount" else "NO",
        "updated_at": result.get("time")
    }


def map_history(rows):

    history = []

    for i, row in enumerate(rows):

        dt = row.get("candle_time", "")

        if " " in dt:
            date, tm = dt.split(" ", 1)
        else:
            date = dt
            tm = ""

        signal = normalize_signal(row.get("signal"))

        entry = row.get("entry_price")

        sl = row.get("stop_loss")

        tp = row.get("take_profit")

        rr = "-"

        if entry and sl and tp:

            try:
                reward = abs(tp - entry)
                risk = abs(entry - sl)

                if risk > 0:
                    rr = f"{reward/risk:.2f}"
            except:
                pass

        history.append({

            "id": str(i + 1),

            "date": date,

            "time": tm,

            "signal": signal,

            "entry": entry,

            "stop_loss": sl,

            "tp1": tp,

            "tp2": None,

            "tp3": None,

            "risk_reward": rr,

            "score": row.get("score"),

            "bias": row.get("bias_1h"),

            "volatility": row.get("volatility_regime"),

            "status": row.get("status"),

            "pnl": "-",

            "result": "Open"

        })

    return history

