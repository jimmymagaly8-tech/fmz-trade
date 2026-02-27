export interface ExchangeConfig {
  eid: string;
  currency: string;
  balance: number;
  stocks: number;
  fee?: [number, number] | null; // [maker, taker] 万分之
}

export interface BacktestConfig {
  start: string;
  end: string;
  period: string;
  basePeriod: string;
  mode: number; // 0=模拟级Tick, 1=实盘级Tick
  exchanges: ExchangeConfig[];
}

export interface TradeRecord {
  id: number;
  timestamp: number;
  type: number;
  type_label: string;
  exchange_idx: number;
  order_type: number;
  price: number;
  amount: number;
  message: string;
  symbol: string;
  extra?: string;
}

export interface SnapshotPoint {
  timestamp: number;
  pnl: number;
  utilization: number;
  long_amount: number;
  short_amount: number;
  margin: number;
  closed_pnl: number;
}

export interface AccountSummary {
  initial_balance: number;
  final_balance: number;
  final_stocks: number;
  pnl: number;
  pnl_percent: number;
  max_drawdown: number;
  max_drawdown_percent: number;
  sharpe_ratio: number;
  annualized_return: number;
  total_trades: number;
  elapsed_ms: number;
  load_elapsed_ms: number;
  // FMZ 账户明细
  exchange_name: string;
  quote_currency: string;
  balance: number;           // 余额
  frozen_balance: number;    // 冻结
  commission: number;        // 手续费
  funding_fee: number;       // 资费
  closed_pnl: number;       // 平仓盈亏
  position_pnl: number;     // 持仓盈亏
  margin: number;            // 保证金
  estimated_profit: number;  // 预估收益
  logs_count: number;        // 日志总数
}

export interface BacktestResult {
  summary: AccountSummary;
  snapshots: SnapshotPoint[];
  trades: TradeRecord[];
  logs_count: number;
}

export type BacktestStatus = 'idle' | 'running' | 'completed' | 'error';

export interface BacktestState {
  status: BacktestStatus;
  progress: number;
  stage: string;
  result: BacktestResult | null;
  error: string | null;
}
