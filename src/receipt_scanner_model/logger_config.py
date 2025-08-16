import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def set_logger() -> None:
    log_dir = Path("logs/")
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = Path(log_dir, "python_server.log")
    handler = RotatingFileHandler(logfile, maxBytes=1024 * 1024, backupCount=5)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
        handlers=[handler],
    )
