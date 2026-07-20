import logging
import json
import datetime
from pathlib import Path
from backend.config import LOGS_DIR
from backend.pii_redactor import redact_pii

LOG_FILE = LOGS_DIR / "pipeline_structured.jsonl"

class JSONFormatter(logging.Formatter):
    """
    Custom logging Formatter that outputs structured JSON logs with PII redaction.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": redact_pii(record.getMessage()),
            "module": record.module,
            "line": record.lineno
        }
        
        # Attach extra structured fields if provided
        if hasattr(record, "project_id"):
            log_entry["project_id"] = getattr(record, "project_id")
        if hasattr(record, "agent_name"):
            log_entry["agent_name"] = getattr(record, "agent_name")
        if hasattr(record, "event_type"):
            log_entry["event_type"] = getattr(record, "event_type")

        return json.dumps(log_entry)

def setup_logger(name: str = "pipeline") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(JSONFormatter())
        logger.addHandler(stream_handler)
        
    return logger

pipeline_logger = setup_logger("agent_pipeline")
