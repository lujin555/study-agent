# 后端镜像：FastAPI + ChromaDB + 本地向量模型（bge-small-zh-v1.5）
# 选 3.12 而不是 3.14：torch / chromadb 这些 C 库对 3.14 支持还不成熟
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 向量模型缓存目录
    SENTENCE_TRANSFORMERS_HOME=/app/models \
    # 国内加速：HuggingFace 走镜像站（build 时已预置模型，运行时不强制联网）
    HF_ENDPOINT=https://hf-mirror.com \
    # 使用打包进镜像的本地模型路径
    EMBEDDING_MODEL_PATH=/app/models/bge-small-zh-v1.5

WORKDIR /app

# ① 先装 CPU 版 torch（避免拉带 CUDA 的数 GB 镜像）。
#    顺序很重要：torch 先装好，后面 sentence-transformers 就不会再拉一份完整版。
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# ② 装项目依赖（国内 pip 镜像加速）
COPY requirements.txt .
# 顺序陷阱：rapidocr 会顺带装 opencv-python，但它是带 GUI 的完整版，
# 在 slim 镜像里 import 会报 "libxcb.so.1: cannot open shared object file"。
# 必须在装完之后立刻换成无 GUI 的 headless 版（OCR 只用像素处理，不需要 GUI）。
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip uninstall -y opencv-python \
    && pip install opencv-python-headless==5.0.0.93 -i https://pypi.tuna.tsinghua.edu.cn/simple

# ③ 拷贝源码（models/bge-small-zh-v1.5 已预置在项目中，会一起打进镜像）

COPY . .

EXPOSE 8084
CMD ["python", "app.py"]
