import logging

log = logging.getLogger(__name__)


class ErrorMiddleware:
    def __init__(self, next):
        self.next = next

    def __call__(self, request):
        return self.next(request)

    def process_exception(self, request, exception):
        log.error("Error handling request %s", request, exc_info=exception)
