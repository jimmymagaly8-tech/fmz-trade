'''backtest
start: 2024-01-01 00:00:00
end: 2024-02-01 00:00:00
period: 1m
basePeriod: 1m
exchanges: [{"eid":"Futures_Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

# Dual Thrust 突破策略 (合约)
# 经典CTA策略, 曾是全球最赚钱的策略之一
# 原理: 根据前N根K线的最高价/最低价/收盘价计算上下轨
#       价格突破上轨做多, 突破下轨做空
# 参数K1/K2不对称, 可以调节多空偏好

import json

# —— 策略参数 ——
N = 20              # 回溯K线数
K1 = 0.5            # 上轨系数 (越小越敏感)
K2 = 0.5            # 下轨系数
TRADE_RATIO = 0.4   # 每次使用资金比例
LEVERAGE = 5        # 杠杆倍数
TRAILING_STOP = 0.03  # 移动止盈 3%

# —— 计算 Dual Thrust 通道 ——
def calc_range(records, n):
    """计算前N根K线的Range"""
    if len(records) < n + 1:
        return None, None

    subset = records[-(n + 1):-1]  # 不包含当前K线
    hh = max(r["High"] for r in subset)    # 最高价的最高
    ll = min(r["Low"] for r in subset)     # 最低价的最低
    hc = max(r["Close"] for r in subset)   # 收盘价的最高
    lc = min(r["Close"] for r in subset)   # 收盘价的最低

    range_val = max(hh - lc, hc - ll)
    open_price = records[-1]["Open"]

    upper = open_price + K1 * range_val
    lower = open_price - K2 * range_val
    return upper, lower

# —— 交易逻辑 ——
exchange.SetContractType("swap")

position = 0       # 1=多, -1=空, 0=无
entry_price = 0
highest_since_entry = 0
lowest_since_entry = 999999999

while True:
    try:
        records = exchange.GetRecords()
        if not records or len(records) < N + 5:
            Sleep(1000)
            continue

        ticker = exchange.GetTicker()
        price = ticker["Last"]

        upper, lower = calc_range(records, N)
        if upper is None:
            Sleep(1000)
            continue

        account = exchange.GetAccount()
        equity = account["Balance"]

        # 移动止盈
        if position == 1:
            highest_since_entry = max(highest_since_entry, price)
            if price < highest_since_entry * (1 - TRAILING_STOP):
                exchange.SetDirection("closebuy")
                exchange.Sell(price * 0.99, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
                Log("移动止盈平多:", price, "最高:", round(highest_since_entry, 1),
                    "盈亏:", round(price - entry_price, 2))
                position = 0

        elif position == -1:
            lowest_since_entry = min(lowest_since_entry, price)
            if price > lowest_since_entry * (1 + TRAILING_STOP):
                exchange.SetDirection("closesell")
                exchange.Buy(price * 1.01, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
                Log("移动止盈平空:", price, "最低:", round(lowest_since_entry, 1),
                    "盈亏:", round(entry_price - price, 2))
                position = 0

        # 突破信号
        if position <= 0 and price > upper:
            # 先平空
            if position == -1:
                exchange.SetDirection("closesell")
                exchange.Buy(price * 1.01, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
                Log("平空反手:", price)

            amount = round(equity * LEVERAGE * TRADE_RATIO / price, 4)
            if amount > 0.001:
                exchange.SetDirection("buy")
                exchange.Buy(price * 1.01, amount)
                position = 1
                entry_price = price
                highest_since_entry = price
                Log("突破上轨开多:", price, "上轨:", round(upper, 1))

        elif position >= 0 and price < lower:
            # 先平多
            if position == 1:
                exchange.SetDirection("closebuy")
                exchange.Sell(price * 0.99, round(equity * LEVERAGE * TRADE_RATIO / entry_price, 4))
                Log("平多反手:", price)

            amount = round(equity * LEVERAGE * TRADE_RATIO / price, 4)
            if amount > 0.001:
                exchange.SetDirection("sell")
                exchange.Sell(price * 0.99, amount)
                position = -1
                entry_price = price
                lowest_since_entry = price
                Log("突破下轨开空:", price, "下轨:", round(lower, 1))

        Sleep(1000)
    except EOFError:
        break

Log("策略结束")
