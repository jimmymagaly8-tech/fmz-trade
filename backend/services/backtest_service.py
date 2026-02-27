import asyncio
import sys
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.config import VENV_PYTHON, RUNNER_SCRIPT, BACKTEST_TIMEOUT


# Python 3.10 兼容: asyncio.timeout 在 3.11 才引入
if sys.version_info >= (3, 11):
    _timeout_ctx = asyncio.timeout
else:
    @asynccontextmanager
    async def _timeout_ctx(delay):
        task = asyncio.current_task()
        loop = asyncio.get_event_loop()
        handle = loop.call_later(delay, task.cancel)
        try:
            yield
        except asyncio.CancelledError:
            raise TimeoutError
        finally:
            handle.cancel()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BacktestTask:
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    process: Any = None
    result: dict | None = None
    error: str | None = None
    config: dict = field(default_factory=dict)
    subscribers: list[asyncio.Queue] = field(default_factory=list)


_tasks: dict[str, BacktestTask] = {}


def get_task(task_id: str) -> BacktestTask | None:
    return _tasks.get(task_id)


async def start_backtest(strategy_code: str, config: dict) -> str:
    task_id = str(uuid.uuid4())[:8]
    task = BacktestTask(task_id=task_id, config=config)
    _tasks[task_id] = task

    asyncio.create_task(_run_backtest(task, strategy_code, config))
    return task_id


def subscribe(task_id: str) -> asyncio.Queue | None:
    task = _tasks.get(task_id)
    if not task:
        return None
    q: asyncio.Queue = asyncio.Queue()
    task.subscribers.append(q)

    # If already completed/failed, immediately send the final message
    if task.status == TaskStatus.COMPLETED and task.result is not None:
        q.put_nowait({"type": "complete", "data": task.result})
    elif task.status == TaskStatus.FAILED:
        q.put_nowait({"type": "error", "data": {"message": task.error or "Unknown error"}})

    return q


def unsubscribe(task_id: str, q: asyncio.Queue):
    task = _tasks.get(task_id)
    if task and q in task.subscribers:
        task.subscribers.remove(q)


async def stop_backtest(task_id: str) -> bool:
    task = _tasks.get(task_id)
    if not task or not task.process:
        return False
    try:
        task.process.kill()
        task.status = TaskStatus.CANCELLED
        await _broadcast(task, {"type": "error", "data": {"message": "Backtest cancelled"}})
        return True
    except ProcessLookupError:
        return False


async def _run_backtest(task: BacktestTask, strategy_code: str, config: dict):
    task.status = TaskStatus.RUNNING
    await _broadcast(task, {"type": "progress", "data": {"percent": 0, "stage": "starting"}})

    try:
        proc = await asyncio.create_subprocess_exec(
            str(VENV_PYTHON), str(RUNNER_SCRIPT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,  # 10MB, 默认64KB不够装回测结果JSON
        )
        task.process = proc

        input_data = json.dumps({
            "strategy_code": strategy_code,
            "config": config,
        }).encode()

        proc.stdin.write(input_data)
        await proc.stdin.drain()
        proc.stdin.close()

        # Read stdout line by line
        try:
            async with _timeout_ctx(BACKTEST_TIMEOUT):
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode().strip()
                    if not line_str:
                        continue
                    try:
                        msg = json.loads(line_str)
                        await _broadcast(task, msg)
                        if msg["type"] == "complete":
                            task.result = msg["data"]
                            task.status = TaskStatus.COMPLETED
                        elif msg["type"] == "error":
                            task.error = msg["data"].get("message", "Unknown error")
                            task.status = TaskStatus.FAILED
                    except json.JSONDecodeError:
                        pass
        except TimeoutError:
            proc.kill()
            task.status = TaskStatus.FAILED
            task.error = "Backtest timeout"
            await _broadcast(task, {"type": "error", "data": {"message": "Backtest timeout"}})
            return

        await proc.wait()

        if task.status == TaskStatus.RUNNING:
            # Process exited without sending complete/error
            stderr = await proc.stderr.read()
            stderr_str = stderr.decode() if stderr else ""
            if proc.returncode != 0:
                task.status = TaskStatus.FAILED
                task.error = stderr_str or f"Process exited with code {proc.returncode}"
                await _broadcast(task, {"type": "error", "data": {"message": task.error}})
            else:
                task.status = TaskStatus.FAILED
                task.error = "No result received"
                await _broadcast(task, {"type": "error", "data": {"message": task.error}})

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        await _broadcast(task, {"type": "error", "data": {"message": str(e)}})


async def _broadcast(task: BacktestTask, msg: dict):
    for q in task.subscribers:
        await q.put(msg)
