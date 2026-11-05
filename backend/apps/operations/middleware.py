import logging
import time
import uuid
from .logging import request_id

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
            logger.info('http.request method=%s status=%s duration_ms=%.2f', request.method, response.status_code, (time.monotonic()-start)*1000)
            return response
        finally:
            request_id.reset(token)
