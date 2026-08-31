"""RAG 评估：检索命中率 + 生成正确率 + 诚实拒绝率。"""

import agent
from eval_questions import EVAL_QUESTIONS
from rag.store import query as vector_query


def eval_retrieval():
    """检索评估：不花钱。检查向量检索有没有把期望片段捞出来。"""
    print("===== 检索评估 =====")
    hits = 0
    total = 0
    for q in EVAL_QUESTIONS:
        if q["expected_source"] is None:
            continue  # 幻觉题没有期望来源，不参与检索评估
        total += 1
        r = vector_query("documents", q["question"], top_k=5)
        chunks = r["documents"][0]
        hit = any(q["expected"] in c for c in chunks)
        hits += hit
        if not hit:
            print(f"  [漏检] {q['question']}（期望含: {q['expected']}）")
    print(f"检索命中率: {hits}/{total}")


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
            refused = any(k in answer for k in ["没有检索到", "没有找到", "没有相关", "没有关于", "资料里没有", "无法基于", "并没有"])
            if refused:
                honest += 1
            else:
                print(f"  [幻觉!] {q['question']}")
                print(f"    实际: {answer[:120]}")
    print(f"生成正确率（资料有的）: {correct}/{have}")
    print(f"诚实拒绝率（资料没有的）: {honest}/{not_in_docs}")


if __name__ == "__main__":
    eval_retrieval()
    eval_generation()
