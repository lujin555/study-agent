from llm import chat
from rag.store import query as vector_query
from config import TOP_K


def search_notes(query: str, top_k: int = None, min_similarity: float = 0.6) -> str:
    if top_k is None:
        top_k = TOP_K
    try:
        result = vector_query("documents", query, top_k=top_k)
        if not result or not result.get("documents") or not result["documents"][0]:
            return "向量库还没有内容。请先把资料拖进 docs/ 文件夹，再运行 ingest.py。"
        chunks = result["documents"][0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        parts = []
        for i, c in enumerate(chunks):
            d = dists[i] if i < len(dists) else 0     # 拿这一条的距离
            if d > min_similarity:                    # 太远 = 不够相关
                continue                              # 过滤掉！
            src = metas[i].get("source", "") if i < len(metas) else ""
            parts.append(f"[片段{i + 1}] {c}（来源：{src}）")
        if not parts:
            return "没有检索到与问题足够相关的内容，换个说法试试，或先把资料拖进 docs/ 文件夹。"
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
