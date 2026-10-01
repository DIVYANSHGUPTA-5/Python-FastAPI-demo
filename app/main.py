import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.routes import auth, products
from app.schemas import HealthResponse, RootResponse

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"

app = FastAPI(
    title="Product Management API",
    description="A RESTful API built with FastAPI for managing products.",
    version=API_VERSION,
    openapi_tags=[
        {"name": "Authentication", "description": "Register and log in to get a JWT token."},
        {"name": "Products", "description": "Manage your own products (login required)."},
    ],
)

app.include_router(auth.router)
app.include_router(products.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the real error server-side but never leak it to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/", response_model=RootResponse, tags=["General"], summary="API information")
def root() -> RootResponse:
    return RootResponse(
        message="Product Management API",
        version=API_VERSION,
        docs="/docs",
        health="/health",
    )


@app.get("/health", response_model=HealthResponse, tags=["General"], summary="Health check")
def health() -> HealthResponse:
    return HealthResponse(status="healthy")
