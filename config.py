import os
from dotenv import load_dotenv

load_dotenv()

# ===== 向量库 / 投件箱 =====
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

# ===== 切块参数（chunker 目前写死，留作以后调参） =====
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ===== 检索 =====
TOP_K = int(os.getenv("TOP_K", "5"))
