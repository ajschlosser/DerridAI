import logging
import sys
from pathlib import Path
from utils.request_id import request_id

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True

def configure_logging(level: int = logging.DEBUG, file_name: str = "derridai.log") -> None:
    """Idempotent: safe to call multiple times (e.g. across reload workers) without duplicating handlers."""
    root = logging.getLogger()
    if root.hasHandlers():
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    r_id_filter = RequestIdFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(r_id_filter)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(Path(file_name), mode="w")
    file_handler.addFilter(r_id_filter)
    file_handler.setFormatter(formatter)

    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
    root.addFilter(r_id_filter)

for logger_name in (
    "httpx",
    "httpcore",
    "watchfiles",
    "huggingface_hub",
    "urllib3",
    "filelock",
    "transformers",
):
    logging.getLogger(logger_name).setLevel(logging.WARNING)