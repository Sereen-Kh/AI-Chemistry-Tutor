import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis import get_redis_client

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for static/health endpoints if needed
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        redis = get_redis_client()
        
        # 100 requests per minute per IP
        limit = 100
        window = 60
        
        try:
            key = f"rate_limit:{client_ip}:{int(time.time() / window)}"
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, window)
                
            if current > limit:
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        except Exception:
            # If Redis fails, let the request pass
            pass
            
        return await call_next(request)
