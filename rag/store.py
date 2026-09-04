"""
向量库统一入口：封装 chromadb 的 增 / 删 / 查。

（从 rag-assiant 合并而来）
设计要点：
- 学习资料库共用一个 collection（"documents"），来源用 metadata 记录
- 暴露高层 API：store_chunks / query / delete_collection / get_collection
"""
import hashlib

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from config import CHROMA_DB_PATH, EMBEDDING_MODEL_PATH

# 嵌入函数：优先用本地模型路径，未设置则回退到 HuggingFace 名称
_model_name_or_path = EMBEDDING_MODEL_PATH or "BAAI/bge-small-zh-v1.5"
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=_model_name_or_path
)

# client 复用：chromadb 把已加载的 embedding function 缓存在 client 实例内部，
# 每次新建 PersistentClient 都会重新初始化（实测首次 30~80s，期间还会尝试联网），
# 导致入库每个文件都要付一次这个代价。这里按路径缓存 client，只在首次付一次。
_clients = {}


def _get_client(persist_path: str = None):
    """获取 chromadb 持久化客户端（同一路径复用同一个 client 实例）"""
    key = persist_path or CHROMA_DB_PATH
    if key not in _clients:
        _clients[key] = chromadb.PersistentClient(
            path=key,
            settings=Settings(anonymized_telemetry=False),
        )
    return _clients[key]


def _chunk_ids(collection_name: str, metas: list) -> list:
    """生成稳定 chunk id：按来源文件哈希，避免不同文件 id 撞车。"""
    source = (metas[0] or {}).get("source") if metas else collection_name
    h = hashlib.md5(str(source).encode("utf-8")).hexdigest()[:8]
    return [f"{collection_name}_{h}_chunk_{i}" for i in range(len(metas))]


def store_chunks(
    chunks,
    collection_name: str = "documents",
    persist_path: str = None,
) -> int:
    """
    增：把切好的 langchain Document 列表写入向量库。

    chunks: List[Document]
    collection_name: 默认 "documents"（学习资料共用一个大库）
    return: 实际入库的 chunk 数
    """
    if not chunks:
        return 0

    client = _get_client(persist_path)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=_ef,
    )

    texts = [c.page_content for c in chunks]
    metas = [c.metadata or {} for c in chunks]
    ids = _chunk_ids(collection_name, metas)

    collection.upsert(ids=ids, documents=texts, metadatas=metas)
    return len(texts)


def query(
    collection_name: str,
    question: str,
    top_k: int = 3,
    persist_path: str = None,
):
    """
    查：在指定 collection 里做语义检索。

    return: {
        "documents": [[str, ...]],
        "metadatas": [[dict, ...]],
        "distances": [[float, ...]],
    } 或 None（collection 不存在）
    """
    col = get_collection(collection_name, persist_path=persist_path)
    if col is None:
        return None
    return col.query(query_texts=[question], n_results=top_k)


def delete_collection(collection_name: str, persist_path: str = None) -> bool:
    """删：删除整个 collection。return: True 表示删了，False 表示本来就没有"""
    client = _get_client(persist_path)
    existing = [c.name for c in client.list_collections()]
    if collection_name not in existing:
        return False
    client.delete_collection(name=collection_name)
    return True


def get_collection(collection_name: str, persist_path: str = None):
    """拿到原始 collection 对象。不存在返回 None。"""
    client = _get_client(persist_path)
    try:
        return client.get_collection(
            name=collection_name,
            embedding_function=_ef,
        )
    except Exception:
        return None
