import ReactECharts from 'echarts-for-react';
import type { SnapshotPoint, AccountSummary } from '../../types/backtest';

interface Props {
  snapshots: SnapshotPoint[];
  summary: AccountSummary;
}

const fmtDate = (ts: number) => {
  const d = new Date(ts);
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const months = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];
  return `${day}. ${months[m - 1]}`;
};

const fmtFull = (ts: number) => {
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
};

export default function EquityCurveChart({ snapshots, summary }: Props) {
  if (!snapshots.length) return null;

  const timestamps = snapshots.map((s) => s.timestamp);

  // --- Derived data ---
  const pnlData = snapshots.map((s) => Math.round(s.pnl * 10000) / 10000);
  const pnlPctData = snapshots.map((s) =>
    summary.initial_balance ? Math.round((s.pnl / summary.initial_balance) * 10000) / 100 : 0
  );

  // 周期盈亏: difference between consecutive PnL
  const periodPnl = snapshots.map((s, i) =>
    i === 0 ? 0 : Math.round((s.pnl - snapshots[i - 1].pnl) * 10000) / 10000
  );

  // 持仓
  const longData = snapshots.map((s) => s.long_amount);
  const shortData = snapshots.map((s) => -s.short_amount); // negative for display

  // 资金利用率
  const utilData = snapshots.map((s) => Math.round(s.utilization * 10000) / 100);

  // --- Header stats ---
  const initVal = summary.initial_balance;
  const cumReturn = summary.pnl_percent;
  const annReturn = summary.annualized_return;
  const sharpe = summary.sharpe_ratio;
  const maxDD = summary.max_drawdown_percent;

  // Annualized volatility: std of returns * sqrt(periods/year)
  const returns: number[] = [];
  for (let i = 1; i < snapshots.length; i++) {
    returns.push(snapshots[i].pnl - snapshots[i - 1].pnl);
  }
  const mean = returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : 0;
  const variance = returns.length ? returns.reduce((a, r) => a + (r - mean) ** 2, 0) / returns.length : 0;
  const std = Math.sqrt(variance);
  let annVol = 0;
  if (snapshots.length >= 2) {
    const totalMs = snapshots[snapshots.length - 1].timestamp - snapshots[0].timestamp;
    const periodMs = totalMs / returns.length;
    const periodsPerYear = (365.25 * 24 * 3600 * 1000) / periodMs;
    annVol = (std / (initVal || 1)) * Math.sqrt(periodsPerYear) * 100;
  }

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: {
        type: 'cross' as const,
        link: [{ xAxisIndex: 'all' }],
      },
      formatter: (params: any[]) => {
        if (!params || !params.length) return '';
        const ts = timestamps[params[0].dataIndex];
        const idx = params[0].dataIndex;
        const pnl = pnlData[idx];
        const pnlPct = pnlPctData[idx];
        const pp = periodPnl[idx];
        const lg = longData[idx];
        const sh = snapshots[idx].short_amount;
        const ut = utilData[idx];

        return `<div style="font-size:12px;line-height:1.8">
          <div style="font-weight:bold;margin-bottom:4px">${fmtFull(ts)}</div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4b7cf3;margin-right:6px"></span>浮动盈亏: <b>${pnl.toFixed(4)}</b> (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)</div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#e76f51;margin-right:6px"></span>周期盈亏: <b>${pp.toFixed(4)}</b></div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#52c41a;margin-right:6px"></span>多仓: ${lg}</div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#faad14;margin-right:6px"></span>空仓: ${sh ? -sh : 0}</div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#8c6d1f;margin-right:6px"></span>资金利用率: ${ut.toFixed(2)}%</div>
        </div>`;
      },
    },
    legend: {
      data: ['浮动盈亏', '周期盈亏', '多仓', '空仓', '资金利用率'],
      bottom: 0,
      textStyle: { fontSize: 11 },
      itemWidth: 14,
      itemHeight: 10,
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
    },
    grid: [
      { left: 60, right: 60, top: 10,  height: '30%' },   // 浮动盈亏
      { left: 60, right: 60, top: '46%', height: '14%' },  // 周期盈亏
      { left: 60, right: 60, top: '64%', height: '14%' },  // 持仓
      { left: 60, right: 60, top: '82%', height: '10%' },  // 资金利用率
    ],
    xAxis: [
      {
        type: 'category' as const,
        data: timestamps,
        gridIndex: 0,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#ddd' } },
        splitLine: { show: true, lineStyle: { color: '#f5f5f5' } },
      },
      {
        type: 'category' as const,
        data: timestamps,
        gridIndex: 1,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#ddd' } },
      },
      {
        type: 'category' as const,
        data: timestamps,
        gridIndex: 2,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#ddd' } },
      },
      {
        type: 'category' as const,
        data: timestamps,
        gridIndex: 3,
        axisLabel: {
          formatter: (val: number) => fmtDate(val),
          fontSize: 10,
          color: '#999',
        },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#ddd' } },
      },
    ],
    yAxis: [
      // 0: 浮动盈亏 (left)
      {
        type: 'value' as const,
        gridIndex: 0,
        position: 'right' as const,
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { fontSize: 10, color: '#999' },
        nameTextStyle: { fontSize: 10, color: '#999', padding: [0, 40, 0, 0] },
        name: '浮动盈亏',
      },
      // 1: 周期盈亏
      {
        type: 'value' as const,
        gridIndex: 1,
        position: 'right' as const,
        splitLine: { show: false },
        axisLabel: { fontSize: 10, color: '#999' },
        name: '周期盈亏',
        nameTextStyle: { fontSize: 10, color: '#999', padding: [0, 40, 0, 0] },
      },
      // 2: 持仓
      {
        type: 'value' as const,
        gridIndex: 2,
        position: 'right' as const,
        splitLine: { show: false },
        axisLabel: { fontSize: 10, color: '#999' },
        name: '持仓',
        nameTextStyle: { fontSize: 10, color: '#999', padding: [0, 24, 0, 0] },
      },
      // 3: 资金利用率
      {
        type: 'value' as const,
        gridIndex: 3,
        position: 'right' as const,
        splitLine: { show: false },
        axisLabel: { fontSize: 10, color: '#999', formatter: '{value}%' },
        name: '资金利用率',
        nameTextStyle: { fontSize: 10, color: '#999', padding: [0, 50, 0, 0] },
      },
    ],
    dataZoom: [
      {
        type: 'slider' as const,
        xAxisIndex: [0, 1, 2, 3],
        bottom: 25,
        height: 18,
        borderColor: '#ddd',
        fillerColor: 'rgba(24,144,255,0.15)',
        handleStyle: { color: '#1890ff' },
      },
      {
        type: 'inside' as const,
        xAxisIndex: [0, 1, 2, 3],
      },
    ],
    series: [
      // --- Grid 0: 浮动盈亏 ---
      {
        name: '浮动盈亏',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: pnlData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#4b7cf3' },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(75,124,243,0.25)' },
              { offset: 1, color: 'rgba(75,124,243,0.02)' },
            ],
          },
        },
        itemStyle: { color: '#4b7cf3' },
      },
      // --- Grid 1: 周期盈亏 (bar) ---
      {
        name: '周期盈亏',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: periodPnl.map((v) => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#7ec578' : '#e8574a' },
        })),
        barMaxWidth: 6,
      },
      // --- Grid 2: 多仓 (bar) ---
      {
        name: '多仓',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: longData,
        barMaxWidth: 6,
        itemStyle: { color: '#52c41a' },
        stack: 'position',
      },
      // --- Grid 2: 空仓 (bar) ---
      {
        name: '空仓',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: shortData,
        barMaxWidth: 6,
        itemStyle: { color: '#faad14' },
        stack: 'position',
      },
      // --- Grid 3: 资金利用率 (area) ---
      {
        name: '资金利用率',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: utilData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1, color: '#8c6d1f' },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(250,173,20,0.35)' },
              { offset: 1, color: 'rgba(250,173,20,0.05)' },
            ],
          },
        },
        itemStyle: { color: '#8c6d1f' },
      },
    ],
  };

  return (
    <div>
      {/* Header stats */}
      <div style={{
        textAlign: 'center',
        padding: '8px 0 4px',
        fontSize: 13,
        color: '#666',
      }}>
        初始净值：{initVal.toFixed(0)}{' '}
        累计收益: {cumReturn >= 0 ? '' : ''}{cumReturn.toFixed(3)} %,{' '}
        年化收益(365天): {annReturn.toFixed(3)} %,{' '}
        夏普比率：{sharpe.toFixed(3)},{' '}
        年化波动率：{annVol.toFixed(3)} %,{' '}
        最大回撤：{maxDD.toFixed(3)} %
      </div>
      <ReactECharts
        option={option}
        style={{ height: 560 }}
        notMerge={true}
      />
    </div>
  );
}
