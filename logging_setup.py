import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()          # 去终端
    console.setFormatter(fmt)
    root.addHandler(console)

    Path("logs").mkdir(exist_ok=True)
    fileh = RotatingFileHandler(               # 去文件，超 1MB 自动轮转
        "logs/app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    fileh.setFormatter(fmt)
    root.addHandler(fileh)