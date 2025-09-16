# import hypercorn
# from fastapi import FastAPI
from app.api.routes import router as api_router
from app.api.config import create_app, lifespan, Settings

app = create_app(Settings(), api_router, lifespan=lifespan)


# if __name__ == "__main__":
#     hypercorn -b "main:app"
