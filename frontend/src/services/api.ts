import type { BacktestConfig } from '../types/backtest';

const BASE = '/api';

export async function fetchStrategies(): Promise<string[]> {
  const res = await fetch(`${BASE}/strategies`);
  return res.json();
}

export async function fetchStrategy(name: string): Promise<{ name: string; code: string }> {
  const res = await fetch(`${BASE}/strategies/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error('Strategy not found');
  return res.json();
}

export async function saveStrategy(name: string, code: string): Promise<void> {
  const res = await fetch(`${BASE}/strategies/${encodeURIComponent(name)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    // Try creating new
    const res2 = await fetch(`${BASE}/strategies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, code }),
    });
    if (!res2.ok) throw new Error('Failed to save strategy');
  }
}

export async function deleteStrategy(name: string): Promise<void> {
  await fetch(`${BASE}/strategies/${encodeURIComponent(name)}`, { method: 'DELETE' });
}

export async function startBacktest(
  strategyCode: string,
  config: BacktestConfig,
): Promise<string> {
  const res = await fetch(`${BASE}/backtest/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      strategy_code: strategyCode,
      ...config,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to start backtest');
  }
  const data = await res.json();
  return data.task_id;
}

export async function stopBacktest(taskId: string): Promise<void> {
  await fetch(`${BASE}/backtest/${taskId}/stop`, { method: 'POST' });
}
