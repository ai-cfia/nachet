# from starlette.config import Config


from contextlib import asynccontextmanager
from http import HTTPStatus

# from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request

# from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool
from pydantic import computed_field #, Field
from pydantic_settings import BaseSettings
# from sqlmodel import StaticPool, create_engine

from app.exceptions import log_error
from app.middleware.headers.headers import HeadersMiddleware
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
    azure_storage_account_name: str | None = None
    azure_storage_account_key: str | None = None
    azure_storage_default_endpoint_protocol: str | None = None
    azure_storage_endpoint_suffix: str | None = None

    # api settings
    base_path: str = ""
    project_name: str = "Nachet API"
    swagger_path: str = "/docs"
    swagger_ui_client_id: str | None = None
    allowed_origins: list[str] = ["localhost", "http://localhost:5173", "http://localhost:5174"]
    testing: bool = True
    debug: bool = False

    @computed_field
    @property
    def azure_storage_connection_string(self) -> str:
        return (
            f"DefaultEndpointsProtocol={self.azure_storage_default_endpoint_protocol};"
            f"AccountName={self.azure_storage_account_name};"
            f"AccountKey={self.azure_storage_account_key};"
            f"EndpointSuffix={self.azure_storage_endpoint_suffix}"
        )

    @computed_field
    @property
    def pg_conn_info(self) -> str:
        return make_conninfo(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
        )

    @computed_field
    @property
    def db_conn_info(self) -> dict:
        if self.testing:
            return {
                "url": "sqlite://",
                "connect_args": {"check_same_thread": False},
                # "poolclass": StaticPool,
            }
        return {
            "url": f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}",
            "connect_args": {
                "options": f"-c search_path={self.nachet_schema},public"
            },
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # settings: Settings = app.settings
    app.pool.open()
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
    yield
    app.pool.close()
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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(HeadersMiddleware, preset="strict")

    pool = ConnectionPool(
        open=False,
        conninfo=settings.pg_conn_info,
        kwargs={"options": f"-c search_path={settings.nachet_schema},public"},
    )
    app.pool = pool

    # app.engine = create_engine(**settings.db_conn_info)

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
