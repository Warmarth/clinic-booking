import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_hits = defaultdict(deque)
_lock = threading.Lock()


def register_middlewares(app: FastAPI, api_key: str) -> None:
    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        path = request.url.path
        is_open = (
            request.method == "OPTIONS"
            or path in ("/", "/docs", "/openapi.json", "/health")
            or path.startswith("/static")
        )
        if is_open:
            return await call_next(request)
        key = request.headers.get("x-api-key", "")
        if not key:
            return JSONResponse({"error": "API key required"}, status_code=401)
        if not hmac.compare_digest(key.encode(), api_key.encode()):
            return JSONResponse({"error": "invalid API key"}, status_code=401)
        return await call_next(request)

    # CORS must wrap API-key authentication so preflight requests stay public.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Retry-After"],
    )


def rate_limited(request: Request, limit: int, window_seconds: int) -> int:
    """Return seconds to wait when this client exceeds the sliding-window limit."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = (forwarded or request.client.host or "?").split(",")[0].strip()
    now = time.time()
    with _lock:
        window = _hits[ip]
        while window and now - window[0] > window_seconds:
            window.popleft()
        if len(window) >= limit:
            return max(1, int(window_seconds - (now - window[0])) + 1)
        window.append(now)
    return 0


def clear_rate_limits() -> None:
    with _lock:
        _hits.clear()
