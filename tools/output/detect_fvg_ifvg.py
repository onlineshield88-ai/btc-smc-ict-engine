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