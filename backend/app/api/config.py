from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from pydantic import computed_field
from pydantic_settings import BaseSettings

from app.exceptions import log_error
from app.middleware.headers.headers import HeadersMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.db.utils import initialize_database, close_database_engine, sessionmanager
from app.blob.manager import (
    initialize_blob_storage,
    close_blob_storage,
    blob_storage_manager,
)


class Settings(BaseSettings):
    # api_endpoint: str = Field(alias="azure_api_endpoint")
    # api_key: str = Field(alias="azure_api_key")
    # base_path: str = Field("", alias="api_base_path")
    # openai_api_deployment: str = Field(alias="azure_openai_deployment")
    # openai_api_endpoint: str = Field(alias="azure_openai_endpoint")
    # openai_api_key: str = Field(alias="azure_openai_key")
    # phoenix_endpoint: str | None = None
    # upload_folder: str = "uploads"
    # otel_exporter_otlp_endpoint: str = Field(alias="otel_exporter_otlp_endpoint")

    # auth settings
    azure_auth_enabled: bool = True
    azure_client_id: str | None = None
    azure_tenant_id: str | None = None
    azure_api_scope_claim: str | None = None

    # database settings
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    nachet_schema: str | None = None

    # blob storage settings
    blob_storage_provider: str | None = None
    blob_storage_name: str | None = None
    blob_storage_key: str | None = None
    blob_storage_endpoint_protocol: str | None = None
    blob_storage_endpoint_suffix: str | None = None
    blob_storage_endpoint_base: str | None = None

    cors_allow_origins: str | None = None
    trusted_hosts: str | None = None

    # frontend static files settings
    frontend_blob_container: str | None = None
    frontend_version_file: str | None = None

    # logging/observability settings
    otel_exporter_protocol: str = "grpc"  # "grpc" or "http"
    otel_exporter_endpoint: str = "http://alloy.monitoring.svc.cluster.local:4317"
    log_level: str = "INFO"

    # api settings
    base_path: str = ""
    project_name: str = "Nachet API"
    swagger_path: str = "/docs"
    swagger_ui_client_id: str | None = None
    testing: bool = True
    debug: bool = False
    security_headers_preset: str = "strict"

    @computed_field
    @property
    def allowed_origin_list(self) -> list[str]:
        origins = []
        if self.cors_allow_origins:
            origins.extend(self.cors_allow_origins.split(","))
        return origins or ["http://localhost:5173"]  # fallback default

    @computed_field
    @property
    def trusted_host_list(self) -> list[str]:
        hosts = []
        if self.trusted_hosts:
            hosts.extend(self.trusted_hosts.split(","))
        return hosts or ["localhost"]

    @computed_field
    @property
    def blob_storage_config(self) -> dict:
        """Configuration for blob storage initialization."""
        return {
            "blob_storage_provider": self.blob_storage_provider,
            "blob_storage_name": self.blob_storage_name,
            "blob_storage_key": self.blob_storage_key,
            "blob_storage_endpoint_protocol": self.blob_storage_endpoint_protocol,
            "blob_storage_endpoint_suffix": self.blob_storage_endpoint_suffix,
            "blob_storage_endpoint_base": self.blob_storage_endpoint_base,
        }

    @computed_field
    @property
    def logging_config(self) -> dict:
        """Configuration for logging initialization."""
        return {
            "otel_exporter_protocol": self.otel_exporter_protocol.lower(),
            "otel_exporter_endpoint": self.otel_exporter_endpoint,
            "log_level": self.log_level.upper(),
        }

    @computed_field
    @property
    def db_conn_info(self) -> dict:
        if self.testing:
            return {
                "url": "sqlite+aiosqlite:///test_migration.db.local",
                "echo": True,
            }
        return {
            "url": f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?options=-csearch_path={self.nachet_schema}",
            "echo": True if self.debug else False,
            # Additional pool options
            "pool_recycle": 3600,
            "pool_size": 20,  # Number of connections to maintain
            "max_overflow": 10,  # Additional connections beyond pool_size
            "pool_timeout": 30,  # Timeout for getting connection
            "pool_pre_ping": True,  # Verify connections before use
        }


# Global settings instance
_settings: Settings | None = None

# Global limiter instance
_limiter: Limiter | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_limiter() -> Limiter:
    """Get or create the global limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["600/minute"],
            strategy="sliding-window-counter",
        )
    return _limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # settings: Settings = app.settings
    print("🚀 Starting lifespan startup...")

    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")
    print("✅ Settings loaded successfully")

    # Initialize logging infrastructure
    print("🔄 Initializing logging...")
    from app.service import LogService
    LogService.setup_logging(settings.logging_config)
    print("✅ Logging initialized successfully")

    # Initialize database (validates schema version and sets up SessionManager)
    print("🔄 Initializing database...")
    await initialize_database(settings)
    print("✅ Database initialized successfully")

    # Initialize blob storage
    print("🔄 Initializing blob storage...")
    await initialize_blob_storage(settings)
    print("✅ Blob storage initialized successfully")

    # Initialize frontend service
    if settings.frontend_blob_container and settings.frontend_version_file:
        print("🔄 Initializing frontend service...")
        from app.service import FrontendService

        FrontendService.configure(
            settings.frontend_blob_container, settings.frontend_version_file
        )
        await FrontendService.check_and_update_version()
        print("✅ Frontend service initialized successfully")

    # Store managers in app state for access throughout the app
    app.state.sessionmanager = sessionmanager
    app.state.blob_storage_manager = blob_storage_manager
    print("✅ App state configured successfully")

    # Note: OTEL logging and tracing is now handled by LogService (see app/service/logs.py)

    print("🎉 FastAPI app startup complete!")
    yield

    # Shutdown
    print("🛑 Starting app shutdown...")
    await close_database_engine()
    await close_blob_storage()
    print("✅ App shutdown complete")


def create_app(settings: Settings, router: APIRouter, lifespan=None):
    app = FastAPI(
        lifespan=lifespan, docs_url=settings.swagger_path, root_path=settings.base_path
    )
    app.settings = settings

    # Initialize rate limiter and add to app state before middleware
    limiter = get_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_origin_regex=r"/^https?:\/\/localhost(:[0-9]{1,5})?$/",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
    app.add_middleware(HeadersMiddleware, preset=settings.security_headers_preset)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(LoggingMiddleware)  # Request/response logging with correlation IDs

    # Database SessionManager will be available via app.state.sessionmanager after lifespan startup

    app.include_router(router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, e: Exception):
        # Get correlation_id from request state if available
        correlation_id = getattr(request.state, 'correlation_id', None)

        log_error(e)

        response_content = {"detail": str(e)}
        if correlation_id:
            response_content["correlation_id"] = correlation_id

        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=response_content
        )

    return app
