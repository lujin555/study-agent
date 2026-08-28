"""投件箱自动监听：拖文件进 docs/ 就自动入库，不用再手动跑 ingest.py。"""
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import DOCS_DIR
from ingest import ingest_one

SUPPORTED = {".pdf", ".doc", ".docx", ".txt"}


class DocsHandler(FileSystemEventHandler):
    """文件夹一有新文件，就自动入库。"""
    def _wait_for_stable_size(self, path: Path, timeout: int = 30, interval: float = 1.0) -> bool:
        """等文件大小稳定（复制完成）再返回 True；超时返回 False。"""
        last_size = -1
        stable = 0
        waited = 0
        while waited < timeout:
            if not path.exists():
                return False                    # 文件消失了（可能复制被取消）
            size = path.stat().st_size
            if size == last_size:
                stable += 1
                if stable >= 2:                 # 连续两次大小一致 = 写完了
                    return True
            else:
                stable = 0                      # 大小还在变 = 还在复制
                last_size = size
            time.sleep(interval)
            waited += interval
        return False                            # 超时（30 秒还不稳定就放弃）

    def _try_ingest(self, path: Path):
        if not (path.is_file() and path.suffix.lower() in SUPPORTED):
            return
        if not self._wait_for_stable_size(path):
            print(f"文件大小一直不稳定或超时，跳过: {path.name}")
            return
        try:
            ingest_one(path)
        except Exception as e:
            print(f"自动入库失败: {path.name} -> {e}")

    def on_created(self, event):
        # 复制/保存进文件夹触发 created
        self._try_ingest(Path(event.src_path))

    def on_moved(self, event):
        # 同盘符拖拽有时触发 moved（源被移走，目标 dest_path）
        self._try_ingest(Path(event.dest_path))


def main():
    docs_dir = Path(DOCS_DIR)
    docs_dir.mkdir(exist_ok=True)

    observer = Observer()
    observer.schedule(DocsHandler(), str(docs_dir), recursive=False)
    observer.start()
    print(f"正在监听 {docs_dir}（拖 PDF/DOCX/TXT 进来就自动入库，Ctrl+C 停止）")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
