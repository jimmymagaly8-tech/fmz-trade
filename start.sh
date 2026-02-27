#!/usr/bin/env bash
# 启动 FMZ 回测平台
# - 生产模式: frontend/dist/ 存在时, 只启动后端 (静态文件由 FastAPI 托管)
# - 开发模式: 同时启动后端 + Vite 前端开发服务器
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$PROJECT_DIR/.pids"
LOG_DIR="$PROJECT_DIR/.logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

# 判断运行模式
if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    MODE="production"
else
    MODE="development"
fi

echo "运行模式: $MODE"

# 检查是否已在运行
if [ -f "$PID_DIR/backend.pid" ] && kill -0 "$(cat "$PID_DIR/backend.pid")" 2>/dev/null; then
    echo "后端已在运行 (PID $(cat "$PID_DIR/backend.pid"))"
    BACKEND_RUNNING=1
else
    BACKEND_RUNNING=0
fi

if [ "$MODE" = "development" ]; then
    if [ -f "$PID_DIR/frontend.pid" ] && kill -0 "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null; then
        echo "前端已在运行 (PID $(cat "$PID_DIR/frontend.pid"))"
        FRONTEND_RUNNING=1
    else
        FRONTEND_RUNNING=0
    fi
else
    FRONTEND_RUNNING=1  # 生产模式不需要前端进程
fi

if [ "$BACKEND_RUNNING" = "1" ] && [ "$FRONTEND_RUNNING" = "1" ]; then
    if [ "$MODE" = "production" ]; then
        echo "平台已在运行, 访问 http://localhost:8000"
    else
        echo "平台已在运行, 访问 http://localhost:5173"
    fi
    exit 0
fi

# 激活虚拟环境
source "$PROJECT_DIR/.venv/bin/activate"

# 启动后端
if [ "$BACKEND_RUNNING" = "0" ]; then
    echo "启动后端 (port 8000)..."
    if [ "$MODE" = "production" ]; then
        nohup python -m uvicorn backend.main:app \
            --host 0.0.0.0 --port 8000 \
            > "$LOG_DIR/backend.log" 2>&1 &
    else
        nohup python -m uvicorn backend.main:app \
            --host 0.0.0.0 --port 8000 --reload \
            > "$LOG_DIR/backend.log" 2>&1 &
    fi
    echo $! > "$PID_DIR/backend.pid"
    echo "后端已启动 (PID $!)"
fi

# 开发模式才启动前端
if [ "$MODE" = "development" ] && [ "$FRONTEND_RUNNING" = "0" ]; then
    echo "启动前端 (port 5173)..."
    cd "$PROJECT_DIR/frontend"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    echo "前端已启动 (PID $!)"
    cd "$PROJECT_DIR"
fi

# 等待服务就绪
echo ""
echo "等待服务启动..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "服务就绪"
        break
    fi
    sleep 1
done

echo ""
echo "================================"
echo "  FMZ 回测平台已启动"
if [ "$MODE" = "production" ]; then
    echo "  访问: http://localhost:8000"
else
    echo "  前端: http://localhost:5173"
    echo "  后端: http://localhost:8000"
fi
echo "  日志: $LOG_DIR/"
echo "  停止: ./stop.sh"
echo "================================"
