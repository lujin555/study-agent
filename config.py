import os
from dotenv import load_dotenv

load_dotenv()
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "")

# ===== 向量库 / 投件箱 =====
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

# ===== 向量模型 =====
# 设置本地路径时，优先加载该目录下的模型；空字符串则回退到 HuggingFace 名称
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "")

# ===== 切块参数 =====
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ===== 检索 =====
TOP_K = int(os.getenv("TOP_K", "5"))
SEARCH_MAX_DISTANCE = float(os.getenv("SEARCH_MAX_DISTANCE", "0.6"))

# ===== 上传 =====
# 单文件上限（字节），默认 50MB；环境变量可覆盖
UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(50 * 1024 * 1024)))
