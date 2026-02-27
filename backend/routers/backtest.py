import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from backend.models.schemas import BacktestRequest, BacktestStartResponse
from backend.services import backtest_service
from backend.services.result_parser import parse_result

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/start", response_model=BacktestStartResponse)
async def start_backtest(body: BacktestRequest):
    config = {
        "start": body.start,
        "end": body.end,
        "period": body.period,
        "basePeriod": body.basePeriod,
        "mode": body.mode,
        "exchanges": [ex.model_dump() for ex in body.exchanges],
    }
    task_id = await backtest_service.start_backtest(body.strategy_code, config)
    return BacktestStartResponse(task_id=task_id)


@router.post("/{task_id}/stop")
async def stop_backtest(task_id: str):
    ok = await backtest_service.stop_backtest(task_id)
    if not ok:
        raise HTTPException(404, "Task not found or already stopped")
    return {"status": "cancelled"}


# WebSocket endpoint is mounted separately (no prefix)
ws_router = APIRouter()


@ws_router.websocket("/ws/backtest/{task_id}")
async def backtest_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()

    queue = backtest_service.subscribe(task_id)
    if queue is None:
        await websocket.send_json({"type": "error", "data": {"message": "Task not found"}})
        await websocket.close()
        return

    try:
        while True:
            msg = await queue.get()
            # Parse complete results into frontend-friendly format
            if msg["type"] == "complete":
                raw_data = msg["data"]
                task = backtest_service.get_task(task_id)
                exchanges_conf = task.config.get("exchanges", [{}]) if task else [{}]
                initial_balance = sum(ex.get("balance", 0) for ex in exchanges_conf)
                exchange_conf = exchanges_conf[0] if exchanges_conf else {}
                parsed = parse_result(raw_data, initial_balance, exchange_conf)
                await websocket.send_json({
                    "type": "complete",
                    "data": json.loads(parsed.model_dump_json()),
                })
            else:
                await websocket.send_json(msg)

            if msg["type"] in ("complete", "error"):
                break
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass
    finally:
        backtest_service.unsubscribe(task_id, queue)
