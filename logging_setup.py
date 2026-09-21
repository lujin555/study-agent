import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_configured = False   # 模块级开关：无论被调用几次，handler 只挂一次


def setup_logging():
    """配置根日志（终端 + 文件轮转），幂等。

    为什么用开关而不是判断 root.handlers：
    uvicorn / pytest 等可能已经给 root 挂过 handler，
    那时我们仍然需要装上自己的，所以不能"看到有 handler 就跳过"。
    """
    global _configured
    if _configured:
        return
    _configured = True

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
