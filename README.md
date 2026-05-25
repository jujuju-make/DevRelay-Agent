# DevRelay-Agent

面向开发者的 **GitHub + 技术博客** 追踪 Agent，基于异步 FastAPI、LangChain ReAct 与 Redis/MySQL。

## 功能概览

| 能力 | 说明 |
|------|------|
| ReAct Agent | 自动调用工具：commits、读文件、RSS、全网搜索、读网页、MySQL 归档 |
| GitHub | 最近 commit、读取 `README.md` 等仓库文件 |
| 技术博客 | RSS/Atom 订阅抓取（`fetch_rss_feed`） |
| Redis | 聊天记忆（24h）、GitHub commit 缓存（10min） |
| MySQL | 用户确认后保存技术报告 |

## 环境要求

- Python 3.11+
- MySQL 8+
- Redis / [Memurai](https://www.memurai.com/)（Windows）
- `.env` 配置文件

## 快速开始

```powershell
cd DevRelay-Agent
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env，填入 MySQL、Redis、OPENAI_API_KEY、GITHUB_TOKEN 等
python main.py
```

访问 Swagger：http://127.0.0.1:8000/docs

## API 示例

### 运行 Agent

```http
POST /api/v1/agent/run
Content-Type: application/json

{
  "query": "总结 fastapi/fastapi 最近更新，并读一下 README 要点",
  "session_id": "user-session-001",
  "repo_owner": "fastapi",
  "repo_name": "fastapi"
}
```

### 查询 RSS 博客（在 query 中提供 URL）

```json
{
  "query": "订阅 https://hnrss.org/frontpage 最近有哪些技术热点？",
  "session_id": "user-session-001"
}
```

### 列出已归档报告

```http
GET /api/v1/reports?limit=20&offset=0
```

### 报告详情

```http
GET /api/v1/reports/1
```

## 项目结构

```
app/
├── routers/      # health, agent, reports
├── services/     # agent_logic, chat_memory, cache
├── tools/        # github, rss, read_web_page
├── models/       # Report ORM
└── schemas/      # Pydantic 模型
scripts/
└── view_chat_history.py   # 终端查看 Redis 会话（中文）
```

## Redis Key 说明

| Key | TTL | 用途 |
|-----|-----|------|
| `devrelay:chat:{session_id}` | 24h | 多轮对话记忆 |
| `devrelay:commits:{owner}:{repo}:...` | 10min | GitHub commit 缓存 |

查看会话：

```powershell
.\.venv\Scripts\python.exe scripts\view_chat_history.py 你的session_id
```

## 工具列表（Agent）

- `fetch_repo_commits` — 仓库最近提交
- `read_github_file` — 读取仓库内文件（如 README.md）
- `fetch_rss_feed` — 技术博客 RSS/Atom
- `search_web` — 全网搜索（需 Serper API Key）
- `read_web_page` — 读取网页正文
- `save_to_mysql` — 归档报告（需用户明确同意）

## 许可证

课程 / 个人学习项目。
