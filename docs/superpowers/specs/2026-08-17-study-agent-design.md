# study-agent v1 设计文档

- 日期：2026-08-17
- 状态：已与用户确认设计，待审阅
- 仓库：GitHub 待建（用户创建），本地目录 `D:\ai\projects\study-agent`
- 关联项目：`rag-assiant`（作为检索工具服务，新增 `/api/retrieve` 接口）

## 1. 背景与目标

学习型项目。目标不是做产品，而是亲手实现 **Tool Calling + Agent Loop + 状态**，为后续进阶打基础。

- 用户基于自己的课程资料提问，Agent 判断是否需要调用工具，检索资料或生成练习题，最后给出回答。
- 刻意**不用** LangGraph / CrewAI 等框架，手写最小 agent loop。
- 网页界面展示 Agent 的每一步工具调用，让"判断 → 调工具 → 拿结果 → 再判断"可见。

## 2. 范围

### v1 做

- 手写 agent loop（最多 5 轮）
- 两个工具：`search_notes`（检索型）、`make_quiz`（动作型）
- FastAPI 后端 + Vue 3 前端（单页，聊天 + 可展开的 Agent 过程）
- DeepSeek 对话（OpenAI 兼容 `tools` 参数）
- 错误处理：工具异常、参数解析失败、超轮数
- 测试问题集验证

### v1 不做（第二阶段再补）

- SQLite 保存题目/笔记
- 判分
- 流式回答
- 部署上线
- 用户登录/鉴权

## 3. 架构

```
浏览器 (Vue 3)
  → study-agent FastAPI :8084
      → Agent Loop（手写）
          ├─ DeepSeek API（带 tools 参数）
          ├─ 工具① search_notes → HTTP 调 rag-assiant :8083 /api/retrieve
          └─ 工具② make_quiz → 调 DeepSeek 生成题目
```

- study-agent 与 rag-assiant 通过 HTTP 通信（工具即服务）
- 本地开发需同时运行两个后端（8083 rag-assiant、8084 study-agent）

## 4. 目录结构

```
D:\ai\projects\study-agent\
├── app.py            # FastAPI 入口：POST /api/chat（返回 answer + trace）
├── agent.py          # 手写 agent loop + 工具注册表 ★学习核心
├── tools.py          # search_notes / make_quiz 两个真实工具
├── llm.py            # DeepSeek 调用封装（支持 tools 参数）
├── requirements.txt
├── .env              # DeepSeek key、RAG_SERVICE_URL、RAG_DOC_ID
└── frontend/         # Vue 3 + Vite 单页
    ├── src/App.vue       # 聊天界面 + Agent 过程折叠区
    ├── src/api.js        # POST /api/chat
    └── vite.config.js    # 代理 /api → localhost:8084
```

## 5. Agent Loop（核心流程）

```
用户问题
  → messages = [system, user]
  → 循环（最多 5 轮）：
      ① messages + tools → DeepSeek
      ② 返回带 tool_calls？
          是 → 把模型消息加进 messages
               逐个执行工具（解析参数 → call_tool → 结果字符串）
               把 role=tool 消息（带 tool_call_id）加回 messages
               继续循环
          否 → 返回最终答案
  → 超轮数：强制结束并说明
```

关键点：

- `tool_calls` 是模型的"意图"，由程序执行
- `tool` 消息必须带 `tool_call_id` 对应模型的调用
- `messages` 就是 Agent 的状态，贯穿整个循环
- 工具参数是模型生成的 JSON，需容错

## 6. 工具定义

### 工具① search_notes（检索型）

```json
{
  "name": "search_notes",
  "description": "从学习资料中检索相关内容，回答基于资料的学习问题时调用",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "检索关键词或问题" },
      "top_k": { "type": "integer", "description": "返回片段数，默认 3" }
    },
    "required": ["query"]
  }
}
```

实现：HTTP 调 `rag-assiant /api/retrieve`，返回片段原文列表（拼接成字符串作为工具结果）。

### 工具② make_quiz（动作型）

```json
{
  "name": "make_quiz",
  "description": "根据主题生成一道练习题，含题目、答案和解析",
  "parameters": {
    "type": "object",
    "properties": {
      "topic": { "type": "string", "description": "题目主题，如'TCP 三次握手'" }
    },
    "required": ["topic"]
  }
}
```

实现：调 DeepSeek 生成 JSON 格式题目（不存库，第一版纯生成）。

## 7. rag-assiant 改动

新增接口 `POST /api/retrieve`（约 15 行）：

- 入参：`{"question": str, "doc_id": str, "top_k": int}`
- 逻辑：复用 `get_collection` + `collection.query`
- 出参：`{"code": 200, "data": [{"content": 片段, "source": 路径}, ...]}`
- 不生成回答，保持"纯检索工具"的职责

## 8. 前端

- 复用 Vue 3 + Vite（不在此学新前端技术）
- 单页：输入框 + 消息区 + 可展开的"Agent 过程"
- Agent 过程每步显示：`调用了 search_notes(计算机网络第三章) → 拿到 3 个片段`
- 过程记录由后端 `/api/chat` 返回的 `trace` 数组提供

## 9. 错误处理（第一版）

- rag-assiant 未启动 / 检索失败 → 工具返回错误说明，Agent 如实告知用户
- 模型返回的参数 JSON 解析失败 → 把错误作为 tool 结果返回，提示模型重试（最多 1 次）
- 超过 5 轮 → 强制结束并说明"已达到最大轮数"
- 前端请求失败 → 显示错误信息，不静默

## 10. 验证标准（怎么算跑通）

测试问题集：

1. "计算机网络第三章讲了什么重点？" → 应调用 `search_notes`
2. "根据 TCP 三次握手出一道练习题" → 应调用 `make_quiz`
3. "你好" → **不应**调用任何工具
4. 网页界面能看到 Agent 过程记录
5. 工具调用失败时，界面能看到合理错误

## 11. 第二阶段（暂不做，先记录）

- SQLite 保存题目 / 笔记
- 判分（提交答案 → 判断对错 → 解析）
- 流式回答（SSE）
- 部署上线（Docker / 云服务器）

## 12. 关键决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| Agent 实现方式 | 手写 loop | 最大学习价值，框架留到以后对比 |
| 资料来源 | rag-assiant 作为检索工具服务 | 复用已做项目，学习"工具即服务" |
| 出题工具 | 第一版纯生成 | 控制范围，数据库留第二阶段 |
| 交互 | 网页 + Agent 过程展示 | 可见的学习反馈 |
| 前端技术 | 复用 Vue 3 | 不引入新学习负担 |
