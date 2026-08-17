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
