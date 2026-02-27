# Stage 1: 构建前端
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com && npm install --silent
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 运行环境
FROM python:3.10-slim
WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt ./
COPY vendor/ ./vendor/
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt \
    && pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    fastapi uvicorn[standard]

# 应用代码
COPY backend/ ./backend/
COPY strategies/ ./strategies/

# 前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 策略目录可挂载
VOLUME /app/strategies

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
