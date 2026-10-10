import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Build the HTTP application without starting a server process."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    # Flutter Web picks an available development port at launch, so listing a
    # handful of fixed localhost ports makes its browser preflight fail before
    # the login handler is reached. Keep this convenience limited to local
    # development; deployed environments must explicitly list their origins.
    local_origin_regex = None
    if settings.app_env.lower() == "development":
        local_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=local_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    """Run the API using the configured host and port."""
    settings = get_settings()
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)


if __name__ == "__main__":
    run()
