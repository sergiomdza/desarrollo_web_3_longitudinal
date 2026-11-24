"""Guarda method, path y hora de inicio de cada request para que los logs los incluyan solos."""
import time

from starlette.middleware.base import BaseHTTPMiddleware

from logging_config import request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request_context.set(
            {"method": request.method, "path": request.url.path, "start": time.perf_counter()}
        )
        try:
            return await call_next(request)
        finally:
            request_context.reset(token)