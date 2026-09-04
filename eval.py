"""RAG 评估：检索命中率 + 生成正确率 + 诚实拒绝率 + 消融实验。"""

import agent
from eval_questions import EVAL_QUESTIONS
from rag.store import query as vector_query, hybrid_query
from llm import chat


def eval_retrieval():
    """检索评估：不花钱。对比纯向量 vs 混合检索（向量+BM25）的命中率。"""
    print("===== 检索评估（纯向量 vs 混合检索）=====")
    for label, fn in [("纯向量", vector_query), ("混合检索", hybrid_query)]:
        hits = 0
        total = 0
        missed = []
        for q in EVAL_QUESTIONS:
            if q["expected_source"] is None:
                continue  # 幻觉题没有期望来源，不参与检索评估
            total += 1
            r = fn("documents", q["question"], top_k=5)
            chunks = r["documents"][0]
            hit = any(q["expected"] in c for c in chunks)
            hits += hit
            if not hit:
                missed.append(f"{q['question']}（期望含: {q['expected']}）")
        print(f"{label}命中率: {hits}/{total}")
        for m in missed:
            print(f"  [漏检] {m}")


def eval_generation():
    """生成评估：完整跑 Agent，检查回答。"""
    print("\n===== 生成评估 =====")
    correct = 0
    have = 0       # 资料里有的题
    honest = 0
    not_in_docs = 0  # 资料里没有的题（测幻觉）
    for q in EVAL_QUESTIONS:
        answer = agent.run_agent(q["question"])["answer"]
        if q["expected"]:
            have += 1
            if q["expected"] in answer:
                correct += 1
            else:
                print(f"  [答错] {q['question']}")
                print(f"    期望含: {q['expected']}")
                print(f"    实际: {answer[:120]}")
        else:
            not_in_docs += 1
            # 判"诚实拒绝"：关键词命中即可。注意覆盖中文里常见的几种说法，
            # 否则模型明明拒答了、只因措辞不同（如"资料中没有提到" vs "资料里没有"）就被误判成幻觉。
            # 先去 markdown 标记，避免 "资料中**没有**关于" 的 ** 打断关键词连续匹配。
            import re
            _clean = re.sub(r"[*_]", "", answer)
            refused = any(k in _clean for k in [
                "没有检索到", "没有找到", "没有相关", "没有关于",
                "资料里没有", "资料中没有", "没有提到", "没有提及",
                "无法基于", "无法根据", "无法从", "并没有", "不包含",
            ])
            if refused:
                honest += 1
            else:
                print(f"  [幻觉!] {q['question']}")
                print(f"    实际: {answer[:120]}")
    print(f"生成正确率（资料有的）: {correct}/{have}")
    print(f"诚实拒绝率（资料没有的）: {honest}/{not_in_docs}")


def llm_only(question: str) -> str:
    """纯模型链路：不检索，直接凭模型自身知识回答。用于消融实验。"""
    resp = chat([
        {"role": "system", "content": "你是学习助理。直接回答用户问题，用中文，简明扼要。"},
        {"role": "user", "content": question},
    ])
    return resp["choices"][0]["message"]["content"]


def eval_ablation():
    """消融实验：同一批资料内题，对比「有检索(RAG)」vs「纯模型」的正确率，量化 RAG 增量。

    关键点：如果两条链路正确率几乎一样，说明当前评测集（通用技术知识）测不出 RAG 的
    增量价值——因为模型本身就会这些知识。此时结论不是"RAG 没用"，而是"评测集太简单，
    需要用私有/冷门/时效性资料才能测出 RAG 真正的价值"。
    """
    print("\n===== 消融实验（RAG 增量）=====")
    rag_correct = 0
    llm_correct = 0
    total = 0
    for q in EVAL_QUESTIONS:
        if not q["expected"]:
            continue  # 只测资料内题
        total += 1
        rag_ans = agent.run_agent(q["question"])["answer"]
        llm_ans = llm_only(q["question"])
        rag_ok = q["expected"] in rag_ans
        llm_ok = q["expected"] in llm_ans
        rag_correct += rag_ok
        llm_correct += llm_ok
        if rag_ok != llm_ok:
            tag = "RAG 补上了" if rag_ok else "RAG 反而带偏了"
            print(f"  [{tag}] {q['question']}")
    print(f"有检索(RAG)正确率: {rag_correct}/{total}")
    print(f"纯模型正确率:      {llm_correct}/{total}")
    print(f"RAG 增量:          {rag_correct - llm_correct} 题")


if __name__ == "__main__":
    eval_retrieval()
    eval_generation()
