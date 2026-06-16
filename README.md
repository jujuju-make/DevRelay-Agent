# DevRelay-Agent — AI 驱动的开发者资讯聚合助手

> 基于 **LangChain ReAct + FastAPI** 的 AI Agent，自动追踪 GitHub 仓库更新和技术博客，生成结构化报告并归档。

**在线体验：** [http://43.138.144.162:8000](http://43.138.144.162:8000)

---

## 项目简介

DevRelay-Agent 是一个 AI 驱动的开发者资讯聚合工具。它通过 LangChain ReAct Agent 自主调用多种工具，帮助开发者一站式追踪关注的 GitHub 仓库动态和技术博客更新，并自动生成日报归档。

### 核心能力

| 能力 | 说明 |
|------|------|
| **AI Agent 编排** | 基于 LangChain ReAct 模式，LLM 自主决策调用 7 种工具，通过多步推理完成复杂追踪任务 |
| **多源信息聚合** | GitHub API + RSS/Atom 订阅 + 全网搜索 + 网页抓取，一站式追踪技术动态 |
| **全链路异步架构** | httpx + SQLAlchemy async + Redis asyncio，避免 IO 阻塞，支持高并发 |
| **智能归档工作流** | Agent 回答 → 自动质量判断 → Redis 暂存 → 前端确认 → MySQL 持久化 |
| **自动日报系统** | 定时任务拉取 commits → LLM 总结 → 自动归档，零人工介入 |
| **用户认证** | JWT 登录/注册，前端路由守卫，用户数据隔离 |
| **容器化部署** | Docker Compose 一键启动 MySQL + Redis + 应用，开箱即用 |

---

## 架构设计

```
用户 / 浏览器 (React SPA)
       │
       ▼
  FastAPI (ASGI, Uvicorn)
  /api/v1/auth/*      注册/登录
  /api/v1/agent/run   AI 对话
  /api/v1/reports/*   报告查询
  /api/v1/subscriptions/*  订阅管理
       │
  ┌────┼────┐
  ▼    ▼    ▼
Agent  Redis MySQL
(LLM)  (缓存) (持久化)
  │
  └── 外部数据源
      GitHub API / RSS / Serper 搜索 / 网页抓取
```

### Agent 工具集（LLM 自动选择调用）

| 工具 | 功能 | 数据源 |
|------|------|--------|
| `fetch_repo_commits` | 获取仓库最近提交 | GitHub REST API |
| `read_github_file` | 读取 README、源码文件等 | GitHub REST API |
| `review_commit_diff` | 分析某次 commit 的代码 diff | GitHub REST API |
| `fetch_rss_feed` | 抓取技术博客/资讯更新 | RSS/Atom |
| `search_web` | 全网搜索补充技术信息 | Serper API (Google) |
| `read_web_page` | 读取网页正文内容 | Jina AI Reader |
| `save_to_mysql` | 归档为结构化报告 | MySQL |

### 关键设计决策

- **ReAct 而非纯 Function Calling**：LangChain 的 ReAct 让 LLM 边思考边调用工具（Thought → Action → Observation），适合需要多步推理的追踪场景
- **异步全链路**：httpx、aiomysql、redis asyncio，避免 IO 阻塞
- **双层缓存**：Redis 缓存 commit（10min）减少 API 调用 + 聊天记忆（24h）支持多轮对话
- **归档工作流**：Agent 回答 → 自动判断质量 → Redis 暂存 → 前端确认 → MySQL 持久化
- **JWT 无状态认证**：python-jose 签发/验证，无需 session 存储
- **测试隔离**：所有外部请求用 respx + AsyncMock 模拟，测试无需真实 API

---

## 快速开始

### Docker Compose 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/jujuju-make/DevRelay-Agent.git
cd DevRelay-Agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写：
#   OPENAI_API_KEY=sk-xxx
#   GITHUB_TOKEN=ghp_xxx

# 3. 构建并启动
docker compose up -d --build

# 4. 访问
open http://localhost:8000
```

### 手动部署（开发模式）

```bash
# 后端
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload  # http://localhost:8000

# 前端（可选，单独开发前端时）
cd frontend
npm install
npm run dev  # http://localhost:3000（已配置 /api 代理）
```

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | LLM 推理（支持 OpenAI 兼容 API） |
| `GITHUB_TOKEN` | ✅ | GitHub API 访问 |
| `JWT_SECRET_KEY` | ❌ | JWT 签名密钥（生产环境务必修改） |
| `SERPER_API_KEY` | ❌ | 全网搜索（不填则禁用） |

---

## 项目结构

```
DevRelay-Agent/
├── main.py                    # FastAPI 应用入口
├── Dockerfile                 # 多阶段构建（Python + Node）
├── docker-compose.yml         # 一键启动（MySQL + Redis + App）
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
├── app/
│   ├── config.py              # Pydantic Settings 配置
│   ├── database.py            # SQLAlchemy async 引擎
│   ├── models/                # ORM 模型
│   │   ├── user.py            # 用户表
│   │   ├── report.py          # 报告表
│   │   └── subscription.py    # 订阅表
│   ├── schemas/               # Pydantic 请求/响应模型
│   ├── routers/               # FastAPI 路由
│   │   ├── auth.py            # 注册/登录
│   │   ├── agent.py           # Agent 对话
│   │   ├── reports.py         # 报告查询
│   │   └── subscriptions.py   # 订阅管理
│   ├── services/              # 核心业务逻辑
│   │   ├── agent_logic.py     # LangChain ReAct 编排
│   │   ├── agent_graph.py     # 归档工作流
│   │   ├── daily_digest.py    # 自动日报
│   │   ├── chat_memory.py     # Redis 聊天记忆
│   │   ├── cache.py           # Redis 缓存
│   │   └── auth.py            # JWT + 密码哈希
│   └── tools/                 # Agent 工具集
│       ├── github.py          # GitHub API 工具
│       ├── rss.py             # RSS 抓取
│       └── read_web_page.py   # 网页正文读取
├── frontend/                  # React SPA 前端
├── tests/                     # pytest 测试
└── scripts/
    └── entrypoint.sh          # Docker 启动脚本
```

---

## API 一览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 | ❌ |
| POST | `/api/v1/auth/login` | 用户登录 | ❌ |
| GET | `/api/v1/auth/me` | 获取当前用户信息 | ✅ |
| POST | `/api/v1/agent/run` | 运行 AI Agent | ❌ |
| POST | `/api/v1/agent/archive-decision` | 确认/拒绝归档 | ❌ |
| GET | `/api/v1/reports` | 报告列表 | ❌ |
| GET | `/api/v1/reports/{id}` | 报告详情 | ❌ |
| GET | `/api/v1/subscriptions` | 订阅列表 | ❌ |
| POST | `/api/v1/subscriptions` | 添加订阅 | ❌ |
| DELETE | `/api/v1/subscriptions/{id}` | 删除订阅 | ❌ |
| GET | `/health` | 健康检查 | ❌ |

---

## 测试

```bash
pytest tests/ -v --cov=app
# => 63+ passed, 覆盖率 >85%
```

| 测试文件 | 覆盖内容 |
|----------|----------|
| `test_agent_logic.py` | Agent 编排、消息提取、来源解析 |
| `test_github_tools.py` | GitHub/搜索/RSS 工具、缓存键 |
| `test_cache.py` | Redis 缓存读写、异常处理 |
| `test_chat_memory.py` | 聊天记忆生命周期 |
| `test_reports.py` | 报告 CRUD |
| `test_rss.py` | RSS 解析 |
| `test_health.py` | 健康检查 API |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **AI 框架** | LangChain (ReAct Agent) + ChatOpenAI |
| **LLM** | OpenAI GPT-4o / 兼容 API |
| **后端框架** | FastAPI (ASGI, async/await) |
| **数据库** | MySQL 8 (SQLAlchemy async + aiomysql) |
| **缓存** | Redis 7 (聊天记忆 + 数据缓存) |
| **认证** | JWT (python-jose, HS256) + scrypt |
| **前端** | React 18 + Vite + TailwindCSS |
| **部署** | Docker Compose / Nginx + Let's Encrypt |
| **测试** | pytest + pytest-asyncio + respx |
