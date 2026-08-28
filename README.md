# study-agent 学习助手 Agent

一个基于自己学习资料回答问题、出练习题的个人 AI 助手。

## 功能

- **基于资料回答**：把学习资料拖进 `docs/` 文件夹（或运行 `watch_docs.py` 自动监听），提问时 Agent 会先从本地向量库检索相关内容，再组织回答
- **出练习题**：输入主题，让模型生成一道题（含答案和解析）
- **对话记忆**：所有对话存在 SQLite 数据库里，刷新页面记录还在
- **流式输出**：回答一个字一个字蹦出来（SSE + 打字机）
- **Agent 过程**：回答下方可以展开看它调用了哪些工具、检索到什么片段

## 技术栈

- 后端：Python + FastAPI
- 前端：Vue 3 + Vite
- 大模型：DeepSeek（deepseek-chat）
- 向量库：ChromaDB（存资料的向量，用于相似度检索）
- 数据库：SQLite（存对话历史）
- 向量化模型：BAAI/bge-small-zh-v1.5（本地运行，把文字变成向量）

## 快速开始

需要：Python 3.x、Node.js

1. 安装后端依赖：`pip install -r requirements.txt`
2. 安装前端依赖：`cd frontend && npm install`
3. 配置密钥：复制 `.env.example` 为 `.env`，填入 `LLM_API_KEY`
4. 启动（二选一）：
   - 双击 `启动后端.bat` 和 `启动前端.bat`
   - 或分别运行 `python app.py`（8084）和 `cd frontend && npm run dev`（5173）
5. 打开 http://localhost:5173/

添加资料：把 PDF/DOCX/TXT 拖进 `docs/`，然后运行 `python ingest.py`（或先启动 `python watch_docs.py` 实现自动入库）。

## 项目结构

| 文件 | 作用 |
|---|---|
| `agent.py` | Agent 大脑：工具名片、通讯录、接单员、主循环 |
| `llm.py` | 调 DeepSeek 大模型（含流式版） |
| `tools.py` | 工具实现：search_notes（查资料）、make_quiz（出题） |
| `rag/` | RAG 引擎：读文档、切块、向量库增删查 |
| `db.py` | SQLite 操作：建表、存消息、读历史 |
| `ingest.py` | 投件箱入库：把 docs/ 文档切块存进向量库 |
| `watch_docs.py` | 自动监听 docs/，新文件拖入即入库 |
| `app.py` | 后端入口：/api/chat（流式）、/api/history |
| `frontend/` | Vue 3 前端 |

## 常见问题

- 第一次启动为什么慢？启动时要加载本地向量化模型（bge），约 30 秒。
