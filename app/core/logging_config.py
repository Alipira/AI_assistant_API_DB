import logging
import os

from datetime import datetime
from logging.handlers import RotatingFileHandler
from elasticsearch import Elasticsearch

# ── Directory for file logs ───────────────────────────────────────────────────
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ── Elasticsearch config ──────────────────────────────────────────────────────
ES_HOST = os.getenv("ELASTICSEARCH_URL")
ES_INDEX = os.getenv("ELASTICSEARCH_INDEX")
ES_API_KEY_ENCODE = os.getenv("ELASTICSEARCH_API_KEY_ENCODE")
APP_ENV = os.getenv("ENVIRONMENT", "demo")

es_client = Elasticsearch(ES_HOST, api_key=ES_API_KEY_ENCODE, verify_certs=False, request_timeout=10)


class ElasticsearchHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            doc = {
                "@timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "env": APP_ENV,
            }
            # attach extra fields if passed via logger.info(..., extra={...})
            for key in ("conv_id", "user_id", "action", "status_code", "elapsed"):
                if hasattr(record, key):
                    doc[key] = getattr(record, key)

            es_client.index(index=ES_INDEX, document=doc)
        except Exception:
            self.handleError(record)  # silently skip if ES is down


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ── Console handler ───────────────────────────────────────────────────────
    # Set to DEBUG for development, INFO for production via LOG_LEVEL env var
    console = logging.StreamHandler()
    console.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())
    console.setFormatter(formatter)
    logger.addHandler(console)

    # ── File handler ──────────────────────────────────────────────────────────
    # Rotates at 5MB, keeps 5 backups
    file_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    # file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # ── Elasticsearch handler ─────────────────────────────────────────────────
    # Only attached if ES is reachable — app starts normally if ES is down
    try:
        if es_client.info():
            es_handler = ElasticsearchHandler()
            es_handler.setLevel(logging.DEBUG)
            es_handler.setFormatter(formatter)
            logger.addHandler(es_handler)
        else:
            logger.warning("Elasticsearch unreachable — logging to console and file only")
    except Exception as e:
        logger.warning(f"Elasticsearch setup failed: {e} — logging to console and file only")

    return logger
