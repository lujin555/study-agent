# study-agent v1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个手写 Agent 循环的学习助理：基于课程资料回答问题（`search_notes` 工具）、根据主题出练习题（`make_quiz` 工具），网页界面展示每一步工具调用。

**Architecture:** FastAPI 后端（:8084）运行手写 agent loop，循环内调 DeepSeek（OpenAI 兼容 `tools` 参数）；`search_notes` 通过 HTTP 调用 rag-assiant（:8083）新增的 `/api/retrieve` 纯检索接口；前端 Vue 3 + Vite 单页（:5173）展示回答与工具过程。

**Tech Stack:** Python 3.10+ / FastAPI / Uvicorn / requests / pytest / Vue 3 / Vite

## Global Constraints

- 手写 agent loop，禁止引入 LangChain / LangGraph / CrewAI 等框架
- DeepSeek 使用 OpenAI 兼容接口（`/chat/completions` + `tools` 参数）
- 端口约定：rag-assiant 8083、study-agent 8084、前端 5173
- `.env` 不入库（`.gitignore` 已配置）；`.env.example` 入库
- 后端一律用 pytest 测试；agent loop 测试用假 chat，禁止真实调用 API
- 每个任务结束必须 commit

---

### Task 1: 项目骨架 + pytest

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Produces: pytest 可运行的后端测试骨架

- [ ] **Step 1: 写依赖清单 `requirements.txt`**

```text
fastapi>=0.100.0
uvicorn>=0.23.2
requests>=2.28.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pytest>=7.0.0
httpx>=0.27.0
```

- [ ] **Step 2: 写 `.env.example`**

```text
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
RAG_SERVICE_URL=http://localhost:8083
RAG_DOC_ID=
```

- [ ] **Step 3: 写冒烟测试 `tests/test_smoke.py`**

```python
def test_smoke():
    assert 1 + 1 == 2
```

- [ ] **Step 4: 安装依赖并跑测试**

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/ -v
```

Expected: `test_smoke` PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example tests/test_smoke.py
git commit -m "chore: 项目骨架 + pytest"
```

---

### Task 2: llm.py —— DeepSeek 调用封装

**Files:**
- Create: `llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Produces: `chat(messages: list, tools: list | None = None) -> dict`（返回 OpenAI 风格响应 dict）

- [ ] **Step 1: 写失败测试 `tests/test_llm.py`**

```python
import llm


class FakeResp:
    def __init__(self, status_code, json_data, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


def test_chat_sends_tools(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    result = llm.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    assert result["choices"][0]["message"]["content"] == "ok"
    assert captured["json"]["tools"] == [{"type": "function"}]


def test_chat_raises_on_error(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return FakeResp(401, {}, text='{"error": "bad key"}')

    monkeypatch.setattr(llm.requests, "post", fake_post)
    try:
        llm.chat([{"role": "user", "content": "hi"}])
        assert False, "应该抛出 RuntimeError"
    except RuntimeError as e:
        assert "401" in str(e)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm'`

- [ ] **Step 3: 写实现 `llm.py`**

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL")
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


def chat(messages, tools=None):
    """调用 DeepSeek 对话接口。tools 为函数定义列表，模型可能返回 tool_calls。"""
    payload = {"model": MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek API {resp.status_code}: {resp.text[:200]}")
    return resp.json()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_llm.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add llm.py tests/test_llm.py
git commit -m "feat: DeepSeek 调用封装（含 tools 参数）"
```

---

### Task 3: tools.py —— 两个真实工具

**Files:**
- Create: `tools.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `llm.chat(messages, tools=None) -> dict`
- Produces: `search_notes(query: str, top_k: int = 3) -> str`、`make_quiz(topic: str) -> str`

- [ ] **Step 1: 写失败测试 `tests/test_tools.py`**

```python
import tools


class FakeResp:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_search_notes_ok(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResp(200, {"code": 200, "data": [
            {"content": "三次握手是 TCP 建立连接的过程", "source": "data/test.pdf"},
        ]})

    monkeypatch.setattr(tools.requests, "post", fake_post)
    result = tools.search_notes("三次握手")
    assert "三次握手" in result
    assert "data/test.pdf" in result


def test_search_notes_empty(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResp(200, {"code": 200, "data": []})

    monkeypatch.setattr(tools.requests, "post", fake_post)
    assert tools.search_notes("不存在的内容") == "没有检索到相关内容。"


def test_search_notes_error(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        raise ConnectionError("backend down")

    monkeypatch.setattr(tools.requests, "post", fake_post)
    assert "检索失败" in tools.search_notes("xxx")


def test_make_quiz(monkeypatch):
    def fake_chat(messages, tools=None):
        return {"choices": [{"message": {"content": '{"question": "三次握手有几步？"}'}}]}

    monkeypatch.setattr(tools, "chat", fake_chat)
    result = tools.make_quiz("TCP 三次握手")
    assert "三次握手" in result
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: 写实现 `tools.py`**

```python
import os
import requests
from dotenv import load_dotenv
from llm import chat

load_dotenv()

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8083")
RAG_DOC_ID = os.getenv("RAG_DOC_ID", "")


def search_notes(query: str, top_k: int = 3) -> str:
    """检索型工具：从 rag-assiant 获取相关片段。"""
    try:
        resp = requests.post(
            f"{RAG_SERVICE_URL}/api/retrieve",
            json={"question": query, "doc_id": RAG_DOC_ID, "top_k": top_k},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        chunks = data.get("data", [])
        if not chunks:
            return "没有检索到相关内容。"
        parts = [f"[片段{i + 1}] {c['content']}（来源：{c['source']}）" for i, c in enumerate(chunks)]
        return "\n\n".join(parts)
    except Exception as e:
        return f"检索失败: {e}"


def make_quiz(topic: str) -> str:
    """动作型工具：让 DeepSeek 生成一道练习题。"""
    prompt = (
        f"请根据主题「{topic}」出一道练习题，只输出 JSON："
        '{"question": "题目", "answer": "答案", "explain": "解析"}'
    )
    result = chat([{"role": "user", "content": prompt}])
    return result["choices"][0]["message"]["content"]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_tools.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: search_notes / make_quiz 两个工具"
```

---

### Task 4: agent.py —— 手写 Agent Loop（核心）

**Files:**
- Create: `agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `llm.chat`、`tools.search_notes`、`tools.make_quiz`
- Produces: `run_agent(question: str, max_rounds: int = 5) -> dict`，返回 `{"answer": str, "trace": [{"tool": str, "arguments": dict, "result_preview": str}]}`；导出 `TOOLS` 和 `call_tool(name, args)`

- [ ] **Step 1: 写失败测试 `tests/test_agent.py`**

```python
import agent


def fake_response(content=None, tool_calls=None):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}]}


def make_tool_call(tool_id, name, args_json):
    return {
        "id": tool_id,
        "type": "function",
        "function": {"name": name, "arguments": args_json},
    }


def test_agent_calls_tool_then_answers(monkeypatch):
    responses = [
        fake_response(tool_calls=[make_tool_call("call_1", "search_notes", '{"query": "三次握手"}')]),
        fake_response(content="三次握手是 TCP 建立连接的过程。"),
    ]
    calls = {"n": 0}

    def fake_chat(messages, tools=None):
        r = responses[calls["n"]]
        calls["n"] += 1
        return r

    monkeypatch.setattr(agent, "chat", fake_chat)
    result = agent.run_agent("三次握手是什么？")

    assert "三次握手" in result["answer"]
    assert len(result["trace"]) == 1
    assert result["trace"][0]["tool"] == "search_notes"
    assert result["trace"][0]["arguments"] == {"query": "三次握手"}


def test_agent_no_tool_when_not_needed(monkeypatch):
    def fake_chat(messages, tools=None):
        return fake_response(content="你好！有什么可以帮你？")

    monkeypatch.setattr(agent, "chat", fake_chat)
    result = agent.run_agent("你好")

    assert result["answer"] == "你好！有什么可以帮你？"
    assert result["trace"] == []


def test_agent_max_rounds(monkeypatch):
    def fake_chat(messages, tools=None):
        return fake_response(tool_calls=[make_tool_call("call_x", "make_quiz", '{"topic": "TCP"}')])

    monkeypatch.setattr(agent, "chat", fake_chat)
    result = agent.run_agent("一直调工具", max_rounds=2)

    assert "最大轮数" in result["answer"]
    assert len(result["trace"]) == 2


def test_agent_bad_arguments_json(monkeypatch):
    responses = [
        fake_response(tool_calls=[make_tool_call("call_1", "search_notes", "not-json")]),
        fake_response(content="我换个方式回答。"),
    ]
    calls = {"n": 0}

    def fake_chat(messages, tools=None):
        r = responses[calls["n"]]
        calls["n"] += 1
        return r

    monkeypatch.setattr(agent, "chat", fake_chat)
    result = agent.run_agent("查一下")

    assert len(result["trace"]) == 1
    assert "工具执行失败" in result["trace"][0]["result_preview"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent'`

- [ ] **Step 3: 写实现 `agent.py`**

```python
import json
from llm import chat
from tools import search_notes, make_quiz

SYSTEM_PROMPT = (
    "你是学习助理。回答基于资料的学习问题前，先调用 search_notes 查资料；"
    "用户要练习题时，调用 make_quiz。其他情况直接回答。用中文。"
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "从学习资料中检索相关内容，回答基于资料的学习问题时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或问题"},
                    "top_k": {"type": "integer", "description": "返回片段数，默认 3"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_quiz",
            "description": "根据主题生成一道练习题，含题目、答案和解析",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "题目主题，如'TCP 三次握手'"},
                },
                "required": ["topic"],
            },
        },
    },
]

TOOL_IMPL = {"search_notes": search_notes, "make_quiz": make_quiz}


def call_tool(name: str, args: dict) -> str:
    """把模型想调的工具路由到真实函数。"""
    if name not in TOOL_IMPL:
        return f"未知工具: {name}"
    try:
        return TOOL_IMPL[name](**args)
    except Exception as e:
        return f"工具执行失败: {e}"


def run_agent(question: str, max_rounds: int = 5) -> dict:
    """手写 agent loop。messages 是状态，贯穿整个循环。"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    trace = []

    for _ in range(max_rounds):
        resp = chat(messages, tools=TOOLS)
        msg = resp["choices"][0]["message"]

        if msg.get("tool_calls"):
            messages.append(msg)  # 模型消息（含调用意图）进状态
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = call_tool(name, args)
                trace.append({"tool": name, "arguments": args, "result_preview": result[:100]})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            continue

        return {"answer": msg["content"], "trace": trace}

    return {"answer": "已达到最大轮数，强制结束。", "trace": trace}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_agent.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: 手写 agent loop（tool calling + 消息循环）"
```

---

### Task 5: app.py —— FastAPI 接口

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `agent.run_agent`
- Produces: `POST /api/chat`，入参 `{"question": str}`，出参 `{"code": 200, "data": {"answer", "trace"}}`

- [ ] **Step 1: 写失败测试 `tests/test_app.py`**

```python
from fastapi.testclient import TestClient
import app


client = TestClient(app.app)


def test_chat_ok(monkeypatch):
    monkeypatch.setattr(app, "run_agent", lambda question: {
        "answer": "测试回答",
        "trace": [{"tool": "search_notes", "arguments": {"query": "x"}, "result_preview": "片段"}],
    })
    resp = client.post("/api/chat", json={"question": "测试"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["answer"] == "测试回答"
    assert data["trace"][0]["tool"] == "search_notes"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: 写实现 `app.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import run_agent

app = FastAPI(title="study-agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    return {"code": 200, "data": run_agent(req.question)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: FastAPI /api/chat 接口"
```

---

### Task 6: rag-assiant 增加 /api/retrieve 纯检索接口

**Files:**
- Modify: `D:\ai\projects\rag-assiant\main.py`

**Interfaces:**
- Produces: `POST /api/retrieve`，入参 `{"question": str, "doc_id": str, "top_k": int}`，出参 `{"code": 200, "data": [{"content": str, "source": str}]}`

- [ ] **Step 1: 在 `main.py` 的 `ChatRequest` 后加检索请求模型**

```python
class RetrieveRequest(BaseModel):
    question: str
    doc_id: str = ""
    top_k: int = 3
```

- [ ] **Step 2: 在 `main.py` 加 `/api/retrieve` 路由（放在 `/api/chat` 后面）**

```python
@app.post("/api/retrieve")
async def retrieve(req: RetrieveRequest):
    """纯检索接口：给 Agent 当工具用，不生成回答。"""
    collection_name = None
    if req.doc_id and req.doc_id in documents:
        collection_name = documents[req.doc_id]["collection_name"]
    elif documents:
        collection_name = list(documents.values())[0]["collection_name"]
    if not collection_name:
        return {"code": 200, "data": []}

    collection = get_collection(collection_name)
    if collection is None:
        return {"code": 200, "data": []}

    results = collection.query(query_texts=[req.question], n_results=req.top_k)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    data = []
    for i, content in enumerate(docs):
        data.append({
            "content": content,
            "source": metas[i].get("source", "") if i < len(metas) else "",
        })
    return {"code": 200, "data": data}
```

- [ ] **Step 3: 验证（启动 rag-assiant 后端）**

```bash
cd D:\ai\projects\rag-assiant
.venv\Scripts\python main.py
```

另开终端：

```bash
curl.exe -s -X POST http://localhost:8083/api/retrieve -H "Content-Type: application/json" -d "{\"question\":\"周杰伦出生于哪一年\",\"top_k\":2}"
```

Expected: 返回 `{"code":200,"data":[...]}`，data 非空且每项含 `content` 和 `source`

- [ ] **Step 4: 提交（在 rag-assiant 仓库）**

```bash
cd D:\ai\projects\rag-assiant
git add main.py
git commit -m "feat: 新增 /api/retrieve 纯检索接口（供 Agent 工具调用）"
git push
```

---

### Task 7: 前端 —— Vue 3 + Vite 单页

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/api.js`
- Create: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `POST /api/chat`（经 Vite 代理到 :8084）

- [ ] **Step 1: `frontend/package.json`**

```json
{
  "name": "study-agent-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "vue": "^3.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.0",
    "vite": "^8.0.0"
  }
}
```

- [ ] **Step 2: `frontend/vite.config.js`**

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8084',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: `frontend/index.html`**

```html
<!doctype html>
<html lang="zh">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>study-agent</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 4: `frontend/src/main.js`**

```js
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

- [ ] **Step 5: `frontend/src/api.js`**

```js
const BASE_URL = "/api";

export async function askAgent(question) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return res.json();
}
```

- [ ] **Step 6: `frontend/src/App.vue`**

```vue
<template>
  <div class="app">
    <h2>学习助手 Agent</h2>
    <div class="messages">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <div class="bubble">{{ m.content }}</div>
        <details v-if="m.trace && m.trace.length" class="trace">
          <summary>Agent 过程（{{ m.trace.length }} 步）</summary>
          <div v-for="(t, j) in m.trace" :key="j" class="step">
            <code>调用了 {{ t.tool }}({{ JSON.stringify(t.arguments) }})</code>
            <p>结果：{{ t.result_preview }}</p>
          </div>
        </details>
      </div>
      <div v-if="loading" class="msg assistant">
        <div class="bubble">思考中...</div>
      </div>
    </div>
    <form @submit.prevent="send">
      <input v-model="question" placeholder="输入学习问题，如：计算机网络第三章讲了什么重点？" />
      <button :disabled="loading || !question.trim()">发送</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { askAgent } from "./api.js";

const question = ref("");
const messages = ref([]);
const loading = ref(false);

async function send() {
  const q = question.value.trim();
  if (!q || loading.value) return;
  loading.value = true;
  messages.value.push({ role: "user", content: q });
  question.value = "";
  try {
    const res = await askAgent(q);
    if (res.code === 200) {
      messages.value.push({ role: "assistant", content: res.data.answer, trace: res.data.trace });
    } else {
      messages.value.push({ role: "assistant", content: res.detail || "出错了" });
    }
  } catch (e) {
    messages.value.push({ role: "assistant", content: "请求失败，请确认后端已启动" });
  }
  loading.value = false;
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: #f5f6f8; }
.app { max-width: 720px; margin: 24px auto; padding: 16px; background: #fff; border-radius: 10px; }
h2 { margin-bottom: 12px; font-size: 18px; }
.messages { min-height: 320px; max-height: 60vh; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.msg { margin-bottom: 10px; }
.bubble { padding: 8px 12px; border-radius: 8px; line-height: 1.6; white-space: pre-wrap; }
.msg.user .bubble { background: #4a90d9; color: #fff; }
.msg.assistant .bubble { background: #f0f0f0; }
.trace { margin-top: 6px; font-size: 12px; color: #666; }
.step { margin: 4px 0; padding: 6px 8px; background: #fafafa; border-radius: 6px; }
.step p { margin-top: 2px; }
form { display: flex; gap: 8px; }
input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; }
button { padding: 10px 18px; border: none; background: #4a90d9; color: #fff; border-radius: 6px; cursor: pointer; }
button:disabled { opacity: 0.5; }
</style>
```

- [ ] **Step 7: 启动前端并验证**

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，确认页面能打开、输入框和按钮正常。

- [ ] **Step 8: Commit**

```bash
cd D:\ai\projects\study-agent
git add frontend/
git commit -m "feat: Vue 前端单页（聊天 + Agent 过程展示）"
```

---

### Task 8: 端到端验证 + README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: Task 1-7 全部产物

- [ ] **Step 1: 启动全部服务**

```bash
# 终端1：rag-assiant 后端（:8083）
cd D:\ai\projects\rag-assiant && .venv\Scripts\python main.py

# 终端2：study-agent 后端（:8084）
cd D:\ai\projects\study-agent && .venv\Scripts\python app.py

# 终端3：前端（:5173）
cd D:\ai\projects\study-agent\frontend && npm run dev
```

- [ ] **Step 2: 跑测试问题集（在网页上或 curl）**

```bash
curl.exe -s -X POST http://localhost:8084/api/chat -H "Content-Type: application/json" -d "{\"question\":\"你好\"}"
curl.exe -s -X POST http://localhost:8084/api/chat -H "Content-Type: application/json" -d "{\"question\":\"计算机网络第三章讲了什么重点？\"}"
curl.exe -s -X POST http://localhost:8084/api/chat -H "Content-Type: application/json" -d "{\"question\":\"根据 TCP 三次握手出一道练习题\"}"
```

Expected：
- "你好" → 不调工具，直接回答
- 资料问题 → trace 里有 `search_notes`
- 出题 → trace 里有 `make_quiz`

- [ ] **Step 3: 写 `README.md`**

```markdown
# study-agent

学习助理 Agent：基于课程资料回答问题、根据主题出题。核心是手写的 Agent Loop（Tool Calling + 消息循环），不用框架。

## 架构

- study-agent 后端（:8084）：手写 agent loop，调 DeepSeek
- search_notes 工具：调 rag-assiant 的 /api/retrieve 检索资料
- make_quiz 工具：调 DeepSeek 出题
- 前端（:5173）：Vue 3 单页，展示回答 + Agent 过程

## 运行

1. 复制 `.env.example` 为 `.env` 并填写 DeepSeek key
2. 启动 rag-assiant（:8083）——它是检索工具服务
3. `python app.py` 启动本后端（:8084）
4. `cd frontend && npm install && npm run dev` 启动前端

## 测试

```bash
.venv\Scripts\python -m pytest tests/ -v
```
```

- [ ] **Step 4: 跑全部测试 + 提交**

```bash
.venv\Scripts\python -m pytest tests/ -v
git add README.md
git commit -m "docs: README + 端到端验证"
git push
```

Expected: 全部测试 PASS，推送成功
