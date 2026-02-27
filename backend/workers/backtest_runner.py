"""
Backtest runner - executed as a subprocess.
Reads JSON config from stdin, runs FMZ backtest, writes JSON messages to stdout.

Protocol (one JSON per line to stdout):
  {"type":"progress","data":{"percent":50}}
  {"type":"log","data":{"message":"..."}}
  {"type":"complete","data":{...raw FMZ result...}}
  {"type":"error","data":{"message":"..."}}
"""
import sys
import json
import re
import signal
import traceback

TIMEOUT = 300  # 5 minutes


def timeout_handler(signum, frame):
    msg = json.dumps({"type": "error", "data": {"message": "Backtest timeout (5 min)"}})
    print(msg, flush=True)
    sys.exit(1)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(TIMEOUT)


PERIOD_MAP = {
    "1m": 60000,
    "3m": 180000,
    "5m": 300000,
    "15m": 900000,
    "30m": 1800000,
    "1h": 3600000,
    "2h": 7200000,
    "4h": 14400000,
    "6h": 21600000,
    "12h": 43200000,
    "1d": 86400000,
}


def period_to_ms(period_str: str) -> int:
    if period_str in PERIOD_MAP:
        return PERIOD_MAP[period_str]
    # Try numeric (already ms)
    try:
        return int(period_str)
    except ValueError:
        pass
    # Try parsing "Xh", "Xm", "Xd" patterns
    m = re.match(r"^(\d+)(m|h|d)$", period_str)
    if m:
        val, unit = int(m.group(1)), m.group(2)
        multipliers = {"m": 60000, "h": 3600000, "d": 86400000}
        return val * multipliers[unit]
    raise ValueError(f"Unknown period format: {period_str}")


def emit(msg_type: str, data: dict):
    line = json.dumps({"type": msg_type, "data": data}, ensure_ascii=False)
    print(line, flush=True)


_skip_patterns = [
    re.compile(r"^\s*from\s+fmz\s+import"),
    re.compile(r"^\s*import\s+fmz\b"),
    re.compile(r"^\s*\w+\s*=\s*(?:fmz\.)?VCtx\("),  # task/_ task = VCtx() or fmz.VCtx()
    re.compile(r".*\w+\.Join\("),                      # task.Join() / _task.Join()
    re.compile(r".*\w+\.Show\("),                      # task.Show() / _task.Show()
    re.compile(r"^\s*if\s+__name__\s*=="),
    re.compile(r"^\s*main\(\)\s*$"),
    re.compile(r"^\s*_LOCAL\s*="),                     # _LOCAL = False / True
    re.compile(r"^\s*_task\s*=\s*None"),               # _task = None
    re.compile(r"^\s*_g\s*=\s*\{"),                    # _g = {"__builtins__": ...}
    re.compile(r"^\s*globals\(\)\.update\("),           # globals().update(...)
]


def _remove_env_detection_block(code: str) -> str:
    """Remove try: exchange except NameError: ... block (environment detection)."""
    lines = code.split("\n")
    result = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "try:":
            # Look ahead for: exchange + except NameError
            j = i + 1
            found_exchange = False
            found_except = False
            while j < len(lines):
                s = lines[j].strip()
                if not s or s.startswith("#"):
                    j += 1
                    continue
                if s == "exchange" and not found_exchange:
                    found_exchange = True
                    j += 1
                    continue
                if found_exchange and "except" in s and "NameError" in s:
                    found_except = True
                    break
                break
            if found_exchange and found_except:
                # Skip entire except block (by indentation)
                base_indent = len(lines[i]) - len(lines[i].lstrip())
                i = j + 1  # skip past "except NameError:" line
                while i < len(lines):
                    if lines[i].strip() == "":
                        i += 1
                        continue
                    if (len(lines[i]) - len(lines[i].lstrip())) <= base_indent:
                        break
                    i += 1
                continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def _remove_conditional_blocks(code: str) -> str:
    """Remove if _LOCAL / if _task conditional blocks."""
    lines = code.split("\n")
    result = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r"^if\s+_LOCAL\b", stripped) or re.match(r"^if\s+_task\b", stripped):
            base_indent = len(lines[i]) - len(lines[i].lstrip())
            i += 1
            while i < len(lines):
                if lines[i].strip() == "":
                    i += 1
                    continue
                if (len(lines[i]) - len(lines[i].lstrip())) <= base_indent:
                    break
                i += 1
            continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def strip_boilerplate(code: str) -> str:
    """Remove FMZ boilerplate so the code can run inside our controlled VCtx."""
    # 1. Remove docstring config block
    code = re.sub(r"'''backtest\n.*?'''", "", code, flags=re.DOTALL)
    code = re.sub(r'"""backtest\n.*?"""', "", code, flags=re.DOTALL)
    # 2. Remove env detection block (try: exchange except NameError: ...)
    code = _remove_env_detection_block(code)
    # 3. Remove if _LOCAL / if _task blocks
    code = _remove_conditional_blocks(code)
    # 4. Line-level pattern removal
    lines = code.split("\n")
    filtered = [l for l in lines if not any(p.match(l) for p in _skip_patterns)]
    return "\n".join(filtered)


def extract_strategy_body(code: str) -> str:
    """Extract the strategy logic, unwrapping from main() if present."""
    code = strip_boilerplate(code)

    # Check if there's a main() function we need to unwrap
    main_match = re.search(r"^def\s+main\(\):\s*$", code, re.MULTILINE)
    if main_match:
        code = _unwrap_main(code)

    # Remove post-backtest reporting code (everything after the except EOFError: break block)
    # These are typically print/reporting statements that reference task.Join() results
    code = _trim_after_backtest_loop(code)

    return code


def _unwrap_main(code: str) -> str:
    """Unwrap the body of main() function, dedenting by one level."""
    lines = code.split("\n")
    main_line_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^def\s+main\(\):\s*$", line):
            main_line_idx = i
            break

    if main_line_idx is None:
        return code

    before_main = lines[:main_line_idx]
    body_lines = []
    for offset, line in enumerate(lines[main_line_idx + 1:]):
        actual_idx = main_line_idx + 1 + offset
        if line.strip() == "":
            body_lines.append("")
            continue
        if line[0] in (" ", "\t"):
            if line.startswith("    "):
                body_lines.append(line[4:])
            elif line.startswith("\t"):
                body_lines.append(line[1:])
            else:
                body_lines.append(line)
        else:
            body_lines.append(line)
            body_lines.extend(lines[actual_idx + 1:])
            break

    return "\n".join(before_main) + "\n" + "\n".join(body_lines)


def _trim_after_backtest_loop(code: str) -> str:
    """Remove post-loop reporting code that references task/result variables."""
    lines = code.split("\n")
    # Find the last 'except EOFError' line - everything after its break is reporting
    last_eof_idx = None
    for i, line in enumerate(lines):
        if re.match(r".*except\s+EOFError", line):
            last_eof_idx = i

    if last_eof_idx is None:
        return code

    # Find the break after except EOFError
    break_idx = None
    for i in range(last_eof_idx + 1, len(lines)):
        if lines[i].strip() == "break":
            break_idx = i
            break

    if break_idx is None:
        return code

    # Keep up to the break line, plus any Log() calls immediately after,
    # but drop result-processing code
    result_lines = lines[:break_idx + 1]

    # Scan remaining lines - keep only simple Log() calls at same indent or less
    for i in range(break_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if stripped == "":
            continue
        # Keep simple Log() calls
        if re.match(r"^Log\(", stripped):
            result_lines.append(line)
        else:
            # Stop at first non-Log, non-empty line (result processing code)
            break

    return "\n".join(result_lines)


FEE_DEFAULTS = {
    "Huobi": [150, 200],
    "OKX": [150, 200],
    "Binance": [150, 200],
    "Futures_Binance": [300, 300],    # FMZ web platform: 0.03% maker/taker
    "Futures_BitMEX": [8, 10],
    "Futures_OKX": [30, 30],
    "Futures_HuobiDM": [30, 30],
    "Futures_CTP": [25, 25],
    "Futures_XTP": [30, 130],
}


def _build_exchange_entry(exchange_conf: dict, base_period: int) -> dict:
    """Build a single exchange entry for the FMZ task config."""
    currency = exchange_conf.get("currency", "BTC_USDT")
    eid = exchange_conf.get("eid", "Binance")
    arr = currency.upper().split("_")
    if len(arr) == 1:
        arr.append("CNY" if "CTP" in eid else "USD")

    custom_fee = exchange_conf.get("fee")
    if custom_fee and len(custom_fee) == 2:
        fee = [int(custom_fee[0]), int(custom_fee[1])]
    else:
        fee = FEE_DEFAULTS.get(eid, [2000, 2000])

    return {
        "Balance": exchange_conf.get("balance", 10000),
        "Stocks": exchange_conf.get("stocks", 3.0),
        "BaseCurrency": arr[0],
        "QuoteCurrency": arr[1],
        "BasePeriod": base_period,
        "FeeDenominator": 6,
        "FeeMaker": fee[0],
        "FeeTaker": fee[1],
        "FeeMin": exchange_conf.get("feeMin", 0),
        "Id": eid,
        "Label": eid,
    }


def build_task_config(config: dict) -> dict:
    """Build the raw task dict matching FMZ parseTask output format."""
    import time as _time
    from datetime import datetime

    start_dt = datetime.strptime(config["start"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config["end"], "%Y-%m-%d %H:%M:%S")

    start_ts = int(_time.mktime(start_dt.timetuple()))
    end_ts = int(_time.mktime(end_dt.timetuple()))

    period = period_to_ms(config["period"])
    base_period_str = config.get("basePeriod", "")
    if base_period_str:
        base_period = period_to_ms(base_period_str)
    else:
        # Auto basePeriod selection (matching FMZ logic)
        base_period = 3600000  # default 1h
        if period == 86400000:
            base_period = 3600000
        elif period == 3600000:
            base_period = 1800000
        elif period == 1800000:
            base_period = 900000
        elif period == 900000:
            base_period = 300000
        elif period == 300000:
            base_period = 60000

    # Backward compatible: support both "exchanges" (new) and "exchange" (old)
    exchanges_conf = config.get("exchanges", [config.get("exchange", {})])
    exchanges = [_build_exchange_entry(ex, base_period) for ex in exchanges_conf]

    # CTP uses different data server — check first exchange
    first_eid = exchanges_conf[0].get("eid", "") if exchanges_conf else ""
    data_server = "http://q.fmz.com"
    if "CTP" in first_eid:
        data_server = "http://q.youquant.com"

    test_range = end_ts - start_ts
    if test_range / 3600 <= 2:
        snapshot_period = 60
    elif test_range / 86400 <= 2:
        snapshot_period = 300
    elif test_range / 86400 < 30:
        snapshot_period = 3600
    else:
        snapshot_period = 86400

    # RetFlags: match FMZ parseTask (445)
    # Status(1) | Indicators(4) | Chart(8) | ProfitLogs(16) |
    # RuntimeLogs(32) | Accounts(128) | PnL(256)
    ret_flags = 1 | 4 | 8 | 16 | 32 | 128 | 256

    mode = config.get("mode", 0)  # 0=模拟级Tick, 1=实盘级Tick

    options = {
        "DataServer": data_server,
        "MaxChartLogs": 800,
        "MaxProfitLogs": 800,
        "MaxRuntimeLogs": 800,
        "NetDelay": 200,
        "Period": period,
        "RetFlags": ret_flags,
        "TimeBegin": start_ts,
        "TimeEnd": end_ts,
        "UpdatePeriod": 5000,
        "SnapshotPeriod": snapshot_period * 1000,
        "Mode": mode,
    }

    return {"Exchanges": exchanges, "Options": options}


def run_backtest(strategy_code: str, config: dict):
    import fmz

    task_config = build_task_config(config)

    emit("progress", {"percent": 5, "stage": "initializing"})

    # VCtx injects exchange/Log/Sleep/etc. into the gApis dict
    # We pass our own dict so we can control what the strategy sees
    g = {"__builtins__": __builtins__}

    task = fmz.VCtx(task=task_config, gApis=g)

    emit("progress", {"percent": 10, "stage": "running"})

    # Add common imports available to strategies
    import json as _json
    import math as _math
    import time as _time_mod
    import datetime as _datetime_mod
    g["json"] = _json
    g["math"] = _math
    g["time"] = _time_mod
    g["datetime"] = _datetime_mod
    try:
        import numpy
        g["numpy"] = numpy
        g["np"] = numpy
    except ImportError:
        pass
    try:
        import talib
        g["talib"] = talib
    except ImportError:
        pass

    # Extract and run strategy logic
    body = extract_strategy_body(strategy_code)
    exec(compile(body, "<strategy>", "exec"), g)

    emit("progress", {"percent": 90, "stage": "collecting_results"})

    raw_result = task.Join()
    result = _json.loads(raw_result)

    emit("progress", {"percent": 100, "stage": "done"})
    emit("complete", result)


def main():
    try:
        input_data = sys.stdin.read()
        payload = json.loads(input_data)

        strategy_code = payload["strategy_code"]
        config = payload["config"]

        run_backtest(strategy_code, config)

    except Exception as e:
        emit("error", {"message": str(e), "traceback": traceback.format_exc()})
        sys.exit(1)


if __name__ == "__main__":
    main()
