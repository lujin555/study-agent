import json
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
def chat_stream(messages, tools=None):
    """流式版 chat：用 stream=True，逐个 yield 回答的文字片段。"""
    payload = {"model": MODEL, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools
    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60,
        stream=True,                      # 关键①：要求边收边给
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek API {resp.status_code}: {resp.text[:200]}")

    for line in resp.iter_lines():        # 关键②：一块一块地收
        if not line or not line.startswith(b"data:"):
            continue                      # 只处理 data: 开头的行
        data = line[5:].strip()           # 剥掉 "data:" 前缀
        if data == b"[DONE]":
            break                         # 结束标记
        try:
            delta = json.loads(data)["choices"][0]["delta"]
        except Exception:
            continue
        content = delta.get("content")    # 剥出这一块的字
        if content:
            yield content                 # 关键③：交一块出去