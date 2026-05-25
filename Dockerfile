FROM python:3.11-slim

WORKDIR /app

# 系统依赖：aiomysql 需要 libmysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 容器内默认使用 8000 端口
EXPOSE 8000

# 使用入口脚本等待 MySQL/Redis 就绪
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]

