from fastapi import FastAPI
from .metrics import setup_metrics
from .routers import requests_router, health_router

app = FastAPI()

setup_metrics(app)

app.include_router(health_router.router)
app.include_router(requests_router.router)
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from .logging_config import configure_logging
from .metrics import setup_metrics
from .routers import requests_router, health_router


configure_logging()

logger = logging.getLogger("requests-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Servicio iniciado",
        extra={"event": "service_started"},
    )

    yield

    logger.info(
        "Servicio apagado",
        extra={"event": "service_stopped"},
    )


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    if request.url.path not in ("/health", "/metrics"):
        validation_errors = [
            {
                "location": error.get("loc"),
                "type": error.get("type"),
            }
            for error in exc.errors()
        ]

        logger.warning(
            "La solicitud recibida contiene datos invalidos",
            extra={
                "event": "validation_failed",
                "method": request.method,
                "path": request.url.path,
                "status_code": 422,
                "error_count": len(validation_errors),
                "validation_errors": validation_errors,
            },
        )

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


setup_metrics(app)

app.include_router(health_router.router)
app.include_router(requests_router.router)