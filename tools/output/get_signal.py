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