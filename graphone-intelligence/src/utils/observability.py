import json
import logging
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "runId": run_id_var.get(),
            "taskId": task_id_var.get(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        for key in (
            "provider",
            "retryCount",
            "statusCode",
            "durationMs",
            "source",
            "errorKind",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def new_run_id() -> str:
    value = str(uuid.uuid4())
    run_id_var.set(value)
    return value


def set_task_id(task_id: str | None = None) -> str:
    value = task_id or str(uuid.uuid4())
    task_id_var.set(value)
    return value


def clear_observability_context() -> None:
    run_id_var.set(None)
    task_id_var.set(None)


class Metrics:
    def __init__(self) -> None:
        self._values: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self._values[name] = self._values.get(name, 0) + amount

    def snapshot(self) -> dict[str, int]:
        return dict(self._values)

    def reset(self) -> None:
        self._values.clear()


metrics = Metrics()


def log_event(
    level: int,
    message: str,
    *,
    event: str,
    logger_name: str = "graphone",
    **fields: Any,
) -> None:
    logger = logging.getLogger(logger_name)
    extra = {"event": event}
    extra.update(fields)
    logger.log(level, message, extra=extra)
