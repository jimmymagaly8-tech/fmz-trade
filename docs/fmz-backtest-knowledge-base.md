# FMZ 回测系统知识库

> 本文档整理自FMZ官方文档、社区文章及源码分析，作为搭建本地回测平台的参考知识库。

---

## 目录

1. [回测系统概述](#1-回测系统概述)
2. [回测架构与原理](#2-回测架构与原理)
3. [回测配置格式](#3-回测配置格式)
4. [核心API参考](#4-核心api参考)
5. [本地Python回测引擎](#5-本地python回测引擎)
6. [自定义数据源](#6-自定义数据源)
7. [技术指标库(TA)](#7-技术指标库ta)
8. [期货交易API](#8-期货交易api)
9. [通用协议(自定义交易所)](#9-通用协议自定义交易所)
10. [回测结果数据结构](#10-回测结果数据结构)
11. [图表与可视化](#11-图表与可视化)
12. [策略参数系统](#12-策略参数系统)
13. [扩展API接口](#13-扩展api接口)
14. [最佳实践与注意事项](#14-最佳实践与注意事项)
15. [自建回测系统参考架构](#15-自建回测系统参考架构)

---

## 1. 回测系统概述

FMZ（发明者量化）提供两种回测方式：

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| **线上回测** | 在FMZ网站直接运行，JS在浏览器执行，Python在FMZ服务器 | 快速验证 |
| **本地回测** | 通过 `fmz` Python/JS包在本地运行 | 深度开发、自定义分析 |

### 支持的策略语言

- **JavaScript** — 浏览器端执行，支持Chrome DevTools调试
- **Python** — 服务端或本地执行，可结合pandas/talib
- **C++** — 高性能策略
- **MyLanguage (麦语言)** — 类通达信语法
- **PINE Script** — 兼容TradingView语法
- **Blockly** — 可视化拖拽编程

### 支持的交易所（回测）

**模拟级Tick**: Bitfinex, Binance, OKX, Huobi, OKX Futures, HuobiDM, BitMEX, Binance Futures, Deribit Options 等

**实盘级Tick**: Binance, OKX (Spot), HuobiDM（交易对有限）

**商品期货**: CTP（数据来自 `http://q.youquant.com`）

---

## 2. 回测架构与原理

### 2.1 时间线原则

回测沿时间轴从左向右推进，**在每个时间点只能访问该时间点之前的历史数据**。精度取决于时间点的分布密度。

### 2.2 两种回测模式

#### 模拟级Tick（Simulation Level）

- 基于K线数据模拟生成Tick，类似MT4的Tick生成机制
- 配置两个周期：**策略K线周期 (period)** 和 **底层K线周期 (basePeriod)**
- 每根底层K线生成约14个模拟Tick点
- 示例：1h策略周期 + 5m底层周期 → 每天约 `24 × 12 × 14 = 4,032` 个时间点
- 速度快，适合策略逻辑验证
- 配置: `mode: 0`（默认）

#### 实盘级Tick（Real Tick Level）

- 使用真实历史Tick数据，最小1秒间隔
- 精度高但速度慢，数据量大（Tick数据上限50MB）
- 支持交易所有限
- 包含特殊事件（如资金费率）
- 配置: `mode: 1`

### 2.3 撮合逻辑

- 买单价格 > Ask1（卖一价）→ 成交
- 卖单价格 < Bid1（买一价）→ 成交
- 简单阈值撮合，**不支持部分成交模拟**
- 回测中订单簿深度：**第一档为真实数据，其余档位为模拟数据**

### 2.4 回测不支持的功能

- 无逐笔成交历史
- 无订单簿深度变化模拟
- 无真实网络延迟（但可模拟延迟）
- 不支持期货回测中途切换交易对
- `GetTrades()` 在回测中返回空
- `Info` 字段在回测中不可用
- `HttpQuery` 在回测中返回 `'dummy'`
- `DBExec` 在回测中不支持
- `GetMeta()` 在回测中返回 `None`

### 2.5 底层引擎架构

```
Python Wrapper (fmz.py)
    ├── 解析 docstring 配置 (parseTask)
    ├── 下载/加载 预编译 .so (C/C++ 引擎)
    │   └── 从 {DATASERVER}/dist/depends/ 下载，MD5校验
    ├── 通过 ctypes 调用 .so 的 C API
    ├── httpGetCallback: 数据获取回调（带本地缓存）
    ├── 向调用者 globals() 注入 API
    │   └── exchange, exchanges, Log, Sleep, TA, Chart 等
    └── task.Join() 返回回测结果
```

**数据流**:
```
q.fmz.com (Data Server) → HTTP GET → Local Cache (tempdir/cache/) → .so Engine → Python API
```

---

## 3. 回测配置格式

### 3.1 Python docstring 格式

```python
'''backtest
start: 2024-01-01 00:00:00
end: 2024-06-30 00:00:00
period: 1h
basePeriod: 15m
mode: 0
exchanges: [{"eid":"Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''
```

### 3.2 JavaScript 注释格式

```javascript
/*backtest
start: 2024-01-01 00:00:00
end: 2024-06-30 00:00:00
period: 1h
basePeriod: 15m
exchanges: [{"eid":"Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
*/
```

### 3.3 PINE Script 注释格式

```pine
/*backtest
start: 2022-06-03 09:00:00
end: 2022-06-08 15:00:00
period: 1m
basePeriod: 1m
exchanges: [{"eid":"Bitfinex","currency":"BTC_USD"}]
*/
```

### 3.4 配置参数说明

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `start` | 回测开始时间 (UTC) | `2024-01-01 00:00:00` |
| `end` | 回测结束时间 (UTC) | `2024-06-30 00:00:00` |
| `period` | 策略K线周期 | `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M` |
| `basePeriod` | 底层数据周期 (模拟Tick精度) | `1m`, `5m`, `15m` 等 |
| `mode` | 回测模式 | `0` = 模拟级Tick, `1` = 实盘级Tick |
| `exchanges` | 交易所配置数组 (JSON) | 见下方 |

### 3.5 exchanges 配置字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `eid` | 交易所ID | `"Binance"`, `"OKX"`, `"Bitfinex"`, `"Futures_Binance"`, `"Futures_OKX"`, `"Futures_CTP"` |
| `currency` | 交易对 | `"BTC_USDT"`, `"ETH_BTC"`, `"BTC_USD"` |
| `balance` | 初始法币余额 | `10000` |
| `stocks` | 初始币种数量 | `0`, `1`, `3` |

### 3.6 自动 basePeriod 选择逻辑

当未指定 basePeriod 时，引擎自动选择：

```
period = 1d   → basePeriod = 1h
period = 1h   → basePeriod = 30m
period = 30m  → basePeriod = 15m
period = 15m  → basePeriod = 5m
period = 5m   → basePeriod = 1m
```

### 3.7 快照周期自动选择

```
回测范围 <= 2小时   → 每60秒快照
回测范围 <= 2天     → 每300秒快照
回测范围 < 30天     → 每3600秒快照
回测范围 >= 30天    → 每86400秒快照
```

### 3.8 默认手续费设置

| 交易所 | Maker (万分之) | Taker (万分之) |
|--------|---------------|---------------|
| Binance | 15 | 20 |
| OKX | 15 | 20 |
| Huobi | 15 | 20 |
| Futures_BitMEX | 0.8 | 1.0 |
| Futures_OKX | 3.0 | 3.0 |
| Futures_HuobiDM | 3.0 | 3.0 |
| Futures_CTP | 2.5 | 2.5 |

> 费率计算: `实际费率 = fee_value / 10^6`

---

## 4. 核心API参考

### 4.1 行情数据

#### exchange.GetTicker(symbol?)

获取最新行情数据。

**返回值**:
```python
{
    "Time": 1518969600000,   # 毫秒时间戳
    "Symbol": "BTC_USDT",
    "Open": 8000.0,          # 开盘价
    "High": 8100.0,          # 最高价
    "Low": 7900.0,           # 最低价
    "Sell": 8050.0,          # 卖一价 (Ask)
    "Buy": 8040.0,           # 买一价 (Bid)
    "Last": 8045.0,          # 最新价
    "Volume": 1234567.89,    # 成交量
    "OpenInterest": 0.0      # 持仓量
}
```

> **注意**: 回测中 `High`/`Low` 是从买一/卖一模拟的，非真实24h最高最低。

#### exchange.GetDepth(symbol?)

获取订单簿深度。

**返回值**:
```python
{
    "Asks": [{"Price": 8050.0, "Amount": 1.5}, ...],  # 卖单(价格从低到高)
    "Bids": [{"Price": 8040.0, "Amount": 2.0}, ...],  # 买单(价格从高到低)
    "Time": 1518969600000
}
```

> **回测注意**: 第一档为真实数据，其余档位为模拟数据。

#### exchange.GetRecords(symbol?, period?, limit?)

获取K线数据。

**参数**:
- `period`: 周期常量或秒数 — `PERIOD_M1`, `PERIOD_M5`, `PERIOD_M15`, `PERIOD_M30`, `PERIOD_H1`, `PERIOD_D1`
- `limit`: 返回数量限制

**返回值** (`MyList` — 可通过属性名批量取值):
```python
[
    {"Time": 1526616000000, "Open": 7995, "High": 8067.65, "Low": 7986.6, "Close": 8027.22, "Volume": 9444676.27},
    {"Time": 1526619600000, "Open": 8019.03, "High": 8049.99, "Low": 7982.78, "Close": 8027, "Volume": 5354251.81}
]
```

**MyList 特殊属性** (需 numpy):
```python
records = exchange.GetRecords()
records.Close  # 返回所有收盘价的 numpy 数组
records.High   # 返回所有最高价的 numpy 数组
records.Open   # 返回所有开盘价的 numpy 数组
```

> **回测注意**: 回测开始前会预加载约5000根K线作为历史数据。最后一根K线在形成过程中会持续更新。

#### exchange.GetTrades(symbol?)

获取逐笔成交记录。**回测中返回空数组。**

#### exchange.GetTickers()

获取所有交易对的Ticker数据。

#### exchange.GetMarkets()

获取市场信息JSON。

#### exchange.GetFundings(symbol?)

获取资金费率数据。

### 4.2 账户信息

#### exchange.GetAccount()

**返回值**:
```python
{
    "Balance": 10000.0,        # 可用法币
    "FrozenBalance": 0.0,      # 冻结法币
    "Stocks": 0.0,             # 可用币种数量
    "FrozenStocks": 0.0,       # 冻结币种数量
    "Equity": 10000.0,         # 权益
    "UPnL": 0.0                # 未实现盈亏
}
```

#### exchange.GetAssets()

获取所有资产信息数组。

### 4.3 交易操作

#### exchange.Buy(price, amount, *extra)

**参数**:
- `price`: 价格。`-1` 表示**市价单**
- `amount`:
  - 限价单: 数量
  - 市价买入: **法币金额**（非数量）
  - 期货市价: **合约数量**（必须为整数）

**返回**: 订单ID (成功) 或 `None` (失败)

#### exchange.Sell(price, amount, *extra)

与 `Buy` 类似，市价卖出时 `amount` 为币种数量。

#### exchange.CreateOrder(symbol, side, price, amount, *extra)

统一下单接口:
- `symbol`: `"BTC_USDT"` (现货), `"BTC_USDT.swap"` (永续合约)
- `side`: `"buy"`, `"sell"`, `"closebuy"`, `"closesell"`

#### exchange.CancelOrder(orderId, *extra)

取消订单，返回布尔值。

#### exchange.GetOrder(orderId)

获取单个订单详情:
```python
{
    "Id": 12345,
    "Price": 8000.0,
    "Amount": 1.0,
    "DealAmount": 0.5,          # 已成交量
    "AvgPrice": 8001.0,         # 成交均价
    "Type": 0,                   # 0=买, 1=卖
    "Offset": 0,                 # 0=开仓, 1=平仓
    "Status": 0,                 # 0=挂单中, 1=已成交, 2=已取消
    "Symbol": "BTC_USDT",
    "ContractType": ""
}
```

#### exchange.GetOrders(symbol?)

获取所有**未成交**挂单数组。

#### exchange.GetHistoryOrders(symbol?, since?, limit?)

获取历史已成交/已取消订单。

### 4.4 条件单

```python
exchange.CreateConditionOrder(symbol, side, amount, condition, *extra)
exchange.ModifyConditionOrder(orderId, side, amount, condition, *extra)
exchange.GetConditionOrders(symbol?)
exchange.GetHistoryConditionOrders(symbol?, since?, limit?)
exchange.GetConditionOrder(orderId)
exchange.CancelConditionOrder(orderId, *extra)
```

### 4.5 配置函数

| 函数 | 功能 |
|------|------|
| `exchange.SetPrecision(pricePrecision, amountPrecision)` | 设置价格和数量精度 |
| `exchange.SetCurrency(pair)` | 切换交易对，如 `"ETH_USDT"` |
| `exchange.SetRate(rate)` / `exchange.GetRate()` | 设置/获取汇率 |
| `exchange.SetMaxBarLen(n)` | 设置最大K线数量（默认1000） |
| `exchange.SetBase(url)` / `exchange.GetBase()` | 切换API基础URL |
| `exchange.SetProxy(addr)` | 设置代理（支持socks5） |
| `exchange.SetData(name, data)` | 注入自定义数据 |
| `exchange.GetData(name, timeout?, offset?)` | 获取自定义数据 |
| `exchange.IO(key, value)` | 多功能配置 |
| `exchange.Go(method, *args)` | 异步调用（返回 AsyncRet） |
| `exchange.GetRawJSON()` | 获取上次API调用的原始JSON |

### 4.6 全局工具函数

| 函数 | 功能 |
|------|------|
| `Log(msg, *args)` | 日志输出。末尾加 `"@"` 触发微信推送 |
| `LogStatus(msg)` | 更新状态栏（不写入日志） |
| `LogProfit(value)` | 记录收益点，绘制权益曲线 |
| `LogReset(keep?)` | 清除日志，可选保留最近n条 |
| `LogProfitReset(keep?)` | 清除收益日志 |
| `LogError(*args)` | 错误日志 |
| `Panic(*args)` | 致命错误 + 停止 |
| `Sleep(ms)` | 暂停执行（回测中推进模拟时间） |
| `Chart(config)` | 创建HighCharts图表 |
| `KLineChart(config)` | 创建K线图表 |
| `HttpQuery(url)` | HTTP GET请求（回测中返回 `'dummy'`） |
| `GetMeta()` | 获取元信息（回测中返回 `None`） |
| `SetErrorFilter(s)` | 设置错误过滤（回测中无效） |
| `EnableLog(flag)` | 开关日志 |
| `Unix()` | 返回模拟Unix时间戳（秒） |
| `UnixNano()` | 返回模拟纳秒时间戳 |
| `GetCommand()` | 获取交互命令 |
| `_N(value, precision)` | 数值格式化 — `_N(9.12345, 2)` → `9.12` |
| `_D(timestamp?, fmt?)` | 时间格式化 |
| `_G(key, value?)` | 持久化键值存储（key必须为字符串） |
| `_C(func, *args)` | 容错包装器，失败自动重试 |
| `_Cross(arr1, arr2)` | 交叉检测 |

### 4.7 策略生命周期函数

```python
def init():
    """策略初始化，main()之前调用（可选）"""
    pass

def main():
    """策略入口（必须），包含核心交易逻辑"""
    while True:
        ticker = exchange.GetTicker()
        # 交易逻辑...
        Sleep(1000)

def onexit():
    """正常退出时调用，最长5分钟（可选）"""
    pass

# JavaScript 还支持:
# function onerror() { /* 异常处理 */ }
```

### 4.8 订单状态常量

```python
ORDER_STATE_PENDING   = 0   # 挂单中
ORDER_STATE_CLOSED    = 1   # 已成交
ORDER_STATE_CANCELED  = 2   # 已取消
ORDER_STATE_UNKNOWN   = 3   # 未知

ORDER_TYPE_BUY  = 0  # 买单
ORDER_TYPE_SELL = 1  # 卖单

ORDER_OFFSET_OPEN  = 0  # 开仓
ORDER_OFFSET_CLOSE = 1  # 平仓

PD_LONG  = 0  # 多仓
PD_SHORT = 1  # 空仓
```

---

## 5. 本地Python回测引擎

### 5.1 安装

```bash
pip install https://github.com/fmzquant/backtest_python/archive/master.zip
```

> **重要**: 仅支持 Python 3.10。Python 3.13/3.14 会导致预编译 .so 段错误。

### 5.2 引擎架构

```
fmz.py (Python Wrapper)
  │
  ├── parseTask(__doc__) → 解析docstring配置
  │
  ├── 下载 .so 引擎
  │   ├── 文件名: backtest_py_{os}_{arch}.so
  │   │   (如 backtest_py_darwin_64bit.so)
  │   ├── 优先检查: ./depends/{soName} (本地调试)
  │   ├── 其次检查: {tempdir}/cache/{soName} (缓存)
  │   └── 最后下载: {DATASERVER}/dist/depends/{soName} + MD5校验
  │
  ├── ctypes.CDLL() 加载 .so
  │
  ├── lib.api_backtest(task_json, httpGetCb, progressCb, None) → ctx
  │
  ├── 创建 Exchange 对象
  │
  └── 注入 API 到 caller globals()
      exchange, exchanges, Log, Sleep, TA, Chart, ...
```

### 5.3 数据获取流程

```
DATASERVER (默认 http://q.fmz.com)
    │
    ├── K线数据 URL → MD5 Hash → 缓存文件名
    │   └── {tempdir}/cache/botvs_kline_{md5hash}
    │
    ├── 首次访问: HTTP GET下载 → 写入缓存
    └── 后续访问: 直接从缓存读取
```

环境变量覆盖: `DATASERVER=http://your-server.com`

### 5.4 基本使用模式

```python
'''backtest
start: 2024-01-01 00:00:00
end: 2024-06-30 00:00:00
period: 1h
basePeriod: 15m
exchanges: [{"eid":"Binance","currency":"BTC_USDT","balance":10000,"stocks":0}]
'''

from fmz import *

task = VCtx(__doc__)  # 初始化回测引擎

def main():
    while True:
        ticker = exchange.GetTicker()
        records = exchange.GetRecords()
        account = exchange.GetAccount()

        # 策略逻辑
        if some_condition:
            exchange.Buy(ticker.Last, 0.1)

        Sleep(1000)  # 推进回测时间

# 回测结束时引擎抛出 EOFError
try:
    main()
except EOFError:
    result = task.Join()   # 获取回测结果 (JSON)
    print(result)
```

### 5.5 VCtx 初始化参数

```python
class VCtx(object):
    def __init__(self, task=None, autoRun=False, gApis=None, progressCallback=None):
        # task: docstring字符串 或 dict配置
        # autoRun: 自动运行模式
        # gApis: 自定义全局API注入目标
        # progressCallback: 进度回调
```

### 5.6 task 对象方法

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `task.Join()` | JSON字符串 | 原始回测结果 |
| `task.Join(True)` | pandas DataFrame | 含 close, balance, stocks, net 列 |
| `task.Show()` | matplotlib图表 | **可能在无头环境崩溃** |

### 5.7 get_bars 辅助函数

```python
from fmz import get_bars

kline = get_bars('BTC_USD_BITFINEX', '1h', start='2019-05-01', end='2019-10-01')
# 返回 pandas DataFrame: open, high, low, close, volume
```

### 5.8 ctypes C API 列表

引擎通过 ctypes 调用以下 C 函数:

```
# 核心
lib.api_backtest(task_json, httpGetCb, progressCb, None) → ctx
lib.api_Join(ctx) → char_p (JSON结果)
lib.api_Release(ctx)
lib.api_free(ptr)

# 日志
lib.api_Log(ctx, args)
lib.api_LogReset(ctx, keep)
lib.api_LogStatus(ctx, args)
lib.api_LogProfit(ctx, profit, args)
lib.api_LogProfitReset(ctx, keep)
lib.api_LogError(ctx, args)

# 时间与控制
lib.api_Sleep(ctx, ms) → int (0=ok, 非零=EOF)
lib.api_Unix(ctx) → ulonglong
lib.api_EnableLog(ctx, flag)

# 图表
lib.api_Chart_New(ctx, json)
lib.api_Chart_Add(ctx, json)
lib.api_Chart_Reset(ctx, keep)

# 行情
lib.api_Exchange_GetTicker(ctx, idx, symbol, ticker_ptr) → int
lib.api_Exchange_GetRecords(ctx, idx, symbol, period, limit, len_ptr, buf_ptr) → int
lib.api_Exchange_GetDepth(ctx, idx, symbol, ask_len, bid_len, buf_ptr) → int
lib.api_Exchange_GetTrades(ctx, idx, symbol, len_ptr, buf_ptr) → int
lib.api_Exchange_GetTickers(ctx, idx, len_ptr, buf_ptr) → int
lib.api_Exchange_GetMarkets(ctx, idx, char_p_ptr)
lib.api_Exchange_GetFundings(ctx, idx, symbol, len_ptr, buf_ptr) → int

# 账户
lib.api_Exchange_GetAccount(ctx, idx, account_ptr) → int
lib.api_Exchange_GetAssets(ctx, idx, len_ptr, buf_ptr) → int

# 交易
lib.api_Exchange_Trade(ctx, idx, side, price, amount, extra) → int
lib.api_Exchange_CreateOrder(ctx, idx, symbol, side, price, amount, extra) → int
lib.api_Exchange_CancelOrder(ctx, idx, order_id, extra) → int
lib.api_Exchange_GetOrder(ctx, idx, order_id, order_ptr) → int
lib.api_Exchange_GetOrders(ctx, idx, symbol, len_ptr, buf_ptr) → int
lib.api_Exchange_GetHistoryOrders(ctx, idx, symbol, since, limit, len_ptr, buf_ptr) → int

# 期货
lib.api_Exchange_SetContractType(ctx, idx, symbol, detail_ptr) → int
lib.api_Exchange_SetDirection(ctx, idx, direction) → bool
lib.api_Exchange_SetMarginLevel(ctx, idx, symbol, level) → bool
lib.api_Exchange_GetPositions(ctx, idx, symbol, len_ptr, buf_ptr) → int

# 配置
lib.api_Exchange_SetPrecision(ctx, idx, price_prec, amount_prec)
lib.api_Exchange_SetCurrency(ctx, idx, currency)
lib.api_Exchange_SetRate(ctx, idx, rate) → double
lib.api_Exchange_GetRate(ctx, idx) → double
lib.api_Exchange_IO(ctx, idx, key, value) → int
lib.api_Exchange_Log(ctx, idx, orderType, price, amount, extra) → int
lib.api_Exchange_SetData(ctx, idx, name, data) → int
lib.api_Exchange_GetData(ctx, idx, ticker_ptr, name, timeout, offset) → int
lib.api_Exchange_SetBase(ctx, idx, url, char_p_ptr)
lib.api_Exchange_GetBase(ctx, idx, char_p_ptr)
```

### 5.9 ctypes 数据结构

```python
# Ticker结构
class _TICKER(Structure):
    _fields_ = [
        ("Time", c_ulonglong), ("Symbol", c_char*31),
        ("Open", c_double), ("High", c_double), ("Low", c_double),
        ("Sell", c_double), ("Buy", c_double), ("Last", c_double),
        ("Volume", c_double), ("OpenInterest", c_double), ("Info", _INFO)
    ]

# K线结构
class _RECORD(Structure):
    _fields_ = [
        ("Time", c_ulonglong),
        ("Open", c_double), ("High", c_double), ("Low", c_double),
        ("Close", c_double), ("Volume", c_double), ("OpenInterest", c_double)
    ]

# 账户结构
class _ACCOUNT(Structure):
    _fields_ = [
        ("Balance", c_double), ("FrozenBalance", c_double),
        ("Stocks", c_double), ("FrozenStocks", c_double),
        ("Equity", c_double), ("UPnL", c_double)
    ]

# 订单结构
class _ORDER(Structure):
    _fields_ = [
        ("Id", c_ulonglong), ("Time", c_ulonglong),
        ("Price", c_double), ("Amount", c_double),
        ("DealAmount", c_double), ("AvgPrice", c_double),
        ("Type", c_uint), ("Offset", c_uint), ("Status", c_uint),
        ("Symbol", c_char*31), ("ContractType", c_char*31),
        ("Condition", _ORDER_CONDITION)
    ]

# 持仓结构
class _POSITION(Structure):
    _fields_ = [
        ("MarginLevel", c_double), ("Amount", c_double),
        ("FrozenAmount", c_double), ("Price", c_double),
        ("Profit", c_double), ("Margin", c_double),
        ("Type", c_uint), ("Symbol", c_char*31), ("ContractType", c_char*31)
    ]
```

### 5.10 结果控制位标志

```python
BT_Status          = 1 << 0   # 1
BT_Symbols         = 1 << 1   # 2
BT_Indicators      = 1 << 2   # 4
BT_Chart           = 1 << 3   # 8
BT_ProfitLogs      = 1 << 4   # 16
BT_RuntimeLogs     = 1 << 5   # 32
BT_CloseProfitLogs = 1 << 6   # 64
BT_Accounts        = 1 << 7   # 128
BT_Accounts_PnL    = 1 << 8   # 256
```

---

## 6. 自定义数据源

### 6.1 K线数据格式

每条K线为数组，6个字段:
```python
[
    1530460800,    # Unix时间戳 (秒)
    2841.5795,     # Open (开盘价)
    2845.6801,     # High (最高价)
    2756.815,      # Low (最低价)
    2775.557,      # Close (收盘价)
    137035034      # Volume (成交量)
]
```

### 6.2 使用 SetData 导入自定义K线

```javascript
function init() {
    var arr = [
        [1530460800, 2841.5795, 2845.6801, 2756.815, 2775.557, 137035034],
        [1530547200, 2775.557, 2798.123, 2750.000, 2790.456, 145678901],
        [1542556800, 2681.8988, 2703.5116, 2674.1781, 2703.5116, 231662827]
    ]
    exchange.SetData(arr)
    Log("Import data successfully")
}
```

> **关键要求**: 自定义K线数据的周期必须与 `basePeriod` 一致。

### 6.3 自定义键值数据

```javascript
// 注入数据
exchange.SetData("myKey", [
    [1579536000000, "abc"],       // [毫秒时间戳, 任意值]
    [1579622400000, 123],
    [1579708800000, {"price": 123}]
])

// 读取数据 (返回当前时间点对应的值)
var data = exchange.GetData("myKey")
// data = {"Time": 1579536000000, "Data": "abc"}
```

### 6.4 DATASERVER 环境变量

可通过设置 `DATASERVER` 环境变量指向自定义数据服务器:

```bash
export DATASERVER=http://localhost:8080
```

数据服务器需要实现与 `q.fmz.com` 相同的HTTP接口和数据格式。

---

## 7. 技术指标库(TA)

### 7.1 内置指标（无需外部依赖）

| 函数 | 说明 | 默认参数 | 返回值 |
|------|------|----------|--------|
| `TA.MA(records, period=9)` | 简单移动平均 | period=9 | 数组 |
| `TA.SMA(records, period=9)` | 同MA | period=9 | 数组 |
| `TA.EMA(records, period=9)` | 指数移动平均 | period=9 | 数组 |
| `TA.MACD(records, fast=12, slow=26, signal=9)` | MACD | 12,26,9 | [DIF, DEA, Histogram] |
| `TA.BOLL(records, period=20, multiplier=2)` | 布林带 | 20, 2 | [Upper, Middle, Lower] |
| `TA.KDJ(records, n=9, k=3, d=3)` | KDJ随机指标 | 9,3,3 | [K, D, J] |
| `TA.RSI(records, period=14)` | 相对强弱指数 | 14 | 数组 |
| `TA.ATR(records, period=14)` | 平均真实波幅 | 14 | 数组 |
| `TA.OBV(records)` | 能量潮 | - | 数组 |
| `TA.CMF(records, period=20)` | 蔡金资金流 | 20 | 数组 |
| `TA.Alligator(records, jaw=13, teeth=8, lips=5)` | 鳄鱼线 | 13,8,5 | [Jaw, Teeth, Lips] |
| `TA.Highest(records, n, attr)` | N周期最高 | - | 数值 |
| `TA.Lowest(records, n, attr)` | N周期最低 | - | 数值 |

### 7.2 内部实现算法

```python
# EMA乘数
multiplier = 2.0 / (period + 1)

# SMA: 简单算术平均
# EMA: 指数加权 (当前值 * multiplier + 上次EMA * (1 - multiplier))
# SMMA: 平滑移动平均 (Alligator使用)
```

### 7.3 配合 talib 使用

```python
import talib

records = exchange.GetRecords()
close = records.Close  # numpy数组

ma5  = talib.MA(close, 5)
ma20 = talib.MA(close, 20)
rsi  = talib.RSI(close, 14)
macd, signal, hist = talib.MACD(close, 12, 26, 9)
```

---

## 8. 期货交易API

### 8.1 合约类型设置

```python
# 数字货币期货
exchange.SetContractType("swap")        # 永续合约
exchange.SetContractType("this_week")    # 当周
exchange.SetContractType("next_week")    # 次周
exchange.SetContractType("quarter")      # 季度
exchange.SetContractType("next_quarter") # 次季度
exchange.SetContractType("third_quarter")# 三季度
exchange.SetContractType("XBTUSD")       # BitMEX永续

# 商品期货 (CTP)
exchange.SetContractType("rb1905")       # 螺纹钢
exchange.SetContractType("MA909")        # 甲醇
exchange.SetContractType("MA000")        # 指数合约
exchange.SetContractType("MA888")        # 主力连续
```

### 8.2 交易方向设置

```python
exchange.SetDirection("buy")              # 买入开多
exchange.SetDirection("sell")             # 卖出开空
exchange.SetDirection("closebuy")         # 平多仓
exchange.SetDirection("closesell")        # 平空仓
exchange.SetDirection("closebuy_today")   # 平今多仓 (CTP)
exchange.SetDirection("closesell_today")  # 平今空仓 (CTP)
```

### 8.3 期货交易完整示例

```python
# 开多
exchange.SetContractType("swap")
exchange.SetDirection("buy")
exchange.Buy(8000, 1)  # 限价8000，1张合约

# 开空
exchange.SetDirection("sell")
exchange.Sell(8000, 1)

# 平多
exchange.SetDirection("closebuy")
exchange.Sell(8100, 1)

# 平空
exchange.SetDirection("closesell")
exchange.Buy(7900, 1)
```

### 8.4 杠杆与持仓

```python
exchange.SetMarginLevel(10)  # 设置10倍杠杆

positions = exchange.GetPositions()
# [{"Amount": 1, "FrozenAmount": 0, "Price": 8000,
#   "Profit": 100, "Type": 0, "Margin": 800,
#   "MarginLevel": 10, "ContractType": "swap"}]

# Type: 0=多仓(PD_LONG), 1=空仓(PD_SHORT)
```

---

## 9. 通用协议(自定义交易所)

FMZ支持通过HTTP协议对接任意交易所，充当中间件。

### 9.1 插件架构

```
FMZ策略 → FMZ托管者 → HTTP请求 → 通用协议插件(localhost:6666) → 目标交易所
```

### 9.2 请求格式

```json
{
    "access_key": "用户AccessKey",
    "secret_key": "用户SecretKey",
    "nonce": 1234567890123,
    "method": "操作方法名",
    "params": {"key": "value"}
}
```

### 9.3 响应格式

```json
// 成功
{"data": { /* 操作结果 */ }}

// 失败
{"error": "错误信息"}
```

### 9.4 方法映射

| FMZ API | 协议Method | 响应data字段 |
|---------|-----------|-------------|
| `GetTicker` | `ticker` | `{time, buy, sell, last, high, low, vol}` |
| `GetDepth` | `depth` | `{time, asks[], bids[]}` |
| `GetTrades` | `trades` | `[{id, time, price, amount, type}]` |
| `GetRecords` | `records` | `[[timestamp, open, high, low, close, volume]]` |
| `GetAccount` | `accounts` | `[{currency, free, frozen}]` |
| `Buy/Sell` | `trade` | `{id}` |
| `GetOrder` | `order` | `{id, amount, price, status, deal_amount, type, avg_price}` |
| `GetOrders` | `orders` | 订单数组 |
| `CancelOrder` | `cancel` | `{data: true/false}` |

### 9.5 订单状态值

- `"open"` — 挂单中
- `"closed"` — 已成交
- `"cancelled"` — 已取消

### 9.6 期货扩展 (IO方法)

```json
{"method": "io", "code": 0, "args": [10]}         // SetMarginLevel(10)
{"method": "io", "code": 1, "args": ["buy"]}      // SetDirection("buy")
{"method": "io", "code": 2, "args": ["swap"]}     // SetContractType("swap")
{"method": "io", "code": 3, "args": []}           // GetPosition()
```

---

## 10. 回测结果数据结构

### 10.1 task.Join() 返回JSON

```json
{
    "Profit": 1234.56,
    "Time": 1521691200000,
    "Elapsed": 42000000,
    "LoadElapsed": 5000000,
    "Progress": 100.0,
    "LogsCount": 150,
    "RuntimeLogs": [
        [0, 1518969600000, 1, "日志内容..."],
        [1, 1518970200000, 2, "交易记录..."]
    ],
    "Snapshort": [
        {/* 交易所状态快照 */}
    ],
    "Task": {
        /* 回测配置回显 */
        "Exchanges": [...],
        "Options": {
            "DataServer": "http://q.fmz.com",
            "Period": 3600000,
            "TimeBegin": 1514764800,
            "TimeEnd": 1530316800
        }
    },
    "Status": "completed"
}
```

### 10.2 task.Join(True) 返回 DataFrame

| 列名 | 说明 |
|------|------|
| `close` | 收盘价时间序列 |
| `balance` | 法币余额时间序列 |
| `stocks` | 币种数量时间序列 |
| `net` | 净值时间序列 |

### 10.3 关键回测指标

- **夏普比率 (Sharpe Ratio)** — 风险调整后收益
- **最大回撤率 (Maximum Drawdown)** — 最大峰谷跌幅
- **年化收益 (Annual Return)** — 年化收益率
- **Profit** — 总盈利

---

## 11. 图表与可视化

### 11.1 Chart (HighCharts/HighStocks)

```javascript
var chart = {
    __isStock: true,                    // 使用HighStocks (时间序列)
    title: { text: '策略分析' },
    xAxis: { type: 'datetime' },
    series: [
        { name: "line1", id: "line1", data: [] },
        { name: "line2", id: "line2", dashStyle: 'shortdash', data: [] }
    ]
}

var ObjChart = Chart(chart)
ObjChart.add([0, [timestamp, value]])   // 添加数据到series[0]
ObjChart.add([1, [timestamp, value]])   // 添加数据到series[1]
ObjChart.reset()                         // 清空图表
ObjChart.reset(10)                       // 保留最近10条
```

### 11.2 KLineChart

```python
chart = KLineChart({})
chart.begin(bar)                      # 开始渲染K线
chart.plot(value, "MA5", "red")       # 叠加指标线
chart.signal("buy", price, qty, id)   # 标记买卖信号
chart.close()                         # 结束渲染
```

---

## 12. 策略参数系统

### 12.1 参数类型

| 类型 | 说明 | 运行时值 |
|------|------|----------|
| `number` | 数值输入 | float/int |
| `string` | 文本输入 | string |
| `combox` | 下拉选择 | int (0-based索引) |
| `bool` | 开关 | boolean |
| `secretString` | 加密凭证 | string |

### 12.2 参数自动注入

策略参数作为**全局变量**自动注入:

```python
# UI定义: TradeAmount (number, 默认0.01)
def main():
    Log("交易量:", TradeAmount)  # 直接访问全局变量
```

### 12.3 参数分组与依赖

- 分组: 在描述中使用 `(groupname)` 语法
- 依赖: `paramName@dependencyParam` 条件显示（仅支持单个bool条件）

---

## 13. 扩展API接口

### 13.1 API基础信息

- **基础URL**: `https://www.fmz.com/api/v1`
- **认证**: Query参数传递
- **签名算法**: `MD5("version|method|args|nonce|secretKey")`

### 13.2 API方法列表

| 方法 | 功能 | 参数 |
|------|------|------|
| `GetNodeList` | 获取托管者列表 | 无 |
| `GetRobotGroupList` | 获取机器人分组 | 无 |
| `GetPlatformList` | 获取已配置交易所 | 无 |
| `GetRobotList` | 获取机器人列表 | offset, length, robotStatusCode |
| `CommandRobot` | 发送交互指令 | robotId, message |
| `StopRobot` | 停止机器人 | robotId |
| `RestartRobot` | 重启机器人 | robotId, settings |
| `GetRobotDetail` | 获取机器人详情 | robotId |
| `GetAccount` | 获取账户信息 | 无 |
| `GetExchangeList` | 获取支持交易所 | 无 |
| `DeleteNode` | 删除托管者 | nodeId |
| `DeleteRobot` | 删除机器人 | robotId |
| `GetStrategyList` | 获取策略列表 | 无 |
| `NewRobot` | 创建新机器人 | settings |
| `PluginRun` | 运行插件 | settings |
| `GetRobotLogs` | 获取机器人日志 | robotId |

### 13.3 返回格式

```json
{
    "code": 0,
    "data": {
        "result": { ... }
    }
}
```

### 13.4 NewRobot 配置

```python
settings = {
    "name": "robot_name",
    "args": [],
    "appid": "user_tag",
    "period": 60,
    "strategy": strategyId,
    "exchanges": [
        {"eid": "Binance", "pair": "BTC_USDT",
         "meta": {"AccessKey": "xxx", "SecretKey": "yyy"}}
    ]
}
```

### 13.5 CommandRobot

```python
# 命令格式: "action:amount"
# action: buy, sell, long, short, cover_long, cover_short, spk, bpk
# 策略端: GetCommand() 接收命令
```

---

## 14. 最佳实践与注意事项

### 14.1 回测环境注意

1. **回测结束机制**: 引擎通过 `EOFError` 结束循环，必须 `try-except` 捕获
2. **Sleep行为不同**: 回测中 `Sleep(ms)` 仅推进模拟时间，不要使用 `time.sleep()`
3. **数据预加载**: `GetRecords()` 会在回测开始前预加载约5000根K线
4. **重复调用推进时间**: 反复调用行情API也会自动推进时间线
5. **Python版本**: 仅支持 Python 3.10，3.13/3.14 会段错误
6. **无头环境**: `task.Show()` 依赖 matplotlib GUI，终端环境会崩溃

### 14.2 策略开发注意

7. **数据周期一致**: 自定义K线数据周期必须与 `basePeriod` 一致
8. **市价单参数**: 价格传 `-1` 表示市价单，注意现货买入 amount 为法币金额
9. **_G键类型**: `_G()` 的 key 必须为字符串，数字会报错
10. **回测功能限制**: `HttpQuery` 返回 `'dummy'`，`GetTrades()` 返回空，`Info` 不可用

### 14.3 回测方法论

11. **样本内外测试**: 用一段数据优化参数(样本内)，另一段验证(样本外)
12. **警惕过拟合**: "如果回测结果是超级赚钱的资金曲线，很多情况下是逻辑写错了"
13. **最少交易次数**: 交易次数太少的策略可能存在幸存者偏差
14. **回测仅供参考**: 实盘有滑点、延迟、网络等因素，回测结果只是参考

### 14.4 常见错误与解决

| 错误 | 原因 | 解决 |
|------|------|------|
| `InternalError: arg1 type error` | `_G()` key为数字 | 使用字符串key |
| `ERR_INSUFFICIENT_ASSET` | 余额不足 | 下单前检查余额 |
| `timeout` | 网络/交易所延迟 | 使用海外VPS |
| `Nonce is not increasing` | 系统时间不准 | 同步服务器时钟 |
| `decrypt failed` | 修改密码后API失效 | 重新配置API Key |
| `403 Access Denied` | API权限不足 | 开启所需权限 |
| `ERR_INVALID_ORDER` | 非法价格/数量 | 检查是否为负/零 |
| `Rate limit exceeded (429)` | API调用过频 | 降低请求频率 |

---

## 15. 自建回测系统参考架构

### 15.1 核心组件设计

基于FMZ API接口设计独立回测系统：

```python
class Exchange:
    """模拟交易所，实现FMZ exchange对象的核心接口"""

    def __init__(self, eid, currency, balance, stocks, fee=0.001):
        self.account = {
            "Balance": balance,      # 法币余额
            "FrozenBalance": 0,
            "Stocks": stocks,        # 币种数量
            "FrozenStocks": 0,
            "Equity": balance,
            "UPnL": 0
        }
        self.orders = {}             # 订单簿
        self.order_id = 0
        self.fee = fee               # 手续费率
        self.current_ticker = None
        self.records = []            # K线数据
        self.positions = []          # 持仓 (期货)

    def GetTicker(self):
        return self.current_ticker

    def GetRecords(self, period=None, limit=None):
        return self.records[:limit] if limit else self.records

    def GetDepth(self):
        # 从ticker生成简单深度
        return {
            "Asks": [{"Price": self.current_ticker["Sell"], "Amount": 1}],
            "Bids": [{"Price": self.current_ticker["Buy"], "Amount": 1}]
        }

    def GetAccount(self):
        return self.account.copy()

    def Buy(self, price, amount):
        # 市价单: price == -1
        if price == -1:
            price = self.current_ticker["Sell"]
        # 检查余额
        cost = price * amount * (1 + self.fee)
        if cost > self.account["Balance"]:
            return None
        # 执行成交
        self.account["Balance"] -= cost
        self.account["Stocks"] += amount
        self.order_id += 1
        return self.order_id

    def Sell(self, price, amount):
        if price == -1:
            price = self.current_ticker["Buy"]
        if amount > self.account["Stocks"]:
            return None
        revenue = price * amount * (1 - self.fee)
        self.account["Balance"] += revenue
        self.account["Stocks"] -= amount
        self.order_id += 1
        return self.order_id

    def Update(self, ticker, records=None):
        """更新行情（每个时间步调用）"""
        self.current_ticker = ticker
        if records:
            self.records = records


class BacktestEngine:
    """回测引擎"""

    def __init__(self, config):
        self.start_time = config["start"]
        self.end_time = config["end"]
        self.period = config["period"]
        self.exchanges = []
        self.logs = []
        self.profit_logs = []
        self.snapshots = []

        # 初始化交易所
        for ex_config in config["exchanges"]:
            self.exchanges.append(Exchange(
                eid=ex_config["eid"],
                currency=ex_config["currency"],
                balance=ex_config.get("balance", 10000),
                stocks=ex_config.get("stocks", 0)
            ))

    def load_data(self, data_source):
        """加载K线数据
        data_source: DataFrame或数组，格式:
        [timestamp, open, high, low, close, volume]
        """
        self.kline_data = data_source

    def run(self, strategy_func):
        """运行策略"""
        for i, bar in enumerate(self.kline_data):
            # 更新行情
            ticker = {
                "Time": bar[0] * 1000,
                "Open": bar[1], "High": bar[2],
                "Low": bar[3], "Last": bar[4],
                "Sell": bar[2],  # 简化: 用High近似
                "Buy": bar[3],   # 简化: 用Low近似
                "Volume": bar[5]
            }

            for ex in self.exchanges:
                ex.Update(ticker, self.kline_data[:i+1])

            # 执行策略
            try:
                strategy_func(self.exchanges[0], i)
            except Exception as e:
                self.logs.append(f"Error at bar {i}: {e}")

            # 快照
            self.snapshots.append({
                "time": bar[0],
                "account": self.exchanges[0].GetAccount()
            })

    def get_result(self):
        """获取回测结果"""
        initial = self.snapshots[0]["account"]
        final = self.snapshots[-1]["account"]

        initial_value = initial["Balance"] + initial["Stocks"] * self.kline_data[0][4]
        final_value = final["Balance"] + final["Stocks"] * self.kline_data[-1][4]

        return {
            "Profit": final_value - initial_value,
            "ProfitRate": (final_value - initial_value) / initial_value * 100,
            "InitialValue": initial_value,
            "FinalValue": final_value,
            "Snapshots": self.snapshots,
            "Logs": self.logs
        }
```

### 15.2 数据获取参考

```python
import requests
import pandas as pd

def fetch_binance_klines(symbol, interval, start_time, end_time=None, limit=1000):
    """从币安获取K线数据

    Args:
        symbol: 交易对，如 "BTCUSDT"
        interval: 周期，如 "1h", "15m", "1d"
        start_time: 开始时间戳(毫秒)
        end_time: 结束时间戳(毫秒)，可选
        limit: 每次请求最大条数(最大1000)

    Returns:
        DataFrame: [timestamp, open, high, low, close, volume]
    """
    url = "https://api.binance.com/api/v3/klines"
    all_data = []

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }
        if end_time:
            params["endTime"] = end_time

        data = requests.get(url, params=params).json()
        if not data:
            break

        for item in data:
            all_data.append([
                item[0] // 1000,  # 时间戳转秒
                float(item[1]),    # open
                float(item[2]),    # high
                float(item[3]),    # low
                float(item[4]),    # close
                float(item[5])     # volume
            ])

        start_time = data[-1][0] + 1
        if len(data) < limit:
            break

    return pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume"])


def fetch_binance_futures_klines(symbol, interval, start_time, end_time=None, limit=1000):
    """从币安期货获取K线数据"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    # 逻辑同上，仅URL不同
    pass
```

### 15.3 账户数据结构（多币种）

```python
account = {
    "USDT": {
        "realised_profit": 0,
        "unrealised_profit": 0,
        "total": 10000,
        "fee": 0
    },
    "BTC": {
        "amount": 0,
        "hold_price": 0,
        "value": 0,
        "price": 0,
        "realised_profit": 0,
        "unrealised_profit": 0,
        "fee": 0
    }
}
```

---

## 附录A: FMZ特有数据品种命名

| 类型 | 命名示例 | 说明 |
|------|----------|------|
| 现货 | `BTC_USDT` | 标准交易对 |
| 永续合约 | `BTC_USDT.swap` | CreateOrder用 |
| 当周合约 | `this_week` | SetContractType用 |
| 次周合约 | `next_week` | SetContractType用 |
| 季度合约 | `quarter` | SetContractType用 |
| CTP期货 | `rb1905`, `MA909` | 具体合约 |
| CTP指数 | `MA000` | 指数合约 |
| CTP主力 | `MA888` | 主力连续 |
| 期权 | `BTC-7AUG20-12750-C` | 标的-行权日-行权价-类型 |

## 附录B: JavaScript多线程API

FMZ为JavaScript策略提供系统级多线程:

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `__Thread(func, params)` | 创建线程 | 线程ID |
| `__threadJoin(id)` | 等待线程完成 | `{id, terminated, elapsed, ret}` |
| `__threadTerminate(id)` | 终止线程 | boolean |
| `__threadPostMessage(id, msg)` | 线程间通信 (id=0为主线程) | - |
| `__threadPeekMessage(timeout?)` | 接收消息 (0=阻塞) | 消息 |
| `__threadId()` | 获取当前线程ID | number |
| `__threadSetData(id, key, value)` | 线程本地存储 | - |
| `__threadGetData(id, key)` | 读取线程存储 | value |

## 附录C: MyLanguage (麦语言) 速查

### 数据引用
`OPEN/O`, `HIGH/H`, `LOW/L`, `CLOSE/C`, `VOL/V`, `OPI`, `REF(X,N)`, `UNIT`, `MINPRICE`

### 赋值操作符
- `:` — 赋值并输出到副图
- `:=` — 赋值不输出
- `^^` — 赋值并输出到主图
- `..` — 赋值显示数值不画线

### 信号指令
`BK`(买开), `SK`(卖开), `BP`(买平), `SP`(卖平), `BPK`(平空反手做多), `SPK`(平多反手做空), `CLOSEOUT`(全平)

### 信号过滤
`AUTOFILTER` — 一开一平过滤多余信号
`MULTSIG(...)` — 允许单K线多信号
`TRADE_AGAIN(N)` — 重复执行N次

### 跨周期引用
```
#IMPORT [MIN, 15, TEST] AS VAR15
CROSSUP(VAR15.AVG1, VAR15.AVG2), BPK;
```

### 嵌入JavaScript
```
%%
scope.CUSTOM = function(obj) {
    return obj.val * 100;
}
%%
ADJUSTED^^CUSTOM(C);
```

## 附录D: PINE Script FMZ扩展

与TradingView差异:
1. 版本声明可选 (`//@version=5` 非必需)
2. 不支持 `import`
3. 扩展 `overlay` 参数
4. 调试: `runtime.log()`, `runtime.debug()`, `runtime.error()`
5. 精度通过 "Pine Trading Library" 模板配置
6. `var` 初始化一次保持; `varip` 跨Tick保持
7. 支持闭合K线模型和实时价格模型两种执行方式

---

## 附录E: 参考链接

- [FMZ用户指南](https://www.fmz.com/user-guide)
- [FMZ API文档](https://www.fmz.com/api)
- [Python本地回测库(GitHub)](https://github.com/fmzquant/backtest_python)
- [JavaScript回测引擎(GitHub)](https://github.com/fmzquant/backtest_javascript)
- [扩展API Demo(GitHub)](https://github.com/fmzquant/fmz_extend_api_demo)
- [FMZ策略广场](https://www.fmz.com/square)
- [FMZ社区论坛](https://www.fmz.com/bbs)
