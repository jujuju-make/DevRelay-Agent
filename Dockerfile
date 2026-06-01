FROM python:3.11-slim AS backend

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/static


# ── 前端构建阶段 ──
FROM node:20-slim AS frontend

WORKDIR /frontend
COPY frontend/ .
RUN npm install && npm run build


# ── 最终镜像 ──
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 从后端阶段复制 Python 代码
COPY --from=backend /app /app
# 从前端阶段复制构建产物
COPY --from=frontend /frontend/dist /app/static

EXPOSE 8000

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]

