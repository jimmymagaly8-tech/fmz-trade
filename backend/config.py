import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STRATEGIES_DIR = BASE_DIR / "strategies"

# Docker 里没有 .venv，直接用当前 Python 解释器
_venv_python = BASE_DIR / ".venv" / "bin" / "python"
VENV_PYTHON = _venv_python if _venv_python.exists() else Path(sys.executable)

RUNNER_SCRIPT = Path(__file__).resolve().parent / "workers" / "backtest_runner.py"

BACKTEST_TIMEOUT = 300  # 5 minutes
