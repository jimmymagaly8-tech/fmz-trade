import type { BacktestConfig, ExchangeConfig } from '../types/backtest';

const DOCSTRING_RE = /(?:'''|""")backtest\n([\s\S]*?)(?:'''|""")/;

/**
 * Parse a single exchange object from the docstring JSON.
 */
function parseExchangeObj(ex: Record<string, unknown>): ExchangeConfig {
  const result: ExchangeConfig = {
    eid: typeof ex.eid === 'string' ? ex.eid : 'Binance',
    currency: typeof ex.currency === 'string' ? ex.currency : 'BTC_USDT',
    balance: typeof ex.balance === 'number' ? ex.balance : 10000,
    stocks: typeof ex.stocks === 'number' ? ex.stocks : 0,
  };
  if (Array.isArray(ex.fee) && ex.fee.length === 2) {
    // FMZ docstring fee format: decimal percentages (e.g., 0.03 = 0.03%)
    // FMZ parseTask converts: int(fee[0]*10000) → internal 万分之 value
    // Frontend stores 万分之 integers, so: 0.03 * 10000 = 300
    result.fee = [
      Math.round(Number(ex.fee[0]) * 10000),
      Math.round(Number(ex.fee[1]) * 10000),
    ];
  }
  return result;
}

/**
 * Parse FMZ backtest docstring config from Python code.
 * Returns partial BacktestConfig if found, null otherwise.
 */
export function parseDocstringConfig(
  code: string,
): Partial<BacktestConfig> | null {
  const match = code.match(DOCSTRING_RE);
  if (!match) return null;

  const body = match[1];
  const result: Record<string, unknown> = {};
  let hasValue = false;

  for (const line of body.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const colonIdx = trimmed.indexOf(':');
    if (colonIdx === -1) continue;

    const key = trimmed.slice(0, colonIdx).trim();
    const value = trimmed.slice(colonIdx + 1).trim();

    switch (key) {
      case 'start':
      case 'end':
      case 'period':
      case 'basePeriod':
        result[key] = value;
        hasValue = true;
        break;
      case 'mode':
        result[key] = parseInt(value, 10);
        hasValue = true;
        break;
      case 'exchanges': {
        try {
          const arr = JSON.parse(value);
          if (Array.isArray(arr) && arr.length > 0) {
            result.exchanges = arr.map(parseExchangeObj);
            hasValue = true;
          }
        } catch {
          // invalid JSON, skip
        }
        break;
      }
    }
  }

  if (!hasValue) return null;

  return result as Partial<BacktestConfig>;
}

/**
 * Build a single exchange JSON object for the docstring.
 */
function buildExchangeObj(ex: ExchangeConfig): Record<string, unknown> {
  const obj: Record<string, unknown> = {
    eid: ex.eid,
    currency: ex.currency,
    balance: ex.balance,
    stocks: ex.stocks,
  };
  if (ex.fee != null) {
    // Frontend stores 万分之 integers (e.g., 300 = 0.03%)
    // FMZ docstring expects decimal percentages (e.g., 0.03)
    obj.fee = [ex.fee[0] / 10000, ex.fee[1] / 10000];
  }
  return obj;
}

/**
 * Build the docstring block text from a BacktestConfig.
 */
function buildDocstring(config: BacktestConfig): string {
  const exchangeObjs = config.exchanges.map(buildExchangeObj);
  const exchangesJson = exchangeObjs.map((o) => JSON.stringify(o)).join(',');

  return [
    `'''backtest`,
    `start: ${config.start}`,
    `end: ${config.end}`,
    `period: ${config.period}`,
    `basePeriod: ${config.basePeriod}`,
    `exchanges: [${exchangesJson}]`,
    `'''`,
  ].join('\n');
}

/**
 * Update or insert the FMZ backtest docstring in Python code.
 * If a docstring exists, replace it. Otherwise insert at the top.
 */
export function updateDocstringConfig(code: string, config: BacktestConfig): string {
  const docstring = buildDocstring(config);

  if (DOCSTRING_RE.test(code)) {
    return code.replace(DOCSTRING_RE, docstring);
  }

  // Insert at the top of the file
  return docstring + '\n\n' + code;
}
