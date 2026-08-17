# study-agent

学习助理 Agent：基于课程资料回答问题、根据主题出题。核心是手写的 Agent Loop（Tool Calling + 消息循环），不用框架。

## 架构

- study-agent 后端（:8084）：手写 agent loop，调 DeepSeek（OpenAI 兼容 `tools` 参数）
- `search_notes` 工具：调 rag-assiant 的 `/api/retrieve` 检索资料
- `make_quiz` 工具：调 DeepSeek 出题
- 前端（:5173）：Vue 3 单页，展示回答 + Agent 过程

## 目录

```
study-agent/
├── app.py      # FastAPI 入口：POST /api/chat（返回 answer + trace）
├── agent.py    # 手写 agent loop + 工具注册表 ★学习核心
├── tools.py    # search_notes / make_quiz
├── llm.py      # DeepSeek 调用封装（含 tools 参数）
└── frontend/   # Vue 3 + Vite 单页
```

## 运行

1. 复制 `.env.example` 为 `.env` 并填写 DeepSeek key、`RAG_DOC_ID`
2. 启动 rag-assiant（:8083）——它是检索工具服务
3. 启动本后端：

```bash
.venv\Scripts\python app.py
```

4. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，输入学习问题即可。

## 测试

```bash
.venv\Scripts\python -m pytest tests/ -v
```

Agent loop 的测试用假 chat 响应，不调用真实 API。
