import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL")
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


def _post(messages, tools=None, stream=False):
    """发送请求 + 指数退避重试（网络错误 / 429 / 5xx 会重试 3 次）。"""
    payload = {"model": MODEL, "messages": messages}
    if stream:
        payload["stream"] = True
    if tools:
        payload["tools"] = tools

    for attempt in range(3):
        try:
            resp = requests.post(
                f"{BASE_URL}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                timeout=60,
                stream=stream,
            )
            if resp.status_code >= 400:
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt)          # 指数退避：1s、2s
                    continue
                raise RuntimeError(f"DeepSeek API {resp.status_code}: {resp.text[:200]}")
            return resp
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"请求 DeepSeek 失败: {e}")

    raise RuntimeError("重试 3 次仍失败")


def chat(messages, tools=None):
    """调用 DeepSeek 对话接口。tools 为函数定义列表，模型可能返回 tool_calls。"""
    return _post(messages, tools).json()


def chat_stream(messages, tools=None):
    """流式版 chat：用 stream=True，逐个 yield 回答的文字片段。"""
    resp = _post(messages, tools, stream=True)
    for line in resp.iter_lines():
        if not line or not line.startswith(b"data:"):
            continue
        data = line[5:].strip()
        if data == b"[DONE]":
            break
        try:
            delta = json.loads(data)["choices"][0]["delta"]
        except Exception:
            continue
        content = delta.get("content")
        if content:
            yield content