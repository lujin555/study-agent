from llm import chat
from rag.store import query as vector_query


def search_notes(query: str, top_k: int = 3) -> str:
    """检索型工具：直接从本地向量库（rag/store）检索相关资料片段。"""
    try:
        result = vector_query("documents", query, top_k=top_k)
        if not result or not result.get("documents") or not result["documents"][0]:
            return "向量库还没有内容。请先把资料拖进 docs/ 文件夹，再运行 ingest.py。"
        chunks = result["documents"][0]
        metas = result.get("metadatas", [[]])[0]
        parts = []
        for i, c in enumerate(chunks):
            src = metas[i].get("source", "") if i < len(metas) else ""
            parts.append(f"[片段{i + 1}] {c}（来源：{src}）")
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
