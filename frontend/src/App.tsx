import { useState, useEffect, useCallback } from 'react';
import { Layout, Select, Button, Space, message, Input, Modal } from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  SaveOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import StrategyEditor from './components/Editor/StrategyEditor';
import BacktestConfigPanel from './components/Config/BacktestConfigPanel';
import ResultsPanel from './components/Results/ResultsPanel';
import { useBacktest } from './hooks/useBacktest';
import { fetchStrategies, fetchStrategy, saveStrategy } from './services/api';
import { parseDocstringConfig, updateDocstringConfig } from './utils/parseDocstring';
import type { BacktestConfig } from './types/backtest';

const { Header, Content } = Layout;

const DEFAULT_CODE = `# 在此编写你的策略
# API: exchange.GetRecords(), exchange.Buy(), exchange.Sell()
# 全局函数: Log(), Sleep(ms)

SHORT_PERIOD = 7
LONG_PERIOD = 25

def calc_ma(records, period):
    if len(records) < period:
        return None
    return sum(r["Close"] for r in records[-period:]) / period

holding = False
while True:
    try:
        records = exchange.GetRecords()
        if not records or len(records) < LONG_PERIOD + 2:
            Sleep(1000)
            continue

        ma_short = calc_ma(records, SHORT_PERIOD)
        ma_long = calc_ma(records, LONG_PERIOD)
        prev_ma_short = calc_ma(records[:-1], SHORT_PERIOD)
        prev_ma_long = calc_ma(records[:-1], LONG_PERIOD)

        if None in (ma_short, ma_long, prev_ma_short, prev_ma_long):
            Sleep(1000)
            continue

        ticker = exchange.GetTicker()
        price = ticker["Last"]

        if prev_ma_short <= prev_ma_long and ma_short > ma_long and not holding:
            account = exchange.GetAccount()
            amount = round((account["Balance"] * 0.95) / price, 4)
            if amount > 0.0001:
                exchange.Buy(price, amount)
                holding = True
                Log("买入:", price, "数量:", amount)

        elif prev_ma_short >= prev_ma_long and ma_short < ma_long and holding:
            account = exchange.GetAccount()
            amount = account["Stocks"]
            if amount > 0.0001:
                exchange.Sell(price, round(amount, 4))
                holding = False
                Log("卖出:", price, "数量:", round(amount, 4))

        Sleep(1000)
    except EOFError:
        break

Log("策略结束")
`;

const DEFAULT_CONFIG: BacktestConfig = {
  start: '2024-01-01 00:00:00',
  end: '2024-06-30 00:00:00',
  period: '1h',
  basePeriod: '1m',
  mode: 0,
  exchanges: [{
    eid: 'Binance',
    currency: 'BTC_USDT',
    balance: 10000,
    stocks: 0,
  }],
};

function App() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [config, setConfig] = useState<BacktestConfig>(DEFAULT_CONFIG);
  const [strategies, setStrategies] = useState<string[]>([]);
  const [currentStrategy, setCurrentStrategy] = useState<string | null>(null);
  const [newNameModal, setNewNameModal] = useState(false);
  const [newName, setNewName] = useState('');
  const { state, startBacktest, stopBacktest } = useBacktest();

  const loadStrategies = useCallback(async () => {
    try {
      const list = await fetchStrategies();
      setStrategies(list);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadStrategies();
  }, [loadStrategies]);

  const handleSelectStrategy = async (name: string) => {
    try {
      const s = await fetchStrategy(name);
      setCode(s.code);
      setCurrentStrategy(name);
      const parsed = parseDocstringConfig(s.code);
      if (parsed) {
        setConfig((prev) => ({
          ...prev,
          ...parsed,
          exchanges: parsed.exchanges || prev.exchanges,
        }));
      }
    } catch {
      message.error('加载策略失败');
    }
  };

  const handleSave = async () => {
    if (!currentStrategy) {
      setNewNameModal(true);
      return;
    }
    try {
      const updatedCode = updateDocstringConfig(code, config);
      setCode(updatedCode);
      await saveStrategy(currentStrategy, updatedCode);
      message.success('策略已保存');
      loadStrategies();
    } catch {
      message.error('保存失败');
    }
  };

  const handleCreateNew = async () => {
    if (!newName.trim()) return;
    try {
      const updatedCode = updateDocstringConfig(code, config);
      setCode(updatedCode);
      await saveStrategy(newName.trim(), updatedCode);
      setCurrentStrategy(newName.trim());
      setNewNameModal(false);
      setNewName('');
      message.success('策略已创建');
      loadStrategies();
    } catch {
      message.error('创建失败');
    }
  };

  const handleStart = () => {
    startBacktest(code, config);
  };

  const isRunning = state.status === 'running';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: '#001529',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 'bold', marginRight: 16 }}>
            策略回测平台
          </span>
          <Select
            placeholder="选择策略"
            value={currentStrategy}
            onChange={handleSelectStrategy}
            style={{ width: 200 }}
            allowClear
            onClear={() => {
              setCurrentStrategy(null);
              setCode(DEFAULT_CODE);
            }}
            options={strategies.map((s) => ({ label: s, value: s }))}
          />
        </div>
        <Space>
          <Button icon={<PlusOutlined />} onClick={() => setNewNameModal(true)}>
            新建
          </Button>
          <Button icon={<SaveOutlined />} onClick={handleSave}>
            保存
          </Button>
          {isRunning ? (
            <Button danger icon={<StopOutlined />} onClick={stopBacktest}>
              停止
            </Button>
          ) : (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart}>
              开始回测
            </Button>
          )}
        </Space>
      </Header>

      <Content style={{ padding: 16 }}>
        <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 64px - 32px - 350px)' }}>
          <div style={{ flex: '0 0 60%' }}>
            <StrategyEditor code={code} onChange={setCode} />
          </div>
          <div style={{ flex: '0 0 40%', overflow: 'auto' }}>
            <BacktestConfigPanel config={config} onChange={setConfig} />
          </div>
        </div>

        <div
          style={{
            marginTop: 16,
            background: '#fff',
            borderRadius: 8,
            minHeight: 300,
            border: '1px solid #f0f0f0',
          }}
        >
          <ResultsPanel state={state} />
        </div>
      </Content>

      <Modal
        title="新建策略"
        open={newNameModal}
        onOk={handleCreateNew}
        onCancel={() => setNewNameModal(false)}
        okText="创建"
        cancelText="取消"
      >
        <Input
          placeholder="策略名称 (英文/数字/下划线)"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onPressEnter={handleCreateNew}
        />
      </Modal>
    </Layout>
  );
}

export default App;
