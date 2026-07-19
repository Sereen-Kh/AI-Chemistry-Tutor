from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings


def _create_redis_pool() -> ConnectionPool:
    return ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=10,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


# One reusable pool per application lifespan. Shutdown replaces this object so
# scripts and TestClient instances never reuse connections from a closed loop.
_redis_pool = _create_redis_pool()

async def get_redis() -> Redis:
    """Dependency for getting a Redis client instance."""
    client = Redis(connection_pool=_redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
        
# For services where we can't easily use FastAPI Depends (e.g. background tasks or internal functions)
def get_redis_client() -> Redis:
    """Get a raw redis client using the global pool."""
    return Redis(connection_pool=_redis_pool)


async def close_redis_pool() -> None:
    """Close the shared Redis pool in one-shot scripts."""
    global _redis_pool

    pool = _redis_pool
    try:
        await pool.aclose()
    except RuntimeError as exc:
        if "Event loop is closed" not in str(exc):
            raise
    finally:
        _redis_pool = _create_redis_pool()
