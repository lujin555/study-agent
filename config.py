import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "")

# ===== 向量库 / 投件箱 =====
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

# ===== 向量模型 =====
# 优先级：环境变量 EMBEDDING_MODEL_PATH > 自动探测 models/ 目录 > HuggingFace 在线名
# 自动探测让 pip install && pytest 开箱即用：跑过 download_model.py 后无需手动配路径
def _detect_local_model():
    """探测 models/ 下已下载的向量模型，避免回退到联网加载卡住。"""
    root = Path(__file__).parent
    for candidate in [
        root / "models" / "bge-small-zh-v1.5",               # Dockerfile 路径 / 手动放置
        root / "models" / "BAAI" / "bge-small-zh-v1.5",        # download_model.py 路径
    ]:
        if (candidate / "model.safetensors").exists():
            return str(candidate)
    return ""

EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "") or _detect_local_model()

# ===== 切块参数 =====
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ===== 检索 =====
TOP_K = int(os.getenv("TOP_K", "5"))
SEARCH_MAX_DISTANCE = float(os.getenv("SEARCH_MAX_DISTANCE", "0.6"))

# ===== 上传 =====
# 单文件上限（字节），默认 50MB；环境变量可覆盖
UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(50 * 1024 * 1024)))

# ===== OCR（扫描版 PDF）=====
# 默认关闭：OCR 约 2 秒/页，会显著拖慢 ingest，只在确认要吃扫描件时开启
OCR_ENABLED = os.getenv("OCR_ENABLED", "false").lower() in ("1", "true", "yes")
# 置信度阈值：低于此值丢弃（解决"OCR 没看清"的错字）
OCR_MIN_SCORE = float(os.getenv("OCR_MIN_SCORE", "0.5"))
# 行长度阈值：短于此值丢弃。
# 关键：置信度高 ≠ 内容有意义。E-R 图/手写残留的碎片（"一""n""5""秀S"）
# 置信度常常也很高，但本身没有语义，只能靠长度兜底过滤。
OCR_MIN_LINE_LEN = int(os.getenv("OCR_MIN_LINE_LEN", "2"))
