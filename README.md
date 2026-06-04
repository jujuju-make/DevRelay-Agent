# DevRelay-Agent — AI 驱动的开发者资讯聚合助手

> 一个基于 **LangChain ReAct + FastAPI** 的 AI Agent，自动追踪 GitHub 仓库更新和技术博客，生成结构化报告并归档。
>
> 简历关键词：`AI Agent` `LangChain` `FastAPI` `异步架构` `Redis/MySQL` `Docker` `JWT 认证`

**在线体验：** [http://43.138.144.162:8000](http://43.138.144.162:8000)
**API 文档：** [http://43.138.144.162:8000/docs](http://43.138.144.162:8000/docs)

---

## 📌 项目亮点

| 维度 | 说明 |
|------|------|
| **AI Agent** | 基于 LangChain ReAct 模式，LLM 自主决策调用 7 种工具完成复杂任务 |
| **多源聚合** | GitHub API + RSS/Atom 订阅 + 全网搜索 + 网页抓取，一站式追踪技术动态 |
| **异步架构** | 全链路 `async/await`（httpx、SQLAlchemy async、Redis），支持高并发 |
| **智能归档** | 自动判断回答质量 → 暂存 Redis → 前端确认 → 持久化到 MySQL |
| **自动日报** | 定时任务拉取 commits → LLM 总结 → 自动归档，零人工介入 |
| **用户认证** | JWT 登录/注册，前端路由守卫，用户隔离 |
| **容器化** | Docker Compose 一键启动 MySQL + Redis + 应用，开箱即用 |
| **测试覆盖** | 63+ 个测试用例（pytest + mock），覆盖全部核心逻辑，无外部依赖 |

---

## 🏗 架构设计

```
                         ┌──────────────────────────────────┐
                         │          用户 / 浏览器             │
                         │  Login → JWT → App (React SPA)   │
                         └────────────┬─────────────────────┘
                                      │
                         ┌────────────▼─────────────────────┐
                         │    FastAPI (ASGI, Uvicorn)        │
                         │    /api/v1/auth/*  (注册/登录)    │
                         │    /api/v1/agent/run  (AI 对话)   │
                         │    /api/v1/reports/*  (报告查询)  │
                         │    /api/v1/subscriptions/* (订阅) │
                         │    /  → StaticFiles (前端 SPA)    │
                         └────────────┬─────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
   ┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
   │  LangChain ReAct     │ │   Redis 缓存     │ │     MySQL 8          │
   │  Agent (7 tools)     │ │  · 聊天记忆 24h  │ │  · users (用户表)    │
   │  · ChatOpenAI (LLM)  │ │  · Commit 10min  │ │  · reports (报告)    │
   │  · 自主思考+工具调用  │ │  · 待归档暂存10m │ │  · subscriptions(订阅)│
   └──────┬──────┬───────┘ └─────────────────┘ └─────────────────────┘
          │      │
   ┌──────┘      └──────┐
   ▼                     ▼
┌──────────────┐  ┌──────────────────┐
│  GitHub API   │  │  外部数据源       │
│ · commits    │  │ · RSS/Atom 订阅  │
│ · 文件读取   │  │ · Serper 搜索    │
│ · diff 分析  │  │ · 网页抓取       │
└──────────────┘  └──────────────────┘
```

### 🔐 认证流程

```
用户注册/登录 → 后端签发 JWT (python-jose, HS256, 8h 过期)
     ↓
前端 localStorage 存储 token → 每次 API 请求附带 Bearer Token
     ↓
FastAPI Depends(get_current_user) → 解析 token → 返回用户信息
     ↓
未登录 → 显示 LoginPage
已登录 → 显示主界面 (App)
Token 过期 → 自动跳转登录页
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

- **ReAct 而非纯 Function Calling**：LangChain 的 ReAct 让 LLM 边思考边调用工具，适合需要多步推理的追踪场景
- **异步全链路**：httpx、aiomysql、redis asyncio，避免 IO 阻塞
- **双层缓存**：Redis 缓存 commit（10min）减少 API 调用 + 聊天记忆（24h）支持多轮对话
- **归档工作流**：Agent 回答 → 自动判断质量 → Redis 暂存 → 前端确认 → MySQL 持久化
- **JWT 无状态认证**：python-jose 签发/验证，无需 session 存储
- **测试隔离**：所有外部请求用 respx + AsyncMock 模拟，测试无需真实 API

---

## 🤖 关键 Prompt 与 Vibe 思路

### System Prompt（指导 Agent 行为）

项目使用 LangChain ReAct 的 `system_prompt` 参数注入核心指令：

```python
SYSTEM_PROMPT = """你是 DevRelay，一名帮助开发者追踪 GitHub 仓库动态与技术博客/资讯的助手。

请使用 ReAct 思路完成任务：先思考需要什么信息，再调用工具，
根据工具返回继续推理，直到能给出完整回答。

工具使用策略：
1. 涉及开源项目「最近更新、commit、改动」→ fetch_repo_commits
2. 需要 README、文档或源码内容 → read_github_file
3. 追踪技术博客/资讯 RSS → fetch_rss_feed
4. 信息不足、版本说明、社区评价 → search_web + read_web_page
5. 分析代码底层逻辑 → review_commit_diff（检查核心逻辑、
   Pydantic Model / Schema 变更、安全风险、整体影响）
6. 完成高质量报告后询问用户是否归档 → save_to_mysql
   标题必须是对内容的一句精炼总结（10~30 字）

回答要求：用中文、结构清晰；区分「仓库事实」「RSS/博客」「网上观点」；
不要编造未在工具结果中出现的信息；结合历史对话理解追问与指代。"""
```

### Vibe 设计思路

| 原则 | 说明 |
|------|------|
| **先思考再行动** | ReAct 模式下 LLM 先输出思考（Thought），再决定调用哪个工具（Action），避免盲目调用 |
| **工具优先级** | 官方 API > 搜索引擎 > 网页抓取，优先保证数据准确性 |
| **渐进式信息收集** | 先拿 commits → 不够再搜索 → 关键链接再读正文，控制成本 |
| **中文优先** | 所有回答用中文，引用英文内容时附带翻译或说明 |
| **来源可追溯** | 每次回答末尾列出所有信息来源（GitHub / RSS / Web），方便用户验证 |
| **用户确认归档** | Agent 不自动存库，先询问用户，前端显示确认按钮，用户同意后才持久化 |

### 典型对话流程

```
用户: "查看 fastapi/fastapi 的最新提交"

Agent 思考: 用户想了解 fastapi/fastapi 仓库的最近提交
  → 调用 fetch_repo_commits(owner="fastapi", repo="fastapi")
  → 拿到提交列表
  → 分析: 最近有 3 次提交，涉及文档更新和 bug 修复
  → 给出结构化回答

用户: "帮我分析最近那次 diff"
Agent 思考: 用户想看最近一次 commit 的详细 diff
  → 调用 review_commit_diff(owner="fastapi", repo="fastapi", commit_sha="xxx")
  → 分析返回的 diff 代码
  → 告知用户: 是否修改核心逻辑 / 是否改了 Schema / 是否有安全风险
```

---

## 🔄 AI 调用逻辑

### 流式 / SSE 支持

前端采用**打字机效果**模拟流式体验（而非真正的 SSE）：

```
用户发送请求 → POST /api/v1/agent/run
                     ↓
          Agent 完整执行（非流式，因为 LangChain ReAct 需要多次工具调用）
                     ↓
          后端返回完整 JSON → { answer, sources, pending_archive }
                     ↓
          前端 setInterval 逐字渲染（每次 2 字符，20ms 间隔）
                     ↓
          打字完成后显示「确认归档」按钮（如 pending_archive=true）
```

> **为何不用真正的 SSE 流式？** 因为 ReAct Agent 需要多轮工具调用（LLM → 工具 → LLM → 工具...），最终才生成完整回答，无法边执行边流式输出。如果后续切换到纯 LLM 对话（无工具调用），可以接入 SSE。

### Function Calling 机制

虽然项目使用 LangChain ReAct（而非 OpenAI 原生 Function Calling），但底层通过 LangChain 的 `create_agent` 封装了类似的能力：

```
┌──────────────────────────────────────────────┐
│  LangChain ReAct Agent                        │
│                                               │
│  1. LLM 接收 System Prompt + 工具描述 (JSON)  │
│  2. LLM 输出 Thought + Action + Action Input  │
│  3. LangChain 解析 → 调用对应工具函数         │
│  4. 工具返回结果 → 注入到 LLM 的 Observation  │
│  5. 重复 2-4 直到 LLM 输出 Final Answer       │
│                                               │
│  工具描述格式:                                 │
│  {name, description, input_schema}            │
│  由 @tool 装饰器自动生成                       │
└──────────────────────────────────────────────┘
```

关键代码路径：
- `app/services/agent_logic.py` → `run_agent()` 入口
- `app/services/agent_graph.py` → `run_agent_with_archive()` 归档逻辑封装
- `app/tools/` → 7 个工具的具体实现
- `app/routers/agent.py` → FastAPI 端点

---

## 🚀 部署步骤

### 前置要求

- Docker & Docker Compose（推荐，一键部署）
- 或 Python 3.11+ + Node.js 20+（手动部署）
- 一个域名（如需 HTTPS）

### 方式一：Docker Compose 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/jujuju-make/DevRelay-Agent.git
cd DevRelay-Agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写：
#   OPENAI_API_KEY=sk-xxx
#   GITHUB_TOKEN=ghp_xxx
#   SERPER_API_KEY=xxx      （可选，用于全网搜索）
#   JWT_SECRET_KEY=xxx       （可选，默认有开发用密钥，生产环境请修改）

# 3. 构建并启动
docker compose up -d --build

# 4. 查看日志
docker compose logs -f app

# 5. 访问
open http://localhost:8000
```

### 方式二：前后端分离部署（开发模式）

```bash
# ── 后端 ──
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate # Linux/Mac
pip install -r requirements.txt
cp .env.example .env      # 编辑配置
uvicorn main:app --reload # http://localhost:8000

# ── 前端 ──
cd frontend
npm install
npm run dev               # http://localhost:3000
                          # （已配置 /api 代理到 localhost:8000）
```

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | LLM 推理（支持 OpenAI 兼容 API） |
| `GITHUB_TOKEN` | ✅ | GitHub API 访问 |
| `JWT_SECRET_KEY` | ❌ | JWT 签名密钥（默认有开发密钥，生产环境务必修改） |
| `SERPER_API_KEY` | ❌ | 全网搜索（不填则禁用） |

---

### 生产环境部署（含 DNS / HTTPS）

本项目已部署在线体验地址 `http://43.138.144.162:8000`，以下是生产环境完整配置流程。

#### 1. DNS 解析

```bash
# 在域名 DNS 管理后台（阿里云、腾讯云、Cloudflare）添加 A 记录：
#   devrelay.example.com → 43.138.144.162
```

#### 2. HTTPS 配置（Nginx 反向代理 + Let's Encrypt）

安装 Nginx：

```bash
apt update && apt install nginx -y
```

配置 `/etc/nginx/sites-available/devrelay`：

```nginx
# HTTP → HTTPS 强制跳转
server {
    listen 80;
    server_name devrelay.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS 反向代理
server {
    listen 443 ssl http2;
    server_name devrelay.example.com;

    ssl_certificate     /etc/letsencrypt/live/devrelay.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/devrelay.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 反向代理到 FastAPI 服务（Docker 运行在宿主机 8000 端口）
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置并申请 SSL 证书：

```bash
ln -s /etc/nginx/sites-available/devrelay /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 安装 certbot 并申请证书
apt install certbot python3-certbot-nginx -y
certbot --nginx -d devrelay.example.com

# 验证自动续期
certbot renew --dry-run
```

#### 3. 安全加固

| 项目 | 建议 |
|------|------|
| `JWT_SECRET_KEY` | 用 `openssl rand -hex 32` 生成强密钥 |
| JWT 过期时间 | 设为 480 分钟（8 小时）或更短 |
| `DEBUG` | 设为 `false` |
| 数据库密码 | 修改 `docker-compose.yml` 中的默认密码 |
| Nginx | 配置 `limit_req` 防止暴力破解登录 |
| 防火墙 | 只开放 80/443 端口，关闭 3307/6380 |

#### 4. 更新前端后的快速部署

```bash
# 本地构建
cd frontend && npm run build

# 上传到服务器
scp -r dist/* root@43.138.144.162:/app/static/

# 或通过 Docker 复制
docker cp dist/. devrelay-app:/app/static/
docker restart devrelay-app
```

---

## 📦 项目结构

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
│   │   ├── base.py            # DeclarativeBase
│   │   ├── user.py            # 用户表 (username, email, password)
│   │   ├── report.py          # 报告表
│   │   └── subscription.py    # 订阅表
│   ├── schemas/               # Pydantic 请求/响应模型
│   │   ├── auth.py            # 注册/登录/Token
│   │   ├── agent.py           # Agent 请求/响应
│   │   ├── report.py          # 报告查询
│   │   └── subscription.py    # 订阅 CRUD
│   ├── routers/               # FastAPI 路由
│   │   ├── auth.py            # 注册/登录/个人信息
│   │   ├── agent.py           # Agent 对话端点
│   │   ├── reports.py         # 报告查询
│   │   ├── subscriptions.py   # 订阅管理
│   │   └── health.py          # 健康检查
│   ├── services/              # 核心业务逻辑
│   │   ├── auth.py            # JWT + 密码哈希
│   │   ├── agent_logic.py     # LangChain ReAct 编排
│   │   ├── agent_graph.py     # 归档工作流封装
│   │   ├── daily_digest.py    # 自动日报生成
│   │   ├── chat_memory.py     # Redis 聊天记忆
│   │   └── cache.py           # Redis 缓存
│   └── tools/                 # Agent 工具集
│       ├── github.py          # GitHub API 工具
│       ├── rss.py             # RSS 抓取
│       └── read_web_page.py   # 网页正文读取
├── frontend/                  # React SPA 前端
│   ├── src/
│   │   ├── contexts/AuthContext.jsx   # JWT 认证上下文
│   │   ├── pages/LoginPage.jsx        # 登录/注册页
│   │   ├── components/                # UI 组件
│   │   └── App.jsx                    # 主应用 + 路由
│   └── vite.config.js                 # 开发代理配置
├── tests/                     # pytest 测试
└── scripts/
    └── entrypoint.sh          # Docker 启动脚本
```

---

## 📄 API 一览

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

## 📊 测试质量

```bash
pytest tests/ -v --cov=app
# => 63+ passed, 覆盖率 >85%
```

| 测试文件 | 覆盖内容 |
|----------|----------|
| `test_health.py` | 健康检查 API |
| `test_github_tools.py` | GitHub/搜索/RSS 工具、缓存键 |
| `test_agent_logic.py` | Agent 编排、消息提取、来源解析 |
| `test_cache.py` | Redis 缓存读写、异常处理 |
| `test_chat_memory.py` | 聊天记忆生命周期 |
| `test_reports.py` | 报告 CRUD |
| `test_rss.py` | RSS 解析 |

---

## 📊 技术栈

| 层级 | 技术 |
|------|------|
| **AI 框架** | LangChain (ReAct Agent) + ChatOpenAI |
| **LLM** | OpenAI GPT-4o / 兼容 API |
| **后端框架** | FastAPI (ASGI, async/await) |
| **数据库** | MySQL 8 (SQLAlchemy async + aiomysql) |
| **缓存** | Redis 7 (聊天记忆 + 数据缓存) |
| **认证** | JWT (python-jose, HS256) + scrypt |
| **前端** | React 18 + Vite + TailwindCSS + Lucide |
| **部署** | Docker Compose / Nginx + Let's Encrypt |
| **测试** | pytest + pytest-asyncio + respx |
