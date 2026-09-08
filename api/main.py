import logging
import uuid
from typing import cast

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from api.routes import router
from api.limiter import limiter
from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def rate_limit_handler(request: Request, exception: Exception) -> Response:
    return _rate_limit_exceeded_handler(
        request,
        cast(RateLimitExceeded, exception),
    )

app = FastAPI(
    title="Autonomous Support Agent API",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.include_router(router)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_id=%s method=%s path=%s status=%s", request_id, request.method, request.url.path, response.status_code)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    try:
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags",
            timeout=2,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "ollama": "unavailable", "detail": str(error)},
        )

    return {"status": "ready", "ollama": "available", "model": settings.OLLAMA_MODEL}