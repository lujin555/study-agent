"""投件箱：把 docs/ 文件夹里的文档自动切块入库。"""
import logging
from pathlib import Path

from config import DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from rag.loader import load_document, ScanPDFError
from rag.chunker import split_text
from rag.store import store_chunks, get_collection
from logging_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

COLLECTION = "documents"
SUPPORTED = {".pdf", ".doc", ".docx", ".txt", ".md"}


def ingest_one(path: Path, collection_name: str = COLLECTION) -> int:
    print(f"读取: {path.name}")
    text = load_document(str(path))
    if not text.strip():
        print(f"  跳过（没有文字内容）: {path.name}")
        return 0

    chunks = split_text(text, str(path), CHUNK_SIZE, CHUNK_OVERLAP)
    col = get_collection(collection_name)
    if col is not None:
        # 重新入库前清掉这个文件旧的块，避免重复
        col.delete(where={"source": str(path)})

    n = store_chunks(chunks, collection_name=collection_name)
    logger.info(f"入库 {n} 块: {path.name}")
    return n


def main():
    docs_dir = Path(DOCS_DIR)
    docs_dir.mkdir(exist_ok=True)
    # 递归扫描：docs/ 下可以有子目录分类存放资料（如 docs/CS-Notes/AI/xxx.md）
    files = [
        p for p in docs_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith(".")
    ]
    if not files:
        print(f"{docs_dir} 里没有文档。把 PDF/DOCX/TXT 拖进来，再运行本脚本。")
        return

    total = 0
    scanned = []
    for f in files:
        try:
            total += ingest_one(f)
        except ScanPDFError as e:
            # 扫描版不算"失败"，但要显眼地提示：这份资料实际没进知识库
            scanned.append(f.name)
            logger.warning(f"{e}")
        except Exception:
            logger.exception(f"失败: {f.name}")

    logger.info(f"完成，共入库 {total} 块。")
    if scanned:
        logger.warning(f"另有 {len(scanned)} 份扫描版 PDF 未入库（无文字层）：{', '.join(scanned)}")


if __name__ == "__main__":
    main()
