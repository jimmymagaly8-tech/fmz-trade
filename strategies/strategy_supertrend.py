'''backtest
start: 2024-01-01 00:00:00
end: 2024-02-01 00:00:00
period: 1m
basePeriod: 1m
exchanges: [{"eid":"Futures_Binance","currency":"ETH_USDT","balance":10000,"stocks":0}]
'''

# SuperTrend + EMA 趋势跟踪策略 (合约)
# 原理: SuperTrend 判断趋势方向, EMA 确认趋势强度
#       趋势翻转时开仓, 反向翻转时平仓
# 适合趋势行情, 震荡行情会有回撤

import json

# —— 策略参数 ——
ATR_LENGTH = 10      # ATR 周期
ATR_MULT = 3.0       # SuperTrend ATR 倍数
EMA_FAST = 12        # 快速EMA
EMA_SLOW = 26        # 慢速EMA
TRADE_RATIO = 0.4    # 每次使用资金比例
LEVERAGE = 5         # 杠杆倍数
STOP_LOSS_PCT = 0.025  # 止损 2.5%

# —— 技术指标 ——
def calc_ema(data, period):
    if len(data) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for val in data[period:]:
        ema = (val - ema) * multiplier + ema
    return ema

def calc_atr(records, period):
    if len(records) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        high = records[i]["High"]
        low = records[i]["Low"]
        prev_close = records[i - 1]["Close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs) / period

class SuperTrend:
    def __init__(self, atr_length, multiplier):
        self.atr_length = atr_length
        self.multiplier = multiplier
        self.prev_upper = None
        self.prev_lower = None
        self.prev_trend = 1  # 1=上升, -1=下降
        self.value = None

    def update(self, records):
        atr = calc_atr(records, self.atr_length)
        if atr is None:
            return None

        hl2 = (records[-1]["High"] + records[-1]["Low"]) / 2
        upper = hl2 + self.multiplier * atr
        lower = hl2 - self.multiplier * atr
        close = records[-1]["Close"]
        prev_close = records[-2]["Close"]

        # Adjust bands
        if self.prev_lower is not None:
            if lower > self.prev_lower or prev_close < self.prev_lower:
                pass  # keep new lower
            else:
                lower = self.prev_lower

        if self.prev_upper is not None:
            if upper < self.prev_upper or prev_close > self.prev_upper:
                pass  # keep new upper
            else:
                upper = self.prev_upper

        # Determine trend
        if self.prev_trend == 1:
            trend = -1 if close < lower else 1
        else:
            trend = 1 if close > upper else -1

        self.value = lower if trend == 1 else upper
        self.prev_upper = upper
        self.prev_lower = lower
        self.prev_trend = trend

        return trend

# —— 交易逻辑 ——
exchange.SetContractType("swap")

st = SuperTrend(ATR_LENGTH, ATR_MULT)
prev_trend = 0
position = 0       # 1=多, -1=空, 0=无
entry_price = 0
min_records = max(ATR_LENGTH, EMA_SLOW) + 5

while True:
    try:
        records = exchange.GetRecords()
        if not records or len(records) < min_records:
            Sleep(1000)
            continue

        closes = [r["Close"] for r in records]
        price = closes[-1]

        trend = st.update(records)
        ema_fast = calc_ema(closes, EMA_FAST)
        ema_slow = calc_ema(closes, EMA_SLOW)

        if trend is None or ema_fast is None or ema_slow is None:
            Sleep(1000)
            continue

        ema_bullish = ema_fast > ema_slow
        account = exchange.GetAccount()
        equity = account["Balance"]

        # 止损
        if position == 1 and price < entry_price * (1 - STOP_LOSS_PCT):
            exchange.SetDirection("closebuy")
            exchange.Sell(price * 0.99, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
            Log("止损平多:", price)
            position = 0

        elif position == -1 and price > entry_price * (1 + STOP_LOSS_PCT):
            exchange.SetDirection("closesell")
            exchange.Buy(price * 1.01, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
            Log("止损平空:", price)
            position = 0

        # SuperTrend 翻转信号 + EMA 确认
        if prev_trend != 0 and trend != prev_trend:
            # 趋势从下降翻转为上升 + EMA看多
            if trend == 1 and ema_bullish:
                if position == -1:
                    exchange.SetDirection("closesell")
                    exchange.Buy(price * 1.01, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
                    Log("平空:", price)
                    position = 0

                if position == 0:
                    amount = round(equity * LEVERAGE * TRADE_RATIO / price, 4)
                    if amount > 0.001:
                        exchange.SetDirection("buy")
                        exchange.Buy(price * 1.01, amount)
                        position = 1
                        entry_price = price
                        Log("SuperTrend翻多, 开多:", price,
                            "EMA快:", round(ema_fast, 1), "EMA慢:", round(ema_slow, 1))

            # 趋势从上升翻转为下降 + EMA看空
            elif trend == -1 and not ema_bullish:
                if position == 1:
                    exchange.SetDirection("closebuy")
                    exchange.Sell(price * 0.99, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
                    Log("平多:", price)
                    position = 0

                if position == 0:
                    amount = round(equity * LEVERAGE * TRADE_RATIO / price, 4)
                    if amount > 0.001:
                        exchange.SetDirection("sell")
                        exchange.Sell(price * 0.99, amount)
                        position = -1
                        entry_price = price
                        Log("SuperTrend翻空, 开空:", price,
                            "EMA快:", round(ema_fast, 1), "EMA慢:", round(ema_slow, 1))

        # 趋势反转平仓 (不需要EMA确认)
        if position == 1 and trend == -1:
            exchange.SetDirection("closebuy")
            exchange.Sell(price * 0.99, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
            Log("趋势翻空, 平多:", price, "盈亏:", round(price - entry_price, 2))
            position = 0

        elif position == -1 and trend == 1:
            exchange.SetDirection("closesell")
            exchange.Buy(price * 1.01, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
            Log("趋势翻多, 平空:", price, "盈亏:", round(entry_price - price, 2))
            position = 0

        prev_trend = trend
        Sleep(1000)
    except EOFError:
        break

Log("策略结束")
