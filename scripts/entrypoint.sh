#!/bin/bash
set -e

echo "等待 MySQL 就绪..."
until python -c "
import asyncio
import aiomysql
loop = asyncio.get_event_loop()
loop.run_until_complete(aiomysql.connect(
    host='mysql', port=3306,
    user='devrelay', password='devrelay123',
    db='devrelay'
))
" 2>/dev/null; do
    sleep 2
done
echo "MySQL 已就绪 ✅"

echo "等待 Redis 就绪..."
until python -c "
import redis
r = redis.Redis(host='redis', port=6379)
r.ping()
" 2>/dev/null; do
    sleep 2
done
echo "Redis 已就绪 ✅"

echo "启动 DevRelay Agent..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
