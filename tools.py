import json

from llm import chat
from rag.store import query as vector_query
from config import TOP_K, SEARCH_MAX_DISTANCE


def search_notes(query: str, top_k: int = None, max_distance: float = SEARCH_MAX_DISTANCE) -> str:
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
            if d > max_distance:                      # 太远 = 不够相关
                continue                              # 过滤掉！
            src = metas[i].get("source", "") if i < len(metas) else ""
            parts.append(f"[片段{i + 1}] {c}（来源：{src}）")
        if not parts:
            return "没有检索到与问题足够相关的内容，换个说法试试，或先把资料拖进 docs/ 文件夹。"
        return "\n\n".join(parts)
    except Exception as e:
        return f"检索失败: {e}"


def make_quiz(topic: str) -> str:
    """动作型工具：让 DeepSeek 生成一道练习题，并格式化为易读文本。"""
    prompt = (
        f"请根据主题「{topic}」出一道练习题，只输出 JSON："
        '{"question": "题目", "answer": "答案", "explain": "解析"}'
    )
    result = chat([{"role": "user", "content": prompt}])["choices"][0]["message"]["content"]
    try:
        # 兼容模型可能包裹的 ```json ... ``` 代码块
        raw = result.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            raw = raw.rsplit("\n", 1)[0] if "\n" in raw else raw
            raw = raw.replace("```", "").strip()
        data = json.loads(raw)
        return (
            f"题目：{data['question']}\n\n"
            f"答案：{data['answer']}\n\n"
            f"解析：{data['explain']}"
        )
    except Exception as e:
        return f"生成练习题结果：\n{result}\n\n（格式化失败：{e}）"
