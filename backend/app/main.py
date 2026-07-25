from contextlib import asynccontextmanager
from os import getenv

from fastapi import FastAPI
from loguru import logger
import ngrok
from sqlalchemy import text
import uvicorn

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.students import router as student_router
from app.api.question_router import router as question_router
from app.db.session import engine   

NGROK_AUTH_TOKEN = getenv(
    "NGROK_AUTH_TOKEN",
    ""
)

APPLICATION_PORT = 8000


@asynccontextmanager
async def lifespan(
    app: FastAPI
):

    # --------------------
    # Startup
    # --------------------

    logger.info(
        "Starting application..."
    )

    # Database health check
    try:

        with engine.connect() as conn:
            conn.execute(
                text("SELECT 1")
            )

        logger.success(
            "Database connected"
        )

    except Exception as e:

        logger.error(
            f"Database connection failed: {e}"
        )

        raise e

    try:

        if NGROK_AUTH_TOKEN:

            logger.info(
                "Setting up ngrok endpoint"
            )

            ngrok.set_auth_token(
                NGROK_AUTH_TOKEN
            )

            ngrok.forward(
                addr=
                APPLICATION_PORT
            )

            logger.success(
                "Ngrok tunnel active"
            )

    except Exception as e:

        logger.warning(
            f"Ngrok failed: {e}"
        )

    yield

    # --------------------
    # Shutdown
    # --------------------

    logger.info(
        "Shutting down..."
    )

    try:
        ngrok.disconnect()

    except Exception:
        pass


app = FastAPI(
    title="Chemistry AI Backend",
    version="1.0.0",
    lifespan=lifespan
)


# --------------------
# Routers
# --------------------

app.include_router(auth_router)
app.include_router(student_router)
app.include_router(chat_router)
app.include_router(question_router)

# --------------------
# Health Routes
# --------------------

@app.get("/")
def root():

    return {
        "message":
        "Chemistry AI Backend"
    }


@app.get("/health")
def health_check():

    return {
        "status":
        "healthy"
    }


if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=APPLICATION_PORT,
        reload=True
    )
