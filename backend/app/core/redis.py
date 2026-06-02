from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

# Create a connection pool to reuse connections
_redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True, # Automatically decode bytes to strings
    max_connections=10
)

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
