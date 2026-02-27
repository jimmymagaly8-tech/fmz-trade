import { Tabs, Progress, Alert, Empty } from 'antd';
import type { BacktestState } from '../../types/backtest';
import AccountSummary from './AccountSummary';
import EquityCurveChart from './EquityCurveChart';
import TradeLogTable from './TradeLogTable';

interface Props {
  state: BacktestState;
}

export default function ResultsPanel({ state }: Props) {
  if (state.status === 'idle') {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Empty description="配置参数后点击「开始回测」" />
      </div>
    );
  }

  if (state.status === 'running') {
    return (
      <div style={{ padding: '24px 40px' }}>
        <div style={{ marginBottom: 8, color: '#666' }}>
          回测运行中... {state.stage}
        </div>
        <Progress
          percent={state.progress}
          status="active"
          strokeColor={{ from: '#108ee9', to: '#87d068' }}
        />
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" showIcon message="回测失败" description={state.error} />
      </div>
    );
  }

  if (!state.result) return null;

  const items = [
    {
      key: 'summary',
      label: '账户摘要',
      children: <AccountSummary summary={state.result.summary} />,
    },
    {
      key: 'chart',
      label: '收益曲线',
      children: <EquityCurveChart snapshots={state.result.snapshots} summary={state.result.summary} />,
    },
    {
      key: 'trades',
      label: `交易日志 (${state.result.trades.length})`,
      children: <TradeLogTable trades={state.result.trades} />,
    },
  ];

  return (
    <div style={{ padding: '0 16px 16px' }}>
      <Tabs defaultActiveKey="summary" items={items} />
    </div>
  );
}
