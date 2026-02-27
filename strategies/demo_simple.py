'''backtest
start: 2024-01-01 00:00:00
end: 2024-01-31 00:00:00
period: 1h
basePeriod: 15m
exchanges: [{"eid":"Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

from fmz import *
import json

def main():
    task = VCtx(__doc__)

    Log("=== 账户信息 ===")
    account = exchange.GetAccount()
    Log("Balance:", account["Balance"], "USDT, Stocks:", account["Stocks"], "BTC")

    Log("=== 行情数据 ===")
    ticker = exchange.GetTicker()
    Log("最新价:", ticker["Last"], "买一:", ticker["Buy"], "卖一:", ticker["Sell"])

    Log("=== K线数据 ===")
    records = exchange.GetRecords()
    if records and len(records) > 0:
        Log("K线数量:", len(records))
        last = records[-1]
        Log("最新K线 - 开:", last["Open"], "高:", last["High"],
            "低:", last["Low"], "收:", last["Close"], "量:", last["Volume"])

    # 获取回测结果 (不传 True 返回原始 JSON)
    raw = task.Join()
    result = json.loads(raw)

    print("\n=== 回测结果 ===")
    print("状态:", "完成" if result.get("Finished") else "未完成")
    print("进度:", result.get("Progress"), "%")
    print("日志条数:", result.get("LogsCount"))
    print("数据加载:", result.get("LoadElapsed", 0) / 1e6, "ms")
    print("回测耗时:", result.get("Elapsed", 0) / 1e6, "ms")

    # 打印快照摘要
    snapshots = result.get("Snapshots", [])
    if snapshots:
        first = snapshots[0][1][0]
        last_snap = snapshots[-1][1][0]
        print(f"\n初始资产: PnL={first['PnL']}")
        print(f"最终资产: PnL={last_snap['PnL']}")
        print(f"快照数量: {len(snapshots)}")

if __name__ == "__main__":
    main()
