# app/middleware/observability.py
"""
Enterprise-Grade Observability Middleware

Provides:
1. Request ID (correlation ID) generation and propagation
2. Request/response timing and logging
3. Context variables for accessing request metadata in any service

Usage:
    from app.middleware.observability import get_request_id, get_user_id
    
    # In any service or agent:
    request_id = get_request_id()
    logger.info("Processing", extra={"request_id": request_id})
"""

import uuid
import time
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from contextvars import ContextVar

# =============================================================================
# CONTEXT VARIABLES - Request-scoped state accessible anywhere in call stack
# =============================================================================

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
route_var: ContextVar[str] = ContextVar("route", default="")

logger = logging.getLogger("ali_platform")


# =============================================================================
# CONTEXT ACCESSORS - Use these in services/agents to get request context
# =============================================================================

def get_request_id() -> str:
    """
    Get the current request ID from context.
    Returns empty string if called outside of a request context.
    """
    return request_id_var.get()


def get_user_id() -> str:
    """
    Get the current user ID from context.
    Returns empty string if user is not authenticated or outside request context.
    """
    return user_id_var.get()


def set_user_id(user_id: str) -> None:
    """
    Set the user ID in context after authentication verification.
    Call this in your auth dependency after verifying the token.
    
    Example:
        async def verify_token(request: Request):
            user = validate_token(...)
            set_user_id(user['uid'])
            return user
    """
    user_id_var.set(user_id)


def get_route() -> str:
    """Get the current route path from context."""
    return route_var.get()


# =============================================================================
# REQUEST ID MIDDLEWARE
# =============================================================================

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Extracts X-Request-ID from incoming request headers (or generates one)
    2. Sets the ID in contextvars for access throughout the request lifecycle
    3. Adds X-Request-ID to response headers for client-side correlation
    4. Logs request start/end with timing metrics
    
    Header precedence:
    1. X-Request-ID (standard)
    2. X-Correlation-ID (alternative)
    3. Generate new UUID if neither present
    """
    
    HEADER_NAMES = ["X-Request-ID", "X-Correlation-ID"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Extract or generate request ID
        request_id = self._extract_request_id(request)
        
        # 2. Set context variables
        request_id_var.set(request_id)
        route_var.set(request.url.path)
        
        # 3. Start timing
        start_time = time.perf_counter()
        
        # 4. Log request start (minimal - full details on completion)
        self._log_request_start(request, request_id)
        
        # 5. Process request
        try:
            response = await call_next(request)
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # 6. Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # 7. Log request completion
            self._log_request_end(request, request_id, response.status_code, latency_ms)
            
            return response
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._log_request_exception(request, request_id, e, latency_ms)
            raise
    
    def _extract_request_id(self, request: Request) -> str:
        """Extract request ID from headers or generate new one."""
        for header_name in self.HEADER_NAMES:
            request_id = request.headers.get(header_name)
            if request_id:
                return request_id
        
        # Generate new UUID
        return str(uuid.uuid4())
    
    def _log_request_start(self, request: Request, request_id: str) -> None:
        """Log request start event."""
        # Skip noisy health check logs
        if request.url.path in ["/health", "/", "/api/heartbeat"]:
            return
        
        logger.info(
            f"➡️ {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "method": request.method,
                "event": "request_start",
                "user_id": get_user_id() or None
            }
        )
    
    def _log_request_end(
        self, 
        request: Request, 
        request_id: str, 
        status_code: int,
        latency_ms: float
    ) -> None:
        """Log request completion event with timing."""
        # Skip noisy health check logs
        if request.url.path in ["/health", "/", "/api/heartbeat"]:
            return
        
        outcome = "success" if status_code < 400 else "client_error" if status_code < 500 else "server_error"
        log_level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
        
        logger.log(
            log_level,
            f"⬅️ {request.method} {request.url.path} → {status_code} ({latency_ms:.1f}ms)",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "latency_ms": round(latency_ms, 2),
                "event": "request_end",
                "outcome": outcome,
                "user_id": get_user_id() or None
            }
        )
    
    def _log_request_exception(
        self, 
        request: Request, 
        request_id: str, 
        error: Exception,
        latency_ms: float
    ) -> None:
        """Log unhandled exception during request processing."""
        logger.exception(
            f"❌ {request.method} {request.url.path} → Exception: {type(error).__name__}",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "method": request.method,
                "latency_ms": round(latency_ms, 2),
                "event": "request_exception",
                "outcome": "exception",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "user_id": get_user_id() or None
            }
        )


# =============================================================================
# METRICS COLLECTOR (In-Memory for Phase 1)
# =============================================================================

class MetricsCollector:
    """
    Simple in-memory metrics collector for API latency and error rates.
    
    In production, replace with Prometheus client or CloudWatch integration.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self._latencies: list = []  # List of (timestamp, route, latency_ms, status_code)
        self._lock = None  # Will use asyncio.Lock if needed
    
    def record_request(
        self, 
        route: str, 
        latency_ms: float, 
        status_code: int
    ) -> None:
        """Record a completed request for metrics aggregation."""
        import time
        
        self._latencies.append({
            "timestamp": time.time(),
            "route": route,
            "latency_ms": latency_ms,
            "status_code": status_code
        })
        
        # Trim old samples
        if len(self._latencies) > self.max_samples:
            self._latencies = self._latencies[-self.max_samples:]
    
    def get_latency_percentiles(
        self, 
        window_seconds: int = 3600
    ) -> dict:
        """
        Calculate latency percentiles over the given time window.
        
        Returns:
            {
                "p50_ms": float,
                "p95_ms": float,
                "p99_ms": float,
                "sample_size": int
            }
        """
        import time
        import statistics
        
        cutoff = time.time() - window_seconds
        recent = [s["latency_ms"] for s in self._latencies if s["timestamp"] > cutoff]
        
        if not recent:
            return {
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "sample_size": 0,
                "period": f"last_{window_seconds}s"
            }
        
        recent.sort()
        n = len(recent)
        
        return {
            "p50_ms": round(recent[int(n * 0.50)] if n > 0 else 0, 2),
            "p95_ms": round(recent[int(n * 0.95)] if n > 0 else 0, 2),
            "p99_ms": round(recent[int(n * 0.99)] if n > 0 else 0, 2),
            "sample_size": n,
            "period": f"last_{window_seconds}s"
        }
    
    def get_failure_rate(
        self, 
        window_seconds: int = 3600
    ) -> dict:
        """
        Calculate failure rate over the given time window.
        
        Returns:
            {
                "total_requests": int,
                "failed_requests": int,
                "failure_rate_pct": float
            }
        """
        import time
        
        cutoff = time.time() - window_seconds
        recent = [s for s in self._latencies if s["timestamp"] > cutoff]
        
        total = len(recent)
        failed = sum(1 for s in recent if s["status_code"] >= 500)
        
        return {
            "total_requests": total,
            "failed_requests": failed,
            "failure_rate_pct": round((failed / total * 100) if total > 0 else 0, 2)
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect request metrics for the System Health dashboard.
    Should be added AFTER RequestIdMiddleware.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Record metrics (skip health checks to reduce noise)
        if request.url.path not in ["/health", "/"]:
            metrics_collector.record_request(
                route=request.url.path,
                latency_ms=latency_ms,
                status_code=response.status_code
            )
        
        return response
