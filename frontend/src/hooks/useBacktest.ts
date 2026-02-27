import { useState, useRef, useCallback } from 'react';
import type { BacktestConfig, BacktestState, BacktestResult } from '../types/backtest';
import { startBacktest as apiStartBacktest, stopBacktest as apiStopBacktest } from '../services/api';

const initialState: BacktestState = {
  status: 'idle',
  progress: 0,
  stage: '',
  result: null,
  error: null,
};

export function useBacktest() {
  const [state, setState] = useState<BacktestState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const taskIdRef = useRef<string | null>(null);

  const startBacktest = useCallback(async (code: string, config: BacktestConfig) => {
    // Clean up previous
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState({ status: 'running', progress: 0, stage: 'starting', result: null, error: null });

    try {
      const taskId = await apiStartBacktest(code, config);
      taskIdRef.current = taskId;

      // Open WebSocket
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${window.location.host}/ws/backtest/${taskId}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case 'progress':
            setState((prev) => ({
              ...prev,
              progress: msg.data.percent ?? prev.progress,
              stage: msg.data.stage ?? prev.stage,
            }));
            break;
          case 'complete':
            setState({
              status: 'completed',
              progress: 100,
              stage: 'done',
              result: msg.data as BacktestResult,
              error: null,
            });
            ws.close();
            break;
          case 'error':
            setState({
              status: 'error',
              progress: 0,
              stage: '',
              result: null,
              error: msg.data.message || 'Unknown error',
            });
            ws.close();
            break;
        }
      };

      ws.onerror = () => {
        setState((prev) => ({
          ...prev,
          status: 'error',
          error: 'WebSocket connection error',
        }));
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    } catch (err) {
      setState({
        status: 'error',
        progress: 0,
        stage: '',
        result: null,
        error: err instanceof Error ? err.message : 'Failed to start backtest',
      });
    }
  }, []);

  const stopBacktest = useCallback(async () => {
    if (taskIdRef.current) {
      await apiStopBacktest(taskIdRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState((prev) => ({ ...prev, status: 'idle', progress: 0 }));
  }, []);

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState(initialState);
  }, []);

  return { state, startBacktest, stopBacktest, reset };
}
