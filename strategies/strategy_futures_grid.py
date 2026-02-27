'''backtest
start: 2024-06-01 00:00:00
end: 2024-09-01 00:00:00
period: 15m
basePeriod: 5m
exchanges: [{"eid":"Futures_Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

# 期货双向网格交易策略
# 通用版: FMZ线上平台 / 本地Web UI / 命令行 均可直接运行

import json

# ─── 策略参数 ───
GRID_LOWER = 50000
GRID_UPPER = 74000
GRID_SPACING = 2000
TRADE_AMOUNT = 0.004
LEVERAGE = 5

# ─── 环境检测: FMZ平台 exchange 已存在, 本地需要初始化 ───
_LOCAL = False
_task = None
try:
    exchange
except NameError:
    _LOCAL = True
    import re, time as _time, datetime as _dt
    from fmz import *

    PERIOD_MAP = {
        "1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000,
        "30m": 1800000, "1h": 3600000, "2h": 7200000, "4h": 14400000,
        "6h": 21600000, "12h": 43200000, "1d": 86400000,
    }
    FEE_DEFAULTS = {
        "Binance": [150, 200], "OKX": [150, 200], "Huobi": [150, 200],
        "Futures_Binance": [300, 300], "Futures_OKX": [30, 30],
        "Futures_HuobiDM": [30, 30], "Futures_BitMEX": [8, 10],
        "Futures_CTP": [25, 25], "Futures_XTP": [30, 130],
    }

    def _build_task(doc):
        body = doc.split("backtest", 1)[1]
        cfg = {}
        for line in body.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            k, _, v = line.partition(":")
            cfg[k.strip()] = v.strip()

        ex = json.loads(cfg.get("exchanges", '[{"eid":"Binance","currency":"BTC_USDT"}]'))[0]
        eid = ex.get("eid", "Binance")
        arr = ex.get("currency", "BTC_USDT").upper().split("_")
        if len(arr) == 1:
            arr.append("CNY" if "CTP" in eid else "USD")

        period = PERIOD_MAP.get(cfg.get("period", "1h"), 3600000)
        bp = PERIOD_MAP.get(cfg.get("basePeriod", ""), 0)
        if not bp:
            bp = {86400000: 3600000, 3600000: 1800000, 1800000: 900000,
                  900000: 300000, 300000: 60000}.get(period, 3600000)

        fee_raw = ex.get("fee")
        # FMZ docstring fee format: decimal percentages (e.g., 0.03 = 0.03%)
        # parseTask converts: int(fee[0]*10000) → internal FeeDenominator=6 value
        fee = [int(fee_raw[0] * 10000), int(fee_raw[1] * 10000)] if fee_raw and len(fee_raw) == 2 else FEE_DEFAULTS.get(eid, [2000, 2000])

        start_ts = int(_time.mktime(_dt.datetime.strptime(cfg["start"], "%Y-%m-%d %H:%M:%S").timetuple()))
        end_ts = int(_time.mktime(_dt.datetime.strptime(cfg["end"], "%Y-%m-%d %H:%M:%S").timetuple()))

        tr = end_ts - start_ts
        sp = 86400 if tr / 86400 >= 30 else 3600 if tr / 86400 >= 2 else 300 if tr / 3600 > 2 else 60

        return {
            "Exchanges": [{
                "Balance": ex.get("balance", 10000), "Stocks": ex.get("stocks", 0),
                "BaseCurrency": arr[0], "QuoteCurrency": arr[1], "BasePeriod": bp,
                "FeeDenominator": 6, "FeeMaker": fee[0], "FeeTaker": fee[1],
                "FeeMin": 0, "Id": eid, "Label": eid,
            }],
            "Options": {
                "DataServer": "http://q.youquant.com" if "CTP" in eid else "http://q.fmz.com",
                "MaxChartLogs": 800, "MaxProfitLogs": 800, "MaxRuntimeLogs": 800,
                "NetDelay": 200, "Period": period,
                "RetFlags": 1 | 4 | 8 | 16 | 32 | 128 | 256,
                "TimeBegin": start_ts, "TimeEnd": end_ts,
                "UpdatePeriod": 5000, "SnapshotPeriod": sp * 1000,
                "Mode": int(cfg.get("mode", "0")),
            }
        }

    _g = {"__builtins__": __builtins__}
    _task = VCtx(task=_build_task(__doc__), gApis=_g)
    # 注入全局变量, 使下方策略代码与 FMZ 平台行为一致
    globals().update({k: v for k, v in _g.items() if k != "__builtins__"})

# ═══════════════════════════════════════════════════════
# 以下为策略逻辑, FMZ平台和本地完全相同
# ═══════════════════════════════════════════════════════

exchange.SetContractType("swap")
exchange.SetMarginLevel(LEVERAGE)

grid_lines = list(range(GRID_LOWER, GRID_UPPER + 1, GRID_SPACING))
state = {p: None for p in grid_lines}
trade_count = 0

Log("网格初始化:", GRID_LOWER, "~", GRID_UPPER,
    "间距:", GRID_SPACING, "线数:", len(grid_lines))

while True:
    try:
        records = exchange.GetRecords()
        if not records or len(records) < 2:
            Sleep(1000)
            continue

        ticker = exchange.GetTicker()
        cur = ticker["Last"]
        prev = records[-2]["Close"]

        for gp in grid_lines:
            if prev >= gp > cur:
                if state[gp] == "short":
                    exchange.SetDirection("closesell")
                    if exchange.Buy(cur, TRADE_AMOUNT):
                        state[gp] = None
                        trade_count += 1
                        Log("平空 @", gp, "价:", cur)
                elif state[gp] is None:
                    exchange.SetDirection("buy")
                    if exchange.Buy(cur, TRADE_AMOUNT):
                        state[gp] = "long"
                        trade_count += 1
                        Log("开多 @", gp, "价:", cur)

            elif prev <= gp < cur:
                if state[gp] == "long":
                    exchange.SetDirection("closebuy")
                    if exchange.Sell(cur, TRADE_AMOUNT):
                        state[gp] = None
                        trade_count += 1
                        Log("平多 @", gp, "价:", cur)
                elif state[gp] is None:
                    exchange.SetDirection("sell")
                    if exchange.Sell(cur, TRADE_AMOUNT):
                        state[gp] = "short"
                        trade_count += 1
                        Log("开空 @", gp, "价:", cur)

        Sleep(1000)
    except EOFError:
        break

Log("策略结束, 总交易:", trade_count)

# ═══════════════════════════════════════════════════════
# 本地回测报告 (FMZ平台自动忽略, 因为 _task 为 None)
# ═══════════════════════════════════════════════════════

if _LOCAL and _task:
    result = json.loads(_task.Join())
    snapshots = result.get("Snapshots", [])
    if snapshots:
        snap = snapshots[-1][1][0]
        assets = snap["Assets"][0]
        symbols = snap["Symbols"]["BTC_USDT.swap"]
        li = symbols.get("Long", {})
        si = symbols.get("Short", {})
        equity = (assets["Amount"] + assets["FrozenAmount"]
                  + li.get("Margin", 0) + si.get("Margin", 0)
                  + li.get("Profit", 0) + si.get("Profit", 0))
        peak = max_dd = 0
        for s in snapshots:
            p = s[1][0]["PnL"]
            if p > peak: peak = p
            dd = peak - p
            if dd > max_dd: max_dd = dd
        pnl = snap["PnL"]
        init = assets["Initial"]
        print(f"\n{'='*55}")
        print(f"初始资金: {init:.2f}  最终资产: {equity:.2f}  交易: {trade_count}")
        print(f"PnL: {pnl:+.2f} ({pnl/init*100:+.2f}%)  手续费: {assets['Commission']:.2f}")
        print(f"最大回撤: {max_dd:.2f} ({max_dd/init*100:.2f}%)")
        print(f"{'='*55}")
