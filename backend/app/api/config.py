# from starlette.config import Config


from contextlib import asynccontextmanager
from http import HTTPStatus

# from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request

# from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# from psycopg.conninfo import make_conninfo
# from psycopg_pool import ConnectionPool
from pydantic import computed_field  # , Field
from pydantic_settings import BaseSettings

# from sqlmodel import StaticPool, create_engine

from app.exceptions import log_error
from app.middleware.headers.headers import HeadersMiddleware
from app.db.utils import initialize_database, close_database_engine, sessionmanager
from app.blob.manager import (
    initialize_blob_storage,
    close_blob_storage,
    blob_storage_manager,
)
# from app.models.bucket_name import MinioBucketName
# from app.services.file_storage import FertiscanStorage, MinIOStorageManager


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
    auth_enabled: bool = True
    auth_audience: str | None = None
    auth_instance: str | None = "https://login.microsoftonline.com"
    auth_tenant_id: str | None = None
    auth_client_id: str | None = None
    auth_client_secret: str | None = None

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

    nachet_frontend_url: str | None = None

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
    def allowed_origins(self) -> list[str]:
        origins = []
        if self.nachet_frontend_url:
            origins.append(self.nachet_frontend_url)
        return origins or ["http://localhost:5173"]  # fallback default

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


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # settings: Settings = app.settings
    print("🚀 Starting lifespan startup...")

    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")
    print("✅ Settings loaded successfully")

    # Initialize database (validates schema version and sets up SessionManager)
    print("🔄 Initializing database...")
    await initialize_database(settings)
    print("✅ Database initialized successfully")

    # Initialize blob storage
    print("🔄 Initializing blob storage...")
    await initialize_blob_storage(settings)
    print("✅ Blob storage initialized successfully")

    # Store managers in app state for access throughout the app
    app.state.sessionmanager = sessionmanager
    app.state.blob_storage_manager = blob_storage_manager
    print("✅ App state configured successfully")

    # Open connection pool
    # app.pool.open()

    # resource = Resource.create(
    #     {
    #         "service.name": "nachet-backend",
    #     }
    # )

    # # Tracing setup
    # tracer_provider = TracerProvider(resource=resource)
    # trace.set_tracer_provider(tracer_provider)
    # tracer_provider.add_span_processor(
    #     BatchSpanProcessor(
    #         OTLPSpanExporter(
    #             endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
    #         )
    #     )
    # )
    # # Logging setup
    # logger_provider = LoggerProvider(resource=resource)
    # set_logger_provider(logger_provider)
    # logger_provider.add_log_record_processor(
    #     BatchLogRecordProcessor(
    #         OTLPLogExporter(
    #             endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
    #         )
    #     )
    # )
    # handler = LoggingHandler(logger_provider=logger_provider)
    # logger.addHandler(handler)

    print("🎉 FastAPI app startup complete!")
    yield

    # Shutdown
    print("🛑 Starting app shutdown...")
    # app.pool.close()
    await close_database_engine()
    await close_blob_storage()
    print("✅ App shutdown complete")
    # logger_provider.shutdown()
    # tracer_provider.shutdown()


def create_app(settings: Settings, router: APIRouter, lifespan=None):
    app = FastAPI(
        lifespan=lifespan, docs_url=settings.swagger_path, root_path=settings.base_path
    )
    app.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex="/^https?:\/\/localhost(:[0-9]{1,5})?$/",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(HeadersMiddleware, preset=settings.security_headers_preset)

    # pool = ConnectionPool(
    #     open=False,
    #     conninfo=settings.pg_conn_info,
    #     kwargs={"options": f"-c search_path={settings.nachet_schema},public"},
    # )
    # app.pool = pool

    # Database SessionManager will be available via app.state.sessionmanager after lifespan startup

    app.include_router(router)

    # storage = FertiscanStorage(sm, settings.minio_app_bucket)

    # app.storage = storage

    @app.exception_handler(Exception)
    async def global_exception_handler(_: Request, e: Exception):
        log_error(e)
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content={"detail": str(e)}
        )

    return app
