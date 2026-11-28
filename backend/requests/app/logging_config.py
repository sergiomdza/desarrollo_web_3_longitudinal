import json
import logging
import logging.config
import os
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):

    RESERVED_FIELDS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }

    def format(self, record):
        timestamp = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

        log_entry = {
            "timestamp": timestamp,
            "level": record.levelname,
            "service": os.getenv("SERVICE_NAME", "requests-backend"),
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_FIELDS and not key.startswith("_"):
                log_entry[key] = value

        if record.exc_info:
            exception_type = record.exc_info[0].__name__
            exception_message = str(record.exc_info[1])

            log_entry["error"] = {
                "type": exception_type,
                "message": exception_message,
            }

        return json.dumps(
            log_entry,
            ensure_ascii=False,
            default=str,
        )


def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "json": {
                "()": JsonFormatter,
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            },
        },

        "root": {
            "handlers": ["console"],
            "level": log_level,
        },

        "loggers": {
            "uvicorn.error": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },

            "uvicorn.access": {
                "handlers": [],
                "level": "WARNING",
                "propagate": False,
                "disabled": True,
            },
        },
    })