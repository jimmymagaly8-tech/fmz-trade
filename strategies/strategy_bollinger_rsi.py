'''backtest
start: 2024-01-01 00:00:00
end: 2024-02-01 00:00:00
period: 1m
basePeriod: 1m
exchanges: [{"eid":"Futures_Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

# 布林带 + RSI 均值回归策略 (合约)
# 原理: 价格触及布林带下轨且RSI超卖时做多, 触及上轨且RSI超买时做空
# 适合震荡行情, 趋势行情需要止损保护

import json

# —— 策略参数 ——
BB_LENGTH = 20       # 布林带周期
BB_STD = 2.0         # 布林带标准差倍数
RSI_LENGTH = 14      # RSI 周期
RSI_OVERSOLD = 30    # RSI 超卖阈值
RSI_OVERBOUGHT = 70  # RSI 超买阈值
TRADE_RATIO = 0.3    # 每次使用资金比例
LEVERAGE = 5         # 杠杆倍数
STOP_LOSS_PCT = 0.02 # 止损比例 2%

# —— 技术指标计算 ——
def calc_sma(data, period):
    if len(data) < period:
        return None
    return sum(data[-period:]) / period

def calc_std(data, period):
    if len(data) < period:
        return None
    mean = sum(data[-period:]) / period
    variance = sum((x - mean) ** 2 for x in data[-period:]) / period
    return variance ** 0.5

def calc_rsi(closes, period):
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_bollinger(closes, length, std_mult):
    sma = calc_sma(closes, length)
    std = calc_std(closes, length)
    if sma is None or std is None:
        return None, None, None
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    return upper, sma, lower

# —— 交易逻辑 ——
exchange.SetContractType("swap")

position = 0       # 1=多, -1=空, 0=无
entry_price = 0
min_records = BB_LENGTH + 5

while True:
    try:
        records = exchange.GetRecords()
        if not records or len(records) < min_records:
            Sleep(1000)
            continue

        closes = [r["Close"] for r in records]
        price = closes[-1]

        upper, mid, lower = calc_bollinger(closes, BB_LENGTH, BB_STD)
        rsi = calc_rsi(closes, RSI_LENGTH)

        if upper is None or rsi is None:
            Sleep(1000)
            continue

        account = exchange.GetAccount()
        equity = account["Balance"]

        # 止损检查
        if position == 1 and price < entry_price * (1 - STOP_LOSS_PCT):
            exchange.SetDirection("closebuy")
            exchange.Sell(price * 0.99, abs(equity * LEVERAGE * TRADE_RATIO / entry_price))
            Log("止损平多:", price, "入场:", entry_price)
            position = 0

        elif position == -1 and price > entry_price * (1 + STOP_LOSS_PCT):
            exchange.SetDirection("closesell")
            exchange.Buy(price * 1.01, abs(equity * LEVERAGE * TRADE_RATIO / entry_price))
            Log("止损平空:", price, "入场:", entry_price)
            position = 0

        # 开仓信号
        if position == 0:
            if price <= lower and rsi < RSI_OVERSOLD:
                amount = round(equity * LEVERAGE * TRADE_RATIO / price, 4)
                if amount > 0.001:
                    exchange.SetDirection("buy")
                    exchange.Buy(price * 1.01, amount)
                    position = 1
                    entry_price = price
                    Log("开多:", price, "RSI:", round(rsi, 1), "下轨:", round(lower, 1))

            elif price >= upper and rsi > RSI_OVERBOUGHT:
                amount = round(equity * LEVERAGE * TRADE_RATIO / price, 4)
                if amount > 0.001:
                    exchange.SetDirection("sell")
                    exchange.Sell(price * 0.99, amount)
                    position = -1
                    entry_price = price
                    Log("开空:", price, "RSI:", round(rsi, 1), "上轨:", round(upper, 1))

        # 平仓信号: 回归中轨
        elif position == 1 and price >= mid:
            exchange.SetDirection("closebuy")
            exchange.Sell(price * 0.99, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
            Log("平多:", price, "中轨:", round(mid, 1), "盈亏:", round(price - entry_price, 2))
            position = 0

        elif position == -1 and price <= mid:
            exchange.SetDirection("closesell")
            exchange.Buy(price * 1.01, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
            Log("平空:", price, "中轨:", round(mid, 1), "盈亏:", round(entry_price - price, 2))
            position = 0

        Sleep(1000)
    except EOFError:
        break

Log("策略结束")
