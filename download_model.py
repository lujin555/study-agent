"""下载 bge-small-zh-v1.5 向量模型到 models/ 目录。

Docker 构建前的前置步骤：
  python download_model.py

环境变量：
  HF_ENDPOINT — 模型下载源，默认 https://hf-mirror.com（国内镜像）

已存在的文件会跳过，多次运行幂等。
"""
import os
import sys
import urllib.request

REPO = "BAAI/bge-small-zh-v1.5"
FILES = [
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "model.safetensors",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "1_Pooling/config.json",
]
DEFAULT_ENDPOINT = "https://hf-mirror.com"


def report(blocks_read, block_size, total_size):
    """urlretrieve 进度回调。"""
    if total_size <= 0:
        return
    downloaded = blocks_read * block_size
    pct = min(downloaded * 100 // total_size, 100)
    sys.stdout.write(f"\r  progress: {pct}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB)")
    sys.stdout.flush()


def main():
    endpoint = os.getenv("HF_ENDPOINT", DEFAULT_ENDPOINT)
    if len(sys.argv) > 1:
        endpoint = sys.argv[1].rstrip("/")

    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", REPO)
    os.makedirs(dest_dir, exist_ok=True)

    ok = True
    for name in FILES:
        dest = os.path.join(dest_dir, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"[skip] {name} 已存在 ({os.path.getsize(dest) // 1024}KB)")
            continue

        sub_dir = os.path.dirname(dest)
        os.makedirs(sub_dir, exist_ok=True)
        url = f"{endpoint}/{REPO}/resolve/main/{name}"
        print(f"[down] {url}")
        tmp = dest + ".part"
        try:
            urllib.request.urlretrieve(url, tmp, reporthook=report)
            sys.stdout.write("\n")
            os.replace(tmp, dest)
        except Exception as e:
            sys.stdout.write("\n")
            print(f"[fail] {name}: {e}", file=sys.stderr)
            if os.path.exists(tmp):
                os.remove(tmp)
            ok = False

    if ok:
        print(f"完成：{dest_dir}")
    else:
        print("部分文件下载失败，请检查网络或设置 HF_ENDPOINT", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
