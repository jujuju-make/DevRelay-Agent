# DevRelay-Agent — AI 驱动的开发者资讯聚合助手

> 一个基于 **LangChain ReAct + FastAPI** 的 AI Agent，自动追踪 GitHub 仓库更新和技术博客，生成结构化报告并归档。
>
> 简历关键词：`AI Agent` `LangChain` `FastAPI` `异步架构` `Redis/MySQL` `Docker`

---

## 📌 项目亮点

| 维度 | 说明 |
|------|------|
| **AI Agent** | 基于 LangChain ReAct 模式，LLM 自主决策调用 7 种工具完成复杂任务 |
| **多源聚合** | GitHub API + RSS/Atom 订阅 + 全网搜索 + 网页抓取，一站式追踪技术动态 |
| **异步架构** | 全链路 `async/await`（httpx、SQLAlchemy async、Redis），支持高并发 |
| **智能归档** | 自动判断回答质量 → 暂存 Redis → 前端确认 → 持久化到 MySQL |
| **自动日报** | 定时任务拉取 commits → LLM 总结 → 自动归档，零人工介入 |
| **容器化** | Docker Compose 一键启动 MySQL + Redis + 应用，开箱即用 |
| **测试覆盖** | 63 个测试用例（pytest + mock），覆盖全部核心逻辑，无外部依赖 |

---

## 🏗 架构设计

```
┌────────────┐   POST /api/v1/agent/run    ┌──────────────────┐
│  用户/前端  │ ──────────────────────────▶ │  FastAPI 服务     │
│            │ ◀────────────────────────── │  (异步, ASGI)    │
└────────────┘      SSE / JSON 响应        └────────┬─────────┘
                                                    │
                          ┌─────────────────────────┼──────────────┐
                          ▼                         ▼              ▼
              ┌────────────────────┐    ┌───────────────┐   ┌──────────┐
              │ LangChain ReAct    │    │   Redis 缓存   │   │  MySQL   │
              │ Agent (7 工具)     │    │  · 聊天记忆 24h │   │  · 报告   │
              │                    │    │  · Commit 10min │   │  · 订阅   │
              └──────┬──────┬──────┘    └───────────────┘   └──────────┘
                     │      │
          ┌──────────┘      └──────────┐
          ▼                             ▼
  ┌──────────────┐           ┌──────────────────┐
  │ GitHub API   │           │  外部服务         │
  │ · commits    │           │ · RSS/Atom 订阅   │
  │ · 文件读取   │           │ · Serper 搜索     │
  │ · diff 分析  │           │ · 网页抓取        │
  └──────────────┘           └──────────────────┘
```

### Agent 工具集（LLM 自动选择调用）

| 工具 | 功能 | 来源 |
|------|------|------|
| `fetch_repo_commits` | 获取仓库最近提交 | GitHub API |
| `read_github_file` | 读取 README、源码等 | GitHub API |
| `review_commit_diff` | 分析某次 commit 的代码 diff | GitHub API |
| `fetch_rss_feed` | 抓取技术博客更新 | RSS/Atom |
| `search_web` | 全网搜索补充信息 | Serper API |
| `read_web_page` | 读取网页正文 | Jina AI |
| `save_to_mysql` | 归档为结构化报告 | MySQL |

### 关键设计决策

- **ReAct 而非纯 Function Calling**：LangChain 的 ReAct 让 LLM 边思考边调用工具，适合需要多步推理的追踪场景
- **异步全链路**：httpx、aiomysql、redis asyncio，避免 IO 阻塞
- **双层缓存**：Redis 缓存 commit（10min）减少 API 调用 + 聊天记忆（24h）支持多轮对话
- **归档工作流**：Agent 回答 → 自动判断质量 → Redis 暂存 → 前端确认 → MySQL 持久化，用户掌控数据
- **测试隔离**：所有外部请求用 respx + AsyncMock 模拟，测试无需真实 API

---

## 🚀 快速开始

```bash
# 克隆
git clone https://github.com/jujuju-make/DevRelay-Agent.git
cd DevRelay-Agent

# 配置（至少填写 OPENAI_API_KEY 和 GITHUB_TOKEN）
cp .env.example .env

# 一键启动
docker compose up -d

# 查看日志
docker compose logs -f app

# 访问
open http://localhost:8000/docs
```

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | LLM 推理（支持 OpenAI 兼容 API） |
| `GITHUB_TOKEN` | ✅ | GitHub API 访问 |
| `SERPER_API_KEY` | ❌ | 全网搜索（不填则禁用） |

---

## 📊 测试质量

```
pytest tests/ -v --cov=app
=> 63 passed, 覆盖率 >85%
```

| 测试文件 | 覆盖内容 |
|----------|----------|
| `test_health.py` | 健康检查 API |
| `test_github_tools.py` | GitHub/搜索/RSS 工具、缓存键 |
| `test_agent_logic.py` | Agent 编排、消息提取、来源解析 |
| `test_cache.py` | Redis 缓存读写、异常处理 |
| `test_chat_memory.py` | 聊天记忆生命周期 |
| `test_reports.py`
