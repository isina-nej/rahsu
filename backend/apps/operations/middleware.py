import logging
import time
import uuid
from .logging import request_id
from .metrics import request_count, request_latency

logger = logging.getLogger('rahsu.requests')

class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        token = request_id.set(uuid.uuid4().hex)
        start = time.monotonic()
        try:
            response = self.get_response(request)
            response['X-Request-ID'] = request_id.get()
            seconds = time.monotonic() - start
            request_count.labels(request.method, str(response.status_code)).inc()
            request_latency.observe(seconds)
            logger.info('http.request method=%s status=%s duration_ms=%.2f', request.method, response.status_code, seconds*1000)
            return response
        finally:
            request_id.reset(token)
