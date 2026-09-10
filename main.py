import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware

from admin.controller import router as admin_router
from auth.controller import router as auth_router
from booking.controller import router as booking_router
from core.exceptions import AppError
from event.controller import categories_router, router as event_router
from logger import logger
from utils.uploads import UPLOAD_ROOT


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="Event Ticketing API",
    description="Backend API for an event ticketing platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://evvnt-ticketer.netlify.app",
        "http://localhost:4200",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


UPLOAD_ROOT.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

app.include_router(auth_router)
app.include_router(event_router)
app.include_router(categories_router)
app.include_router(booking_router)
app.include_router(admin_router)


@app.get("/")
async def read_root():
    return {
        "message": "Event Ticketing API is running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def catch_all(request: Request, path: str):
    return JSONResponse(
        status_code=404,
        content={"message": f"Can't find {path} on this server!"}
    )

@app.exception_handler(AppError)
async def app_error_handler(
    request: Request,
    exc: AppError,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "fail",
            "message": exc.message,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.exception("Database error on %s %s: %s", request.method, request.url.path, exc)

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "A database error occurred",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception("Unexpected error on %s %s: %s", request.method, request.url.path, exc)

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
        },
    )