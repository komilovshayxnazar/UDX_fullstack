"""
jsonlog.py — JSON-line log handler matching the Distributed Log Aggregator's
canonical LogLine schema (internal/logline/logline.go): exactly
{timestamp, log_level, component, trace_id, message} per line.

The Go agent's decoder calls DisallowUnknownFields(), so any extra key
(e.g. a raw asdict() of the whole LogRecord) makes the line unparseable
and it gets silently skipped — the payload below is built by hand to
keep it exact.

LOG_FILE sozlanmagan bo'lsa (masalan lokal devda, aggregator stacki
ishlamayotganda) fayl handler ulanmaydi — konsol logging o'zgarishsiz
davom etadi.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
from datetime import datetime, timezone

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")

COMPONENT = os.getenv("LOGAGG_COMPONENT", "udx-backend")


class JSONLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message = f"{message} | {self.formatException(record.exc_info)}"

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": record.levelname,
            "component": COMPONENT,
            "message": message,
        }
        trace_id = trace_id_var.get()
        if trace_id:
            payload["trace_id"] = trace_id
        return json.dumps(payload, ensure_ascii=False)


def init_json_logging() -> None:
    """Attach a JSON-line file handler (tailed by the logagg agent) to the
    root logger, in addition to the existing console handler."""
    log_file = os.getenv("LOG_FILE")
    if not log_file:
        logging.info("[LOGAGG] LOG_FILE topilmadi — JSON-line logging o'chirilgan")
        return
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(JSONLineFormatter())
    logging.getLogger().addHandler(handler)
    logging.info("[LOGAGG] JSON-line logging yoqildi: %s", log_file)
