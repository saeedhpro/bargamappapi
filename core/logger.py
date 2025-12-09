import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json

# ساخت دایرکتوری logs
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """فرمت رنگی برای ترمینال"""

    COLORS = {
        'DEBUG': '\033[36m',  # cyan
        'INFO': '\033[32m',  # green
        'WARNING': '\033[33m',  # yellow
        'ERROR': '\033[31m',  # red
        'CRITICAL': '\033[35m',  # magenta
        'RESET': '\033[0m'  # reset
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(
        name: str,
        log_file: str = None,
        level: int = logging.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
) -> logging.Logger:
    """
    تنظیم یک logger با خروجی فایل و کنسول

    Args:
        name: نام logger
        log_file: نام فایل لاگ (اگر None باشه، فقط به کنسول می‌نویسه)
        level: سطح لاگ (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: حداکثر سایز فایل لاگ قبل از rotate
        backup_count: تعداد فایل‌های backup
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # پاک کردن handler های قبلی
    logger.handlers.clear()

    # فرمت لاگ
    log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Handler برای کنسول (با رنگ)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Handler برای فایل (بدون رنگ)
    if log_file:
        file_path = LOGS_DIR / log_file
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


class DatabaseLogger:
    """کلاس مخصوص لاگ‌گذاری عملیات دیتابیس"""

    def __init__(self, logger_name: str = "database"):
        self.logger = setup_logger(
            name=logger_name,
            log_file=f"{logger_name}.log"
        )

    def log_query(self, query: str, params: dict = None):
        """لاگ کوئری دیتابیس"""
        msg = f"QUERY: {query}"
        if params:
            msg += f"\nPARAMS: {json.dumps(params, ensure_ascii=False, indent=2)}"
        self.logger.debug(msg)

    def log_create(self, model_name: str, data: dict):
        """لاگ ساخت رکورد جدید"""
        self.logger.info(
            f"CREATE {model_name}:\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        )

    def log_update(self, model_name: str, record_id: int, changes: dict):
        """لاگ به‌روزرسانی رکورد"""
        self.logger.info(
            f"UPDATE {model_name} (id={record_id}):\n{json.dumps(changes, ensure_ascii=False, indent=2)}"
        )

    def log_delete(self, model_name: str, record_id: int):
        """لاگ حذف رکورد"""
        self.logger.warning(f"DELETE {model_name} (id={record_id})")

    def log_error(self, operation: str, error: Exception):
        """لاگ خطای دیتابیس"""
        import traceback
        self.logger.error(
            f"DB ERROR in {operation}:\n"
            f"Error Type: {type(error).__name__}\n"
            f"Error Message: {str(error)}\n"
            f"Traceback:\n{traceback.format_exc()}"
        )


class WebSocketLogger:
    """کلاس مخصوص لاگ‌گذاری WebSocket"""

    def __init__(self, logger_name: str = "websocket"):
        self.logger = setup_logger(
            name=logger_name,
            log_file=f"{logger_name}.log"
        )

    def log_connect(self, user_id: int, conversation_id: int):
        """لاگ اتصال"""
        self.logger.info(f"🔗 CONNECT: user={user_id}, conversation={conversation_id}")

    def log_disconnect(self, user_id: int, conversation_id: int):
        """لاگ قطع اتصال"""
        self.logger.info(f"🔌 DISCONNECT: user={user_id}, conversation={conversation_id}")

    def log_message(self, action: str, data: dict):
        """لاگ پیام دریافتی"""
        self.logger.debug(
            f"📩 MESSAGE: action={action}\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        )

    def log_broadcast(self, conversation_id: int, message_type: str):
        """لاگ ارسال پخش عمومی"""
        self.logger.debug(f"📡 BROADCAST: conversation={conversation_id}, type={message_type}")

    def log_error(self, context: str, error: Exception):
        """لاگ خطای WebSocket"""
        import traceback
        self.logger.error(
            f"❌ WS ERROR in {context}:\n"
            f"Error Type: {type(error).__name__}\n"
            f"Error Message: {str(error)}\n"
            f"Traceback:\n{traceback.format_exc()}"
        )


# نمونه‌های آماده برای استفاده
db_logger = DatabaseLogger()
ws_logger = WebSocketLogger()
app_logger = setup_logger("app", "app.log")
