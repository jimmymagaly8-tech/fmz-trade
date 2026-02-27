import { Form, Select, DatePicker, InputNumber, Card, Row, Col, Radio, Collapse, Button, Space } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { BacktestConfig, ExchangeConfig } from '../../types/backtest';

interface Props {
  config: BacktestConfig;
  onChange: (config: BacktestConfig) => void;
}

const EXCHANGES = [
  { label: '现货', options: [
    { label: 'Binance', value: 'Binance' },
    { label: 'OKX', value: 'OKX' },
    { label: 'Huobi', value: 'Huobi' },
    { label: 'Bitfinex', value: 'Bitfinex' },
  ]},
  { label: '合约', options: [
    { label: 'Binance 合约', value: 'Futures_Binance' },
    { label: 'OKX 合约', value: 'Futures_OKX' },
    { label: 'HuobiDM 合约', value: 'Futures_HuobiDM' },
    { label: 'BitMEX 合约', value: 'Futures_BitMEX' },
  ]},
  { label: '商品期货', options: [
    { label: 'CTP 期货', value: 'Futures_CTP' },
    { label: 'XTP 期货', value: 'Futures_XTP' },
  ]},
];

const CURRENCIES = [
  'BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT',
  'XRP_USDT', 'ADA_USDT', 'DOGE_USDT', 'DOT_USDT',
  'BTC_USD', 'ETH_USD', 'ETH_BTC',
];

const PERIODS = [
  { label: '1 分钟', value: '1m' },
  { label: '3 分钟', value: '3m' },
  { label: '5 分钟', value: '5m' },
  { label: '15 分钟', value: '15m' },
  { label: '30 分钟', value: '30m' },
  { label: '1 小时', value: '1h' },
  { label: '2 小时', value: '2h' },
  { label: '4 小时', value: '4h' },
  { label: '6 小时', value: '6h' },
  { label: '8 小时', value: '8h' },
  { label: '12 小时', value: '12h' },
  { label: '1 天', value: '1d' },
  { label: '3 天', value: '3d' },
  { label: '1 周', value: '1w' },
];

// Default fees per exchange (万分之: maker, taker)
// Match FMZ web platform defaults (fmz.py feeDef + Futures_Binance confirmed)
const FEE_DEFAULTS: Record<string, [number, number]> = {
  Binance: [150, 200],
  OKX: [150, 200],
  Huobi: [150, 200],
  Futures_Binance: [300, 300],    // FMZ web platform: 0.03% maker/taker
  Futures_OKX: [30, 30],
  Futures_HuobiDM: [30, 30],
  Futures_BitMEX: [8, 10],
  Futures_CTP: [25, 25],
  Futures_XTP: [30, 130],
};

const MAX_EXCHANGES = 5;

function ExchangeCard({
  exchange,
  index,
  total,
  onUpdate,
  onRemove,
}: {
  exchange: ExchangeConfig;
  index: number;
  total: number;
  onUpdate: (partial: Partial<ExchangeConfig>) => void;
  onRemove: () => void;
}) {
  const defaultFee = FEE_DEFAULTS[exchange.eid] || [2000, 2000];

  return (
    <Card
      size="small"
      title={`交易所 ${index + 1}`}
      extra={
        total > 1 ? (
          <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={onRemove} />
        ) : null
      }
      styles={{ body: { padding: '8px 12px' } }}
      style={{ marginBottom: 8 }}
    >
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="交易所" style={{ marginBottom: 8 }}>
            <Select
              value={exchange.eid}
              onChange={(v) => onUpdate({ eid: v })}
              options={EXCHANGES}
              size="small"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="交易对" style={{ marginBottom: 8 }}>
            <Select
              value={exchange.currency}
              onChange={(v) => onUpdate({ currency: v })}
              options={CURRENCIES.map((c) => ({ label: c, value: c }))}
              showSearch
              size="small"
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="初始资金 (USDT)" style={{ marginBottom: 8 }}>
            <InputNumber
              value={exchange.balance}
              onChange={(v) => v !== null && onUpdate({ balance: v })}
              min={0}
              style={{ width: '100%' }}
              size="small"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="初始持仓" style={{ marginBottom: 8 }}>
            <InputNumber
              value={exchange.stocks}
              onChange={(v) => v !== null && onUpdate({ stocks: v })}
              min={0}
              step={0.01}
              style={{ width: '100%' }}
              size="small"
            />
          </Form.Item>
        </Col>
      </Row>

      <Collapse
        size="small"
        items={[{
          key: 'fee',
          label: `手续费 (默认: Maker ${(defaultFee[0] / 10000).toFixed(3)}% / Taker ${(defaultFee[1] / 10000).toFixed(3)}%)`,
          children: (
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item label="Maker (万分之)" style={{ marginBottom: 4 }}>
                  <InputNumber
                    value={exchange.fee?.[0] ?? defaultFee[0]}
                    onChange={(v) => {
                      const taker = exchange.fee?.[1] ?? defaultFee[1];
                      onUpdate({ fee: v !== null ? [v, taker] : null });
                    }}
                    min={0}
                    style={{ width: '100%' }}
                    size="small"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Taker (万分之)" style={{ marginBottom: 4 }}>
                  <InputNumber
                    value={exchange.fee?.[1] ?? defaultFee[1]}
                    onChange={(v) => {
                      const maker = exchange.fee?.[0] ?? defaultFee[0];
                      onUpdate({ fee: v !== null ? [maker, v] : null });
                    }}
                    min={0}
                    style={{ width: '100%' }}
                    size="small"
                  />
                </Form.Item>
              </Col>
            </Row>
          ),
        }]}
      />
    </Card>
  );
}

export default function BacktestConfigPanel({ config, onChange }: Props) {
  const updateExchange = (index: number, partial: Partial<ExchangeConfig>) => {
    const updated = config.exchanges.map((ex, i) =>
      i === index ? { ...ex, ...partial } : ex,
    );
    onChange({ ...config, exchanges: updated });
  };

  const addExchange = () => {
    if (config.exchanges.length >= MAX_EXCHANGES) return;
    onChange({
      ...config,
      exchanges: [
        ...config.exchanges,
        { eid: 'Binance', currency: 'BTC_USDT', balance: 10000, stocks: 0 },
      ],
    });
  };

  const removeExchange = (index: number) => {
    if (config.exchanges.length <= 1) return;
    onChange({
      ...config,
      exchanges: config.exchanges.filter((_, i) => i !== index),
    });
  };

  return (
    <Card title="回测配置" size="small" styles={{ body: { padding: '12px 16px' } }}>
      <Form layout="vertical" size="small">
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label="开始时间">
              <DatePicker
                value={dayjs(config.start)}
                onChange={(d) => d && onChange({ ...config, start: d.format('YYYY-MM-DD HH:mm:ss') })}
                showTime
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="结束时间">
              <DatePicker
                value={dayjs(config.end)}
                onChange={(d) => d && onChange({ ...config, end: d.format('YYYY-MM-DD HH:mm:ss') })}
                showTime
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label="K线周期">
              <Select
                value={config.period}
                onChange={(v) => onChange({ ...config, period: v })}
                options={PERIODS}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="底层周期">
              <Select
                value={config.basePeriod}
                onChange={(v) => onChange({ ...config, basePeriod: v })}
                options={[{ label: '自动', value: '' }, ...PERIODS]}
                allowClear
                placeholder="自动"
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="回测模式">
          <Radio.Group
            value={config.mode}
            onChange={(e) => onChange({ ...config, mode: e.target.value })}
          >
            <Radio value={0}>模拟级 Tick（快速）</Radio>
            <Radio value={1}>实盘级 Tick（精确）</Radio>
          </Radio.Group>
        </Form.Item>

        {config.exchanges.map((ex, i) => (
          <ExchangeCard
            key={i}
            exchange={ex}
            index={i}
            total={config.exchanges.length}
            onUpdate={(partial) => updateExchange(i, partial)}
            onRemove={() => removeExchange(i)}
          />
        ))}

        {config.exchanges.length < MAX_EXCHANGES && (
          <Space style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}>
            <Button
              type="dashed"
              size="small"
              icon={<PlusOutlined />}
              onClick={addExchange}
            >
              添加交易所
            </Button>
          </Space>
        )}
      </Form>
    </Card>
  );
}
