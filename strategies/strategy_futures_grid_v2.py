'''backtest
start: 2024-06-01 00:00:00
end: 2024-09-01 00:00:00
period: 15m
basePeriod: 5m
exchanges: [{"eid":"Futures_Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

# 期货双向网格交易策略 v2 — 限价单模拟
#
# 核心改进 (对比 v1):
#   v1: 只比较相邻K线收盘价，用市价单成交 → 漏掉K线内穿越，成交价有偏差
#   v2: 用每根K线的 High/Low 检测穿越，在网格价精确成交 → 模拟真实限价挂单
#
# 逻辑 (模拟币安网格机器人):
#   每条网格线是一个"限价单位置"
#   价格从上往下穿越网格线 → 买入 (若有空仓则平空, 否则开多)
#   价格从下往上穿越网格线 → 卖出 (若有多仓则平多, 否则开空)
#   成交价 = 网格线价格 (限价单，不是市价单)

from fmz import *
import json

# ─── 参数 ───
GRID_LOWER = 50000
GRID_UPPER = 74000
GRID_SPACING = 2000
TRADE_AMOUNT = 0.004
LEVERAGE = 5


def main():
    task = VCtx(__doc__)

    exchange.SetContractType("swap")
    exchange.SetMarginLevel(LEVERAGE)

    grid_lines = list(range(GRID_LOWER, GRID_UPPER + 1, GRID_SPACING))
    # 每条线状态: None=空闲, "long"=持多仓, "short"=持空仓
    state = {p: None for p in grid_lines}
    trade_count = 0
    last_bar_time = 0

    Log("网格v2初始化:", GRID_LOWER, "~", GRID_UPPER,
        "间距:", GRID_SPACING, "线数:", len(grid_lines))

    while True:
        try:
            records = exchange.GetRecords()
            if not records or len(records) < 2:
                Sleep(1000)
                continue

            # 只在新K线完成时处理一次 (用倒数第2根，即最新已完成K线)
            bar = records[-2]
            bar_time = bar["Time"]
            if bar_time == last_bar_time:
                Sleep(1000)
                continue
            last_bar_time = bar_time

            high = bar["High"]
            low = bar["Low"]

            # 找出本根K线 High-Low 范围内穿越的所有网格线
            crossed = [gp for gp in grid_lines if low <= gp <= high]
            if not crossed:
                Sleep(1000)
                continue

            # 推断K线内价格路径方向:
            # Open 更靠近 High → 先涨后跌 → 先处理上穿(高→低排序)再处理下穿
            # Open 更靠近 Low  → 先跌后涨 → 先处理下穿(低→高排序)再处理上穿
            open_price = bar["Open"]
            close_price = bar["Close"]

            if abs(open_price - high) < abs(open_price - low):
                # 开盘靠近高点 → 先涨到High再跌到Low
                # 先处理上穿 (从低到高), 再处理下穿 (从高到低)
                up_lines = sorted([gp for gp in crossed if gp > open_price])
                down_lines = sorted([gp for gp in crossed if gp <= open_price], reverse=True)
                ordered = up_lines + down_lines
            else:
                # 开盘靠近低点 → 先跌到Low再涨到High
                # 先处理下穿 (从高到低), 再处理上穿 (从低到高)
                down_lines = sorted([gp for gp in crossed if gp < open_price], reverse=True)
                up_lines = sorted([gp for gp in crossed if gp >= open_price])
                ordered = down_lines + up_lines

            # 用一个简单的"虚拟价格指针"模拟路径
            virtual_price = open_price

            for gp in ordered:
                if gp < virtual_price:
                    # 价格下穿此网格线 → 买入方向
                    if state[gp] == "short":
                        exchange.SetDirection("closesell")
                        if exchange.Buy(gp, TRADE_AMOUNT):
                            state[gp] = None
                            trade_count += 1
                            Log("平空 @", gp)
                    elif state[gp] is None:
                        exchange.SetDirection("buy")
                        if exchange.Buy(gp, TRADE_AMOUNT):
                            state[gp] = "long"
                            trade_count += 1
                            Log("开多 @", gp)
                    virtual_price = gp

                elif gp > virtual_price:
                    # 价格上穿此网格线 → 卖出方向
                    if state[gp] == "long":
                        exchange.SetDirection("closebuy")
                        if exchange.Sell(gp, TRADE_AMOUNT):
                            state[gp] = None
                            trade_count += 1
                            Log("平多 @", gp)
                    elif state[gp] is None:
                        exchange.SetDirection("sell")
                        if exchange.Sell(gp, TRADE_AMOUNT):
                            state[gp] = "short"
                            trade_count += 1
                            Log("开空 @", gp)
                    virtual_price = gp

            Sleep(1000)
        except EOFError:
            break

    Log("策略结束, 总交易:", trade_count)

    # ─── 回测报告 ───
    raw = task.Join()
    result = json.loads(raw)

    print("\n" + "=" * 50)
    print("期货双向网格策略 v2 回测报告")
    print("=" * 50)
    print(f"回测区间: 2024-06-01 ~ 2024-09-01")
    print(f"网格: {GRID_LOWER}~{GRID_UPPER}, 间距 {GRID_SPACING}, "
          f"每格 {TRADE_AMOUNT} BTC")
    print(f"总交易次数: {trade_count}")

    snapshots = result.get("Snapshots", [])
    if snapshots:
        last = snapshots[-1][1][0]
        pnl = last["PnL"]
        print(f"最终PnL: {pnl:.2f} USDT")
        print(f"收益率: {pnl / 10000 * 100:.2f}%")

        peak = 0
        max_dd = 0
        for s in snapshots:
            p = s[1][0]["PnL"]
            if p > peak:
                peak = p
            dd = peak - p
            if dd > max_dd:
                max_dd = dd
        print(f"最大回撤: {max_dd:.2f} USDT")

    print("=" * 50)


if __name__ == "__main__":
    main()
