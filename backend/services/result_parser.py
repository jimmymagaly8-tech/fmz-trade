import math
from backend.models.schemas import (
    BacktestResult, AccountSummary, SnapshotPoint, TradeRecord,
)

TYPE_LABELS = {0: "买入", 1: "卖出", 2: "撤单", 3: "错误", 4: "收益", 5: "日志"}


def parse_result(
    raw: dict, initial_balance: float = 10000, exchange_conf: dict | None = None,
) -> BacktestResult:
    snapshots = _parse_snapshots(raw.get("Snapshots", []))
    trades = _parse_trades(raw.get("RuntimeLogs", []))
    profit_logs = raw.get("ProfitLogs", [])
    logs_count = raw.get("LogsCount", 0)
    summary = _build_summary(
        raw, snapshots, trades, initial_balance, exchange_conf or {}, logs_count,
    )
    return BacktestResult(
        summary=summary,
        snapshots=snapshots,
        trades=trades,
        profit_logs=profit_logs if profit_logs else None,
        logs_count=logs_count,
    )


def _parse_snapshots(raw_snaps: list) -> list[SnapshotPoint]:
    points = []
    for snap in raw_snaps:
        ts = snap[0]
        info = snap[1][0] if snap[1] else {}

        # Extract position data from Symbols
        symbols = info.get("Symbols", {})
        total_long = 0.0
        total_short = 0.0
        total_margin = 0.0
        total_closed_pnl = 0.0
        for sym_data in symbols.values():
            long_info = sym_data.get("Long", {})
            short_info = sym_data.get("Short", {})
            total_long += long_info.get("Amount", 0)
            total_short += short_info.get("Amount", 0)
            total_margin += long_info.get("Margin", 0) + short_info.get("Margin", 0)
            total_closed_pnl += long_info.get("ClosedProfit", 0) + short_info.get("ClosedProfit", 0)

        if total_closed_pnl == 0:
            total_closed_pnl = info.get("CloseProfit", 0)

        points.append(SnapshotPoint(
            timestamp=ts,
            pnl=info.get("PnL", 0),
            utilization=info.get("Utilization", 0),
            long_amount=total_long,
            short_amount=total_short,
            margin=total_margin,
            closed_pnl=total_closed_pnl,
        ))
    return points


def _parse_trades(runtime_logs: list) -> list[TradeRecord]:
    trades = []
    for log in runtime_logs:
        if len(log) < 9:
            continue
        type_val = log[2]
        # include buy/sell/profit
        if type_val not in (0, 1, 4):
            continue
        trades.append(TradeRecord(
            id=log[0],
            timestamp=log[1],
            type=type_val,
            type_label=TYPE_LABELS.get(type_val, "未知"),
            exchange_idx=log[3],
            order_type=log[4],
            price=log[5] or 0,
            amount=log[6] or 0,
            message=str(log[7]) if log[7] else "",
            symbol=log[8] if len(log) > 8 else "",
            extra=str(log[9]) if len(log) > 9 else None,
        ))
    return trades


def _calc_sharpe_ratio(snapshots: list[SnapshotPoint]) -> float:
    """Calculate annualized Sharpe ratio from PnL snapshots."""
    if len(snapshots) < 2:
        return 0.0

    # Calculate period returns
    returns = []
    for i in range(1, len(snapshots)):
        prev_pnl = snapshots[i - 1].pnl
        curr_pnl = snapshots[i].pnl
        returns.append(curr_pnl - prev_pnl)

    if not returns:
        return 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_return = math.sqrt(variance) if variance > 0 else 0

    if std_return == 0:
        return 0.0

    # Estimate periods per year from timestamp range
    total_ms = snapshots[-1].timestamp - snapshots[0].timestamp
    if total_ms <= 0:
        return 0.0
    period_ms = total_ms / len(returns)
    periods_per_year = (365.25 * 24 * 3600 * 1000) / period_ms

    sharpe = (mean_return / std_return) * math.sqrt(periods_per_year)
    return round(sharpe, 4)


def _calc_annualized_return(
    pnl: float, initial_balance: float, snapshots: list[SnapshotPoint]
) -> float:
    """Calculate annualized return percentage."""
    if not snapshots or len(snapshots) < 2 or initial_balance <= 0:
        return 0.0

    total_ms = snapshots[-1].timestamp - snapshots[0].timestamp
    if total_ms <= 0:
        return 0.0

    total_return = pnl / initial_balance
    years = total_ms / (365.25 * 24 * 3600 * 1000)
    if years <= 0:
        return 0.0

    # (1 + total_return)^(1/years) - 1
    try:
        annualized = (1 + total_return) ** (1 / years) - 1
        return round(annualized * 100, 4)
    except (ValueError, OverflowError):
        return 0.0


def _extract_account_details(raw: dict, exchange_conf: dict, initial_balance: float):
    """Extract detailed account info from the last snapshot."""
    raw_snaps = raw.get("Snapshots", [])
    if not raw_snaps:
        return {}

    last_snap = raw_snaps[-1][1][0] if raw_snaps[-1][1] else {}
    assets = last_snap.get("Assets", [{}])
    asset = assets[0] if assets else {}

    balance = asset.get("Amount", 0)
    frozen = asset.get("FrozenAmount", 0)
    commission = asset.get("Commission", 0)
    funding_fee = asset.get("Fee", 0)  # 资费/Funding fee

    # Aggregate position info from all symbols
    symbols = last_snap.get("Symbols", {})
    total_margin = 0.0
    total_position_pnl = 0.0
    total_closed_pnl = 0.0
    for sym_data in symbols.values():
        long_info = sym_data.get("Long", {})
        short_info = sym_data.get("Short", {})
        total_margin += long_info.get("Margin", 0) + short_info.get("Margin", 0)
        total_position_pnl += long_info.get("Profit", 0) + short_info.get("Profit", 0)
        total_closed_pnl += long_info.get("ClosedProfit", 0) + short_info.get("ClosedProfit", 0)

    # If ClosedProfit not in symbols, try snapshot-level field
    if total_closed_pnl == 0:
        total_closed_pnl = last_snap.get("CloseProfit", 0)

    # 预估收益 = 余额 + 冻结 + 保证金 + 持仓盈亏 - 初始资金
    actual_initial = asset.get("Initial", initial_balance)
    estimated_profit = balance + frozen + total_margin + total_position_pnl - actual_initial

    # Exchange info from config
    eid = exchange_conf.get("eid", "")
    currency = exchange_conf.get("currency", "BTC_USDT")
    quote = currency.split("_")[-1] if "_" in currency else "USDT"

    return {
        "exchange_name": eid,
        "quote_currency": quote,
        "balance": balance,
        "frozen_balance": frozen,
        "commission": commission,
        "funding_fee": funding_fee,
        "closed_pnl": total_closed_pnl,
        "position_pnl": total_position_pnl,
        "margin": total_margin,
        "estimated_profit": estimated_profit,
    }


def _build_summary(
    raw: dict,
    snapshots: list[SnapshotPoint],
    trades: list[TradeRecord],
    initial_balance: float,
    exchange_conf: dict,
    logs_count: int,
) -> AccountSummary:
    # Prefer top-level Profit if available, otherwise from snapshots
    pnl = raw.get("Profit", None)
    if pnl is None and snapshots:
        pnl = snapshots[-1].pnl
    elif pnl is None:
        pnl = 0.0

    # Max drawdown
    peak = 0.0
    max_dd = 0.0
    for s in snapshots:
        if s.pnl > peak:
            peak = s.pnl
        dd = peak - s.pnl
        if dd > max_dd:
            max_dd = dd

    trade_count = sum(1 for t in trades if t.type in (0, 1))

    sharpe = _calc_sharpe_ratio(snapshots)
    annualized = _calc_annualized_return(pnl, initial_balance, snapshots)

    details = _extract_account_details(raw, exchange_conf, initial_balance)

    return AccountSummary(
        initial_balance=initial_balance,
        final_balance=initial_balance + pnl,
        final_stocks=0,
        pnl=pnl,
        pnl_percent=(pnl / initial_balance * 100) if initial_balance else 0,
        max_drawdown=max_dd,
        max_drawdown_percent=(max_dd / initial_balance * 100) if initial_balance else 0,
        sharpe_ratio=sharpe,
        annualized_return=annualized,
        total_trades=trade_count,
        elapsed_ms=raw.get("Elapsed", 0) / 1e6,
        load_elapsed_ms=raw.get("LoadElapsed", 0) / 1e6,
        logs_count=logs_count,
        **details,
    )
