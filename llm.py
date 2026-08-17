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
