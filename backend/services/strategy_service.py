from pathlib import Path
from backend.config import STRATEGIES_DIR


def list_strategies() -> list[str]:
    STRATEGIES_DIR.mkdir(exist_ok=True)
    return sorted(
        f.stem for f in STRATEGIES_DIR.glob("*.py") if f.is_file()
    )


def get_strategy(name: str) -> str | None:
    path = _strategy_path(name)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def save_strategy(name: str, code: str) -> None:
    STRATEGIES_DIR.mkdir(exist_ok=True)
    path = _strategy_path(name)
    path.write_text(code, encoding="utf-8")


def delete_strategy(name: str) -> bool:
    path = _strategy_path(name)
    if not path.exists():
        return False
    path.unlink()
    return True


def strategy_exists(name: str) -> bool:
    return _strategy_path(name).exists()


def _strategy_path(name: str) -> Path:
    # Sanitize name
    safe_name = "".join(c for c in name if c.isalnum() or c in ("_", "-"))
    return STRATEGIES_DIR / f"{safe_name}.py"
