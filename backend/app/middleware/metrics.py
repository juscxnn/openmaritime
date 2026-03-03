"""
Metrics middleware for OpenMaritime.

Tracks request duration, API call counts, and integrates with Prometheus.
"""
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    metrics_collector,
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect request metrics for Prometheus.
    
    Records:
    - Request count by method, endpoint, and status code
    - Request duration histogram by method and endpoint
    """
    
    # endpoints to exclude from metrics (health checks, etc.)
    EXCLUDED_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Skip metrics endpoint itself
        if request.url.path.startswith("/metrics"):
            return await call_next(request)
        
        # Start timer
        start_time = time.perf_counter()
        
        # Extract endpoint label (normalize path parameters)
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            logger.error(f"Request error: {e}")
            raise
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Record metrics
            self._record_metrics(method, endpoint, status, duration)
        
        return response
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for better grouping.
        
        Examples:
        - /api/v1/fixtures/abc-123 -> /api/v1/fixtures/{id}
        - /api/v1/plugins/enabled -> /api/v1/plugins/{action}
        """
        # Replace UUIDs
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        path = re.sub(uuid_pattern, '{id}', path)
        
        # Replace numeric IDs
        numeric_pattern = r'/\d+'
        path = re.sub(numeric_pattern, '/{id}', path)
        
        return path
    
    def _record_metrics(self, method: str, endpoint: str, status: int, duration: float):
        """Record request metrics to Prometheus."""
        # Record using the metrics collector
        metrics_collector.record_request(method, endpoint, status, duration)
        
        # Also directly update Prometheus metrics for more control
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
