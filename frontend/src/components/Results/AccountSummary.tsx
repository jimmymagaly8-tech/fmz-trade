import { Descriptions, Table, Typography } from 'antd';
import type { AccountSummary as AccountSummaryType } from '../../types/backtest';

const { Text } = Typography;

interface Props {
  summary: AccountSummaryType;
}

const fmt = (v: number, decimals = 8) =>
  v !== 0 ? v.toFixed(decimals) : '0';

export default function AccountSummary({ summary }: Props) {
  const pnlColor = summary.pnl >= 0 ? '#3f8600' : '#cf1322';
  const annColor = summary.annualized_return >= 0 ? '#3f8600' : '#cf1322';

  // FMZ-style asset detail table
  const assetColumns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 140 },
    { title: '品种', dataIndex: 'currency', key: 'currency', width: 80 },
    {
      title: '余额', dataIndex: 'balance', key: 'balance',
      render: (v: number) => fmt(v),
    },
    {
      title: '冻结', dataIndex: 'frozen', key: 'frozen',
      render: (v: number) => fmt(v),
    },
    {
      title: '手续费', dataIndex: 'commission', key: 'commission',
      render: (v: number) => fmt(v),
    },
    {
      title: '资费', dataIndex: 'fundingFee', key: 'fundingFee',
      render: (v: number) => fmt(v),
    },
    {
      title: '平仓盈亏', dataIndex: 'closedPnl', key: 'closedPnl',
      render: (v: number) => fmt(v),
    },
    {
      title: '持仓盈亏', dataIndex: 'positionPnl', key: 'positionPnl',
      render: (v: number) => fmt(v),
    },
    {
      title: '保证金', dataIndex: 'margin', key: 'margin',
      render: (v: number) => fmt(v),
    },
    {
      title: '预估收益',
      dataIndex: 'estimatedProfit',
      key: 'estimatedProfit',
      render: (v: number) => (
        <Text strong style={{ color: v >= 0 ? '#3f8600' : '#cf1322' }}>
          {summary.quote_currency} {fmt(v)}
        </Text>
      ),
    },
  ];

  const assetData = [
    {
      key: '1',
      name: summary.exchange_name || '-',
      currency: summary.quote_currency || 'USDT',
      balance: summary.balance,
      frozen: summary.frozen_balance,
      commission: summary.commission,
      fundingFee: summary.funding_fee,
      closedPnl: summary.closed_pnl,
      positionPnl: summary.position_pnl,
      margin: summary.margin,
      estimatedProfit: summary.estimated_profit,
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header stats line */}
      <div style={{ padding: '4px 0', color: '#666', fontSize: 13 }}>
        日志总数: {summary.logs_count} - 交易次数: {summary.total_trades} - 耗时: {(summary.elapsed_ms / 1000).toFixed(3)}秒
      </div>

      {/* FMZ-style asset table */}
      <Table
        columns={assetColumns}
        dataSource={assetData}
        pagination={false}
        size="small"
        bordered
        scroll={{ x: 'max-content' }}
      />

      {/* Strategy performance metrics */}
      <Descriptions bordered size="small" column={3}>
        <Descriptions.Item label="初始资金">
          {summary.initial_balance.toFixed(2)} {summary.quote_currency}
        </Descriptions.Item>
        <Descriptions.Item label="最终资产">
          {summary.final_balance.toFixed(2)} {summary.quote_currency}
        </Descriptions.Item>
        <Descriptions.Item label="收益 (PnL)">
          <span style={{ color: pnlColor, fontWeight: 'bold' }}>
            {summary.pnl >= 0 ? '+' : ''}{summary.pnl.toFixed(2)} {summary.quote_currency}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="收益率">
          <span style={{ color: pnlColor, fontWeight: 'bold' }}>
            {summary.pnl_percent >= 0 ? '+' : ''}{summary.pnl_percent.toFixed(2)}%
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="年化收益率">
          <span style={{ color: annColor, fontWeight: 'bold' }}>
            {summary.annualized_return >= 0 ? '+' : ''}{summary.annualized_return.toFixed(2)}%
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="最大回撤">
          <span style={{ color: '#cf1322' }}>
            {summary.max_drawdown.toFixed(2)} {summary.quote_currency} ({summary.max_drawdown_percent.toFixed(2)}%)
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="夏普比率">
          <span style={{ fontWeight: 'bold' }}>
            {summary.sharpe_ratio.toFixed(4)}
          </span>
        </Descriptions.Item>
      </Descriptions>
    </div>
  );
}
