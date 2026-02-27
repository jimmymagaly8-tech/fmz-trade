import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TradeRecord } from '../../types/backtest';

interface Props {
  trades: TradeRecord[];
}

const TYPE_COLORS: Record<number, string> = {
  0: 'green',   // buy
  1: 'red',     // sell
  4: 'blue',    // profit
};

const columns: ColumnsType<TradeRecord> = [
  {
    title: '时间',
    dataIndex: 'timestamp',
    key: 'timestamp',
    width: 180,
    render: (ts: number) => new Date(ts).toLocaleString('zh-CN'),
  },
  {
    title: '类型',
    dataIndex: 'type_label',
    key: 'type_label',
    width: 80,
    render: (label: string, record) => (
      <Tag color={TYPE_COLORS[record.type] || 'default'}>{label}</Tag>
    ),
  },
  {
    title: '价格',
    dataIndex: 'price',
    key: 'price',
    width: 120,
    render: (v: number) => v ? v.toFixed(2) : '-',
  },
  {
    title: '数量',
    dataIndex: 'amount',
    key: 'amount',
    width: 120,
    render: (v: number) => v ? v.toFixed(6) : '-',
  },
  {
    title: '信息',
    dataIndex: 'message',
    key: 'message',
    ellipsis: true,
  },
];

export default function TradeLogTable({ trades }: Props) {
  return (
    <Table
      dataSource={trades}
      columns={columns}
      rowKey="id"
      size="small"
      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
      scroll={{ y: 300 }}
    />
  );
}
