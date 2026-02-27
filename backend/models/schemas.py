from pydantic import BaseModel
from typing import Optional


class StrategyCreate(BaseModel):
    name: str
    code: str


class StrategyUpdate(BaseModel):
    code: str


class StrategyResponse(BaseModel):
    name: str
    code: str


class ExchangeConfig(BaseModel):
    eid: str = "Binance"
    currency: str = "BTC_USDT"
    balance: float = 10000
    stocks: float = 0
    fee: list[float] | None = None  # [maker, taker] 万分之, e.g. [150, 200]


class BacktestRequest(BaseModel):
    strategy_code: str
    start: str  # "2024-01-01 00:00:00"
    end: str
    period: str  # "1h"
    basePeriod: str  # "15m"
    mode: int = 0  # 0=模拟级Tick, 1=实盘级Tick
    exchanges: list[ExchangeConfig] = [ExchangeConfig()]


class BacktestStartResponse(BaseModel):
    task_id: str


class TradeRecord(BaseModel):
    id: int
    timestamp: int
    type: int  # 0=buy, 1=sell, 2=cancel, 3=error, 4=profit, 5=log
    type_label: str
    exchange_idx: int
    order_type: int
    price: float
    amount: float
    message: str
    symbol: str
    extra: Optional[str] = None


class SnapshotPoint(BaseModel):
    timestamp: int
    pnl: float
    utilization: float
    long_amount: float = 0       # 多仓数量
    short_amount: float = 0      # 空仓数量
    margin: float = 0            # 保证金
    closed_pnl: float = 0        # 平仓盈亏


class AccountSummary(BaseModel):
    initial_balance: float
    final_balance: float
    final_stocks: float
    pnl: float
    pnl_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    annualized_return: float
    total_trades: int
    elapsed_ms: float
    load_elapsed_ms: float
    # FMZ 账户明细
    exchange_name: str = ""
    quote_currency: str = "USDT"
    balance: float = 0           # 余额
    frozen_balance: float = 0    # 冻结
    commission: float = 0        # 手续费
    funding_fee: float = 0       # 资费
    closed_pnl: float = 0       # 平仓盈亏
    position_pnl: float = 0     # 持仓盈亏
    margin: float = 0            # 保证金
    estimated_profit: float = 0  # 预估收益
    logs_count: int = 0          # 日志总数


class BacktestResult(BaseModel):
    summary: AccountSummary
    snapshots: list[SnapshotPoint]
    trades: list[TradeRecord]
    profit_logs: list[list] | None = None  # ProfitLogs 原始数据
    logs_count: int
