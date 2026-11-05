"""Privacy-aware JSON logs; no payloads, tokens, or precise geolocation."""
import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime, timezone

request_id = ContextVar('request_id', default='')
SENSITIVE = re.compile(r'(?i)(bearer\s+[\w.\-]+|password\s*[=:]\s*\S+|token\s*[=:]\s*\S+|secret\s*[=:]\s*\S+)')

class JsonFormatter(logging.Formatter):
    def format(self, record):
        message = SENSITIVE.sub('[REDACTED]', record.getMessage())
        event = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'event': message,
            'request_id': request_id.get(),
        }
        try:
            from opentelemetry import trace
            span = trace.get_current_span().get_span_context()
            if span.is_valid:
                event['trace_id'] = f'{span.trace_id:032x}'
        except ImportError:
            pass
        if record.exc_info:
            event['exception_class'] = record.exc_info[0].__name__
        return json.dumps(event, ensure_ascii=False)
