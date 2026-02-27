#!/usr/bin/env bash
# ============================================================
#  FMZ 回测平台 - Linux 服务器一键部署
#  用法: bash deploy.sh
# ============================================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================"
echo "  FMZ 回测平台 - 部署脚本"
echo "========================================"
echo ""

# ----------------------------------------------------------
# 1. 检查 Python 3.10
# ----------------------------------------------------------
PYTHON=""
for cmd in python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        if [ "$ver" = "3.10" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[!] 未找到 Python 3.10"
    echo "    请先安装: sudo apt install python3.10 python3.10-venv python3.10-dev"
    echo "    或使用 pyenv: pyenv install 3.10.14 && pyenv local 3.10.14"
    exit 1
fi
echo "[OK] Python: $PYTHON ($($PYTHON --version))"

# ----------------------------------------------------------
# 2. 创建 / 更新虚拟环境
# ----------------------------------------------------------
if [ ! -d ".venv" ]; then
    echo "[..] 创建虚拟环境..."
    $PYTHON -m venv .venv
fi
source .venv/bin/activate
echo "[OK] 虚拟环境已激活"

echo "[..] 安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
# FastAPI + uvicorn
pip install fastapi uvicorn[standard] -q
echo "[OK] Python 依赖安装完成"

# ----------------------------------------------------------
# 3. 构建前端
# ----------------------------------------------------------
if command -v node &>/dev/null; then
    NODE_VER=$(node --version | grep -oP '\d+' | head -1)
    echo "[OK] Node.js: $(node --version)"
else
    echo "[!] 未找到 Node.js, 正在安装..."
    # 使用 NodeSource 安装 Node 20 LTS
    if command -v apt &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
    elif command -v yum &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
        sudo yum install -y nodejs
    else
        echo "[!] 无法自动安装 Node.js, 请手动安装后重试"
        exit 1
    fi
    echo "[OK] Node.js: $(node --version)"
fi

echo "[..] 安装前端依赖..."
cd "$PROJECT_DIR/frontend"
npm install --silent 2>&1 | tail -1
echo "[..] 构建前端..."
npm run build
cd "$PROJECT_DIR"
echo "[OK] 前端构建完成 → frontend/dist/"

# ----------------------------------------------------------
# 4. 创建 strategies 目录
# ----------------------------------------------------------
mkdir -p strategies
echo "[OK] strategies/ 目录就绪"

# ----------------------------------------------------------
# 5. 创建 systemd 服务文件 (可选)
# ----------------------------------------------------------
SERVICE_FILE="fmz-trade.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=FMZ Backtest Platform
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"
echo ""
echo "启动方式 (二选一):"
echo ""
echo "  方式1 - 直接启动:"
echo "    ./start.sh"
echo ""
echo "  方式2 - systemd 服务 (推荐, 开机自启):"
echo "    sudo cp $SERVICE_FILE /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable fmz-trade"
echo "    sudo systemctl start fmz-trade"
echo ""
echo "  访问: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_SERVER_IP'):8000"
echo ""
