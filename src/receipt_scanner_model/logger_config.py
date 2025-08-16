import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal

LOG_TYPE = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LoggerConfig:
    """ログ設定クラス"""

    def __init__(
        self,
        level: LOG_TYPE,
        log_fp: Path,
    ):
        self.log_fp = log_fp
        self.log_level = getattr(logging, level)

    def setup_logging(self) -> None:
        """ログ設定を初期化"""
        # ログファイル作成
        self.log_fp.parent.mkdir(parents=True, exist_ok=True)

        # ハンドラー設定
        handlers = []

        # ファイルハンドラー
        file_handler = RotatingFileHandler(
            filename=self.log_fp,
            maxBytes=1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y/%m/%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(levelname)s - %(message)s",
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

        # 基本設定
        logging.basicConfig(
            level=self.log_level,
            handlers=handlers,
            force=True,
        )

        # Uvicorn/FastAPIログの統合
        self._configure_third_party_loggers(handlers, self.log_level)

    def _configure_third_party_loggers(self, handlers: list, log_level: int) -> None:
        """サードパーティライブラリのログ設定"""
        third_party_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error"]

        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.handlers.extend(handlers)
            logger.setLevel(log_level)
            logger.propagate = False


def set_logger(
    level: LOG_TYPE = "INFO",
    log_fp: Path = Path("logs/python_server.log"),
) -> None:
    """ログ設定を初期化"""
    config = LoggerConfig(level=level, log_fp=log_fp)
    config.setup_logging()
