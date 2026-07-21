# import hypercorn
# from fastapi import FastAPI
from app.api.routes import router as api_router
from app.api.config import create_app, get_settings, lifespan
from app.service.auth.config import BackendAuthConfig
from dbos import DBOS, DBOSConfig

# Share one validated settings instance across startup, lifespan, and auth.
settings = get_settings()
auth_config = BackendAuthConfig.from_settings(settings)
# Conditional import for debug routes
if settings.nachet_env == "development":
    from app.api.dev_routes import router as debug_router

    api_router.include_router(debug_router)

app = create_app(
    settings,
    api_router,
    lifespan=lifespan,
    auth_provider_origin=auth_config.browser_provider_origin,
)

dbos_config = DBOSConfig(
    name="nachet-dbos",
    dbos_system_schema="nachetdbos",
    system_database_url=app.settings.db_conn_info["url"],
    application_database_uri=app.settings.db_conn_info["url"],
    # system_database_engine=None,
    enable_otlp=app.settings.otel_enabled,
    log_level=app.settings.log_level.upper(),
    otlp_logs_endpoints=(
        [app.settings.dbos_exporter_endpoint] if app.settings.otel_enabled else []
    ),
    # otlp_traces_endpoints=["http://localhost:4318/v1/traces"]
    run_admin_server=True,
    admin_port=3001,
    application_version="2.8.0",
)

DBOS(fastapi=app, config=dbos_config)
