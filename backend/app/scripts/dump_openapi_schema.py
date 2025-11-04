# Dump the OpenAPI schema to a file
from fastapi.openapi.utils import get_openapi
from app.api.routes import router as api_router
from app.api.config import create_app, lifespan, Settings

app = create_app(Settings(), api_router, lifespan=lifespan)


# Function to generate and save the OpenAPI JSON
def generate_openapi_json():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        routes=app.routes,
    )
    import json

    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
        # add newline at the end of the file
        f.write("\n")


if __name__ == "__main__":
    generate_openapi_json()
    print("OpenAPI JSON generated and saved to openapi.json")
