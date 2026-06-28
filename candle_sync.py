LAST_CANDLE = None


def is_new_candle(candle_time):

    global LAST_CANDLE

    if LAST_CANDLE is None:
        LAST_CANDLE = candle_time
        return True

    if candle_time != LAST_CANDLE:
        LAST_CANDLE = candle_time
        return True

    return False
