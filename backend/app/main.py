import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.routers.aqi import router as aqi_router
from app.routers.advice import router as advice_router
from app.routers.cities import router as cities_router
from app.routers.health import router as health_router
from app.rate_limit import limiter


def create_app() -> FastAPI:
    load_dotenv()
    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]

    app = FastAPI(
        title="Urban Air Quality Assistant",
        version="0.1.0",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(cities_router, prefix="/api")
    app.include_router(aqi_router, prefix="/api")
    app.include_router(advice_router, prefix="/api")
    return app


app = create_app()
