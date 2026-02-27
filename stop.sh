#!/usr/bin/env bash
# 停止 FMZ 回测平台
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$PROJECT_DIR/.pids"

stopped=0

for service in backend frontend; do
    pidfile="$PID_DIR/$service.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            # 同时终止子进程 (uvicorn worker / vite)
            pkill -P "$pid" 2>/dev/null
            kill "$pid" 2>/dev/null
            echo "已停止 $service (PID $pid)"
            stopped=1
        else
            echo "$service 未在运行"
        fi
        rm -f "$pidfile"
    fi
done

if [ "$stopped" = "0" ]; then
    echo "没有正在运行的服务"
fi

echo "平台已停止"
