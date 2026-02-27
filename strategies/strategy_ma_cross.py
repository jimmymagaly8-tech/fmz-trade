'''backtest
start: 2024-01-01 00:00:00
end: 2024-06-30 00:00:00
period: 1h
basePeriod: 1m
exchanges: [{"eid":"Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

# 双均线交叉策略
# 短期均线上穿长期均线 -> 买入
# 短期均线下穿长期均线 -> 卖出

from fmz import *
import json

SHORT_PERIOD = 7
LONG_PERIOD = 25
TRADE_RATIO = 0.95  # 每次用 95% 资金交易


def calc_ma(records, period):
    """计算简单移动平均线"""
    if len(records) < period:
        return None
    total = sum(r["Close"] for r in records[-period:])
    return total / period


def main():
    task = VCtx(__doc__)
    holding = False
    trade_count = 0

    while True:
        try:
            records = exchange.GetRecords()
            if not records or len(records) < LONG_PERIOD + 2:
                Sleep(1000)
                continue

            ma_short = calc_ma(records, SHORT_PERIOD)
            ma_long = calc_ma(records, LONG_PERIOD)

            # 前一根K线的均线
            prev_records = records[:-1]
            prev_ma_short = calc_ma(prev_records, SHORT_PERIOD)
            prev_ma_long = calc_ma(prev_records, LONG_PERIOD)

            if None in (ma_short, ma_long, prev_ma_short, prev_ma_long):
                Sleep(1000)
                continue

            ticker = exchange.GetTicker()
            price = ticker["Last"]

            # 金叉: 短均线从下方穿越长均线 -> 买入
            if prev_ma_short <= prev_ma_long and ma_short > ma_long and not holding:
                account = exchange.GetAccount()
                amount = (account["Balance"] * TRADE_RATIO) / price
                amount = round(amount, 4)
                if amount > 0.0001:
                    exchange.Buy(price, amount)
                    holding = True
                    trade_count += 1
                    Log("金叉买入:", price, "数量:", amount,
                        "MA7:", round(ma_short, 2), "MA25:", round(ma_long, 2))

            # 死叉: 短均线从上方穿越长均线 -> 卖出
            elif prev_ma_short >= prev_ma_long and ma_short < ma_long and holding:
                account = exchange.GetAccount()
                amount = account["Stocks"]
                if amount > 0.0001:
                    exchange.Sell(price, round(amount, 4))
                    holding = False
                    trade_count += 1
                    Log("死叉卖出:", price, "数量:", round(amount, 4),
                        "MA7:", round(ma_short, 2), "MA25:", round(ma_long, 2))

            Sleep(1000)
        except EOFError:
            break

    Log("策略结束, 总交易次数:", trade_count)

    raw = task.Join()
    result = json.loads(raw)

    print("\n" + "=" * 50)
    print("双均线交叉策略回测报告")
    print("=" * 50)
    print(f"回测区间: 2024-01-01 ~ 2024-06-30")
    print(f"交易对: BTC_USDT (Binance)")
    print(f"初始资金: 10000 USDT")
    print(f"总交易次数: {trade_count}")
    print(f"日志条数: {result.get('LogsCount')}")

    snapshots = result.get("Snapshots", [])
    if snapshots:
        last_snap = snapshots[-1][1][0]
        pnl = last_snap["PnL"]
        print(f"最终PnL: {pnl:.2f} USDT")
        print(f"收益率: {pnl / 100:.2f}%")
        print(f"快照数量: {len(snapshots)}")

        # 找最大回撤
        peak = 0
        max_dd = 0
        for snap in snapshots:
            p = snap[1][0]["PnL"]
            if p > peak:
                peak = p
            dd = peak - p
            if dd > max_dd:
                max_dd = dd
        print(f"最大回撤: {max_dd:.2f} USDT")


if __name__ == "__main__":
    main()
