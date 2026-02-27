import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STRATEGIES_DIR = BASE_DIR / "strategies"
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
RUNNER_SCRIPT = Path(__file__).resolve().parent / "workers" / "backtest_runner.py"

BACKTEST_TIMEOUT = 300  # 5 minutes
