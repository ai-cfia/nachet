# import hypercorn
# from fastapi import FastAPI

print("🔄 Starting main.py imports...")
print("🔄 Importing routes...")
from app.api.routes import router as api_router
print("✅ Routes imported successfully")

print("🔄 Importing config...")
from app.api.config import create_app, lifespan, Settings
print("✅ Config imported successfully")
# from core import config


# def get_application() -> FastAPI:
#     application = FastAPI(
#         title=config.PROJECT_NAME,
#         debug=config.DEBUG,
#         version=config.VERSION,
#         swagger_ui_oauth2_redirect_url='/oauth2-redirect',
#         swagger_ui_init_oauth={
#             "usePkceWithAuthorizationCodeGrant": True,
#             "clientId": config.SWAGGER_UI_CLIENT_ID,
#             "scopes": [f'api://{config.API_CLIENT_ID}/access_as_user']
#         }
#     )
#     application.include_router(api_router)
#     return application


print("🔄 Creating FastAPI app...")
app = create_app(Settings(), api_router, lifespan=lifespan)
print("✅ FastAPI app created successfully")


# if __name__ == "__main__":
#     hypercorn -b "main:app"
