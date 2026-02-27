from fastapi import APIRouter, HTTPException

from backend.models.schemas import StrategyCreate, StrategyUpdate, StrategyResponse
from backend.services import strategy_service

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("", response_model=list[str])
def list_strategies():
    return strategy_service.list_strategies()


@router.get("/{name}", response_model=StrategyResponse)
def get_strategy(name: str):
    code = strategy_service.get_strategy(name)
    if code is None:
        raise HTTPException(404, "Strategy not found")
    return StrategyResponse(name=name, code=code)


@router.post("", response_model=StrategyResponse, status_code=201)
def create_strategy(body: StrategyCreate):
    if strategy_service.strategy_exists(body.name):
        raise HTTPException(409, "Strategy already exists")
    strategy_service.save_strategy(body.name, body.code)
    return StrategyResponse(name=body.name, code=body.code)


@router.put("/{name}", response_model=StrategyResponse)
def update_strategy(name: str, body: StrategyUpdate):
    if not strategy_service.strategy_exists(name):
        raise HTTPException(404, "Strategy not found")
    strategy_service.save_strategy(name, body.code)
    return StrategyResponse(name=name, code=body.code)


@router.delete("/{name}", status_code=204)
def delete_strategy(name: str):
    if not strategy_service.delete_strategy(name):
        raise HTTPException(404, "Strategy not found")
