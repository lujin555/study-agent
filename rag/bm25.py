"""BM25 关键词检索（零依赖实现），用于和向量检索做混合召回。

为什么需要它：纯向量检索（bge-small-zh 中文模型）对英文专有名词
（Transformer / OpenPose / DeepPose 等）召回偏弱，BM25 用精确词匹配补齐。
评测上表现为 3 个漏检题，混合检索后应能召回。
"""
import math
import re
from collections import Counter


def tokenize(text: str) -> list:
    """分词：英文/数字连续串整体作为一个 token，中文按单字。统一小写。"""
    return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower())


class BM25:
    """标准 BM25（Okapi），默认 k1=1.5, b=0.75。"""

    def __init__(self, docs: list, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs = docs
        self.doc_tokens = [tokenize(d) for d in docs]
        self.doc_freq = Counter()          # token -> 含该 token 的文档数
        for tokens in self.doc_tokens:
            for t in set(tokens):
                self.doc_freq[t] += 1
        self.n = len(docs)
        self.avgdl = sum(len(t) for t in self.doc_tokens) / max(1, self.n)

    def _idf(self, token: str) -> float:
        df = self.doc_freq.get(token, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1.0)

    def scores(self, query: str) -> list:
        """返回每个文档的 BM25 分数（与 docs 同序）。"""
        q_tokens = tokenize(query)
        result = []
        for tokens in self.doc_tokens:
            tf = Counter(tokens)
            dl = len(tokens)
            s = 0.0
            for qt in q_tokens:
                f = tf.get(qt, 0)
                if f == 0:
                    continue
                norm = 1.0 - self.b + self.b * dl / self.avgdl
                s += self._idf(qt) * (f * (self.k1 + 1.0)) / (f + self.k1 * norm)
            result.append(s)
        return result

    def top(self, query: str, k: int) -> list:
        """返回分数最高的 k 个文档的索引（与 docs 同序的下标）。"""
        sc = self.scores(query)
        return sorted(range(len(sc)), key=lambda i: -sc[i])[:k]


def rrf_fusion(*ranked_id_lists, k: int = 60) -> list:
    """Reciprocal Rank Fusion：合并多路召回的 id 列表，返回融合排序后的 id。

    每个入参是一路召回的 id 列表（已按相关度降序，rank 从 1 起算）。
    """
    score = {}
    for id_list in ranked_id_lists:
        for rank, doc_id in enumerate(id_list):
            score[doc_id] = score.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(score, key=lambda d: -score[d])
