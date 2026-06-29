"""
Fibonacci Module

Berisi:

- get_fibo_ote()

Seluruh implementasi dipindahkan langsung dari engine.py.

JANGAN ubah algoritma.
"""

__all__ = [
    "get_fibo_ote",
]


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
