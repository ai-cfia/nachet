import urllib.request
import json
import os
import base64
import re
import io
import magic
import time
import warnings

from PIL import Image
from datetime import date
from dotenv import load_dotenv
from quart import Quart, request, jsonify
from quart_cors import cors
from collections import namedtuple
from cryptography.fernet import Fernet

load_dotenv()  # noqa: E402

import model.inference as inference  # noqa: E402
import storage.datastore_storage_api as datastore  # noqa: E402
from model.model_exceptions import ModelAPIError  # noqa: E402
from model import request_function  # noqa: E402
from datastore import azure_storage  # noqa: E402
from auth.cookie import decode_vouch_cookie  # noqa: E402


class APIError(Exception):
    pass


class MissingArgumentsError(APIError):
    pass


class DeleteDirectoryRequestError(APIError):
    pass


class InferenceRequestError(APIError):
    pass


class CreateDirectoryRequestError(APIError):
    pass


class ServerError(APIError):
    pass


class ImageValidationError(APIError):
    pass


class ValidateEnvVariablesError(APIError):
    pass


class EmailNotSendError(APIError):
    pass


class BatchImportError(APIError):
    pass


class APIWarnings(UserWarning):
    pass


class ImageWarning(APIWarnings):
    pass


class MaxContentLengthWarning(APIWarnings):
    pass


connection_string_regex = r"^DefaultEndpointsProtocol=https?;.*;FileEndpoint=https://[a-zA-Z0-9]+\.file\.core\.windows\.net/;$"
pipeline_version_regex = r"\d.\d.\d"

CONNECTION_STRING = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")

# FERNET_KEY = os.getenv("NACHET_BLOB_PIPELINE_DECRYPTION_KEY")
PIPELINE_VERSION = os.getenv("NACHET_BLOB_PIPELINE_VERSION")
PIPELINE_BLOB_NAME = os.getenv("NACHET_BLOB_PIPELINE_NAME")

NACHET_DATA = os.getenv("NACHET_DATA")
ENVIRONMENT = os.getenv("NACHET_ENV")
NACHET_FRONTEND_DEV_URL = os.getenv("NACHET_FRONTEND_DEV_URL")
NACHET_FRONTEND_PUBLIC_URL = os.getenv("NACHET_FRONTEND_PUBLIC_URL", "").split(",")
ALLOWED_URL = [NACHET_FRONTEND_DEV_URL] if ENVIRONMENT == "local" else NACHET_FRONTEND_PUBLIC_URL

try:
    VALID_EXTENSION = json.loads(os.getenv("NACHET_VALID_EXTENSION"))
    VALID_DIMENSION = json.loads(os.getenv("NACHET_VALID_DIMENSION"))
except (TypeError, json.decoder.JSONDecodeError):
    # For testing
    VALID_DIMENSION = {"width": 1920, "height": 1080}
    VALID_EXTENSION = {"jpeg", "jpg", "png", "gif", "bmp", "tiff", "webp"}
    warnings.warn(
        f"""
        NACHET_VALID_EXTENSION or NACHET_VALID_DIMENSION is not set,
        using default values: {", ".join(list(VALID_EXTENSION))} and dimension: {tuple(VALID_DIMENSION.values())}
        """,
        ImageWarning,
    )

try:
    MAX_CONTENT_LENGTH_MEGABYTES = int(os.getenv("NACHET_MAX_CONTENT_LENGTH"))
except (TypeError, ValueError):
    MAX_CONTENT_LENGTH_MEGABYTES = 16
    warnings.warn(
        f"NACHET_MAX_CONTENT_LENGTH not set, using default value of {MAX_CONTENT_LENGTH_MEGABYTES}",
        MaxContentLengthWarning,
    )


Model = namedtuple(
    "Model",
    [
        "request_function",
        "name",
        "version",
        "endpoint",
        "api_key",
        "content_type",
        "deployment_platform",
    ],
)

CACHE = {"seeds": None, "endpoints": None, "pipelines": {}, "validators": []}

cors_settings = {
    "allow_origin": ALLOWED_URL,
    "allow_methods": ["GET", "POST", "OPTIONS"],
    "allow_credentials": True,
    "max_age": 86400
}

app = Quart(__name__)
app = cors(app, **cors_settings)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MEGABYTES * 1024 * 1024


@app.before_serving
async def before_serving():
    try:
        # Check: do environment variables exist?
        if CONNECTION_STRING is None:
            raise ServerError(
                "Missing environment variable: NACHET_AZURE_STORAGE_CONNECTION_STRING"
            )

        if NACHET_DATA is None:
            raise ServerError("Missing environment variable: NACHET_DATA")

        # if FERNET_KEY is None:
        #     raise ServerError("Missing environment variable: FERNET_KEY")

        if PIPELINE_VERSION is None:
            raise ServerError("Missing environment variable: PIPELINE_VERSION")

        if PIPELINE_BLOB_NAME is None:
            raise ServerError("Missing environment variable: PIPELINE_BLOB_NAME")

        if NACHET_DATA is None:
            raise ServerError("Missing environment variable: NACHET_DATA")

        if not bool(re.match(pipeline_version_regex, PIPELINE_VERSION)):
            raise ServerError("Incorrect environment variable: PIPELINE_VERSION")

        # Store the seeds names and ml structure in CACHE
        CACHE["seeds"] = await datastore.get_all_seeds()
        CACHE["endpoints"] = await get_pipelines()

        print(
            f"""Server start with current configuration:\n
                date: {date.today()}
                file version of pipelines: {PIPELINE_VERSION}
                pipelines: {[pipeline for pipeline in CACHE["pipelines"].keys()]}\n
            """
        )  # TODO Transform into logging

    except (Exception, ServerError, inference.ModelAPIError) as e:
        print(e)
        raise


@app.post("/get-user-id")
async def get_user_id():
    """
    Returns the user id
    """
    try:
        email = None

        if "jxVouchCookie" in request.cookies:
            decoded_cookie = decode_vouch_cookie(request.cookies["jxVouchCookie"])
            # print(decoded_cookie)
            email = decoded_cookie["CustomClaims"]["email"]

        if ENVIRONMENT == "local" and not email:  # only allow local dev requests to bypass email
            data = await request.get_json()
            email = data.get("email")

        if not email:
            email = "example@gmail.com"
            # raise MissingArgumentsError("Missing email")

        user_id = datastore.get_user_id(email)

        return jsonify({"user_id": user_id}), 200

    except datastore.DatastoreError as error:
        print(error)
        return (
            jsonify(
                [f"Datastore Error retrieving user id for email {email} : {str(error)}"]
            ),
            400,
        )
    except (KeyError, TypeError, ValueError, APIError) as error:
        print(error)
        return (
            jsonify([f"API Error retrieving user id for email {email} : {str(error)}"]),
            400,
        )
    except Exception as error:
        print(error)
        return (
            jsonify(
                [f"Unhandled API error : Error retrieving user id for email {email}"]
            ),
            400,
        )


# Deprecated
@app.post("/del")
async def delete_directory():
    """
    deletes a directory in the user's container
    """
    try:
        data = await request.get_json()
        container_name = data.get("container_name")
        folder_name = data.get("folder_name")
        if container_name and folder_name:
            container_client = await azure_storage.mount_container(
                CONNECTION_STRING, container_name, create_container=True
            )
            if container_client:
                folder_uuid = await azure_storage.get_folder_uuid(
                    container_client, folder_name
                )
                if folder_uuid:
                    blob_list = container_client.list_blobs()
                    for blob in blob_list:
                        if blob.name.split("/")[0] == folder_uuid:
                            container_client.delete_blob(blob.name)
                    return jsonify([True]), 200
                else:
                    raise DeleteDirectoryRequestError("directory does not exist")
            else:
                raise DeleteDirectoryRequestError("failed to mount container")
        else:
            raise MissingArgumentsError("missing container or directory name")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error deleting directory : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error deleting directory : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error deleting directory"]), 400


@app.post("/delete-request")
async def delete_request():
    """
    Request to delete a directory in the user's container.

    Return true if there is validated pictuers in it, false otherwise
    """
    try:
        data = await request.get_json()
        user_id = data.get("container_name")
        picture_set_id = data.get("folder_uuid")
        if user_id and picture_set_id:
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            response = await datastore.delete_directory_request(
                cursor, str(user_id), str(picture_set_id)
            )
            # Close connection
            datastore.end_query(connection, cursor)

            return jsonify(response), 200
        else:
            raise MissingArgumentsError("missing container or directory name")

    except datastore.DatastoreError as error:
        print(error)
        return (
            jsonify(
                [f"Datastore Error requesting deletion of directory : {str(error)}"]
            ),
            400,
        )
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return (
            jsonify([f"API Error requesting deletion of directory : {str(error)}"]),
            400,
        )
    except Exception as error:
        print(error)
        return (
            jsonify(["Unhandled API error : Error requesting deletion of directory"]),
            400,
        )


@app.post("/delete-permanently")
async def delete_permanently():
    """
    deletes a directory in the user's container permanently
    """
    try:
        data = await request.get_json()
        container_name = data.get("container_name")
        user_id = container_name
        picture_set_id = data.get("folder_uuid")
        if user_id and picture_set_id:
            container_client = await azure_storage.mount_container(
                CONNECTION_STRING, container_name, create_container=True
            )
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            response = await datastore.delete_directory_permanently(
                cursor, str(user_id), str(picture_set_id), container_client
            )
            # Close connection
            datastore.end_query(connection, cursor)

            return jsonify(response), 200
        else:
            raise MissingArgumentsError("missing container name or directory id")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error deleting directory : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error deleting directory : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error deleting directory"]), 400


@app.post("/delete-with-archive")
async def delete_with_archive():
    """
    deletes a directory in the user's container and saves the validated pictures in the dev user container
    """
    try:
        data = await request.get_json()
        container_name = data.get("container_name")
        user_id = container_name
        picture_set_id = data.get("folder_uuid")
        if user_id and picture_set_id:
            container_client = await azure_storage.mount_container(
                CONNECTION_STRING, container_name, create_container=True
            )
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            response = await datastore.delete_directory_with_archive(
                cursor, str(user_id), str(picture_set_id), container_client
            )
            # Close connection
            datastore.end_query(connection, cursor)

            if response:
                return jsonify(True), 200
        else:
            raise MissingArgumentsError("missing container or directory name")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error deleting directory : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error deleting directory : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error deleting directory"]), 400


# Deprecated
@app.post("/dir")
async def list_directories():
    """
    lists all directories in the user's container
    """
    try:
        data = await request.get_json()
        user_id = data.get("container_name")
        if user_id:
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            directories = await datastore.get_directories(cursor, str(user_id))
            # Close connection
            datastore.end_query(connection, cursor)
            return jsonify(directories)
        else:
            raise MissingArgumentsError("Missing container name")

    except datastore.DatastoreError as error:
        print(error)
        return (
            jsonify([f"Datastore Error retrieving user directories : {str(error)}"]),
            400,
        )
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error retrieving user directories : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error retrieving user directories"]), 400


@app.post("/get-directories")
async def get_directories():
    """
    get all directories in the user's container with pictures names and number of pictures
    """
    try:
        data = await request.get_json()
        user_id = data.get("container_name")
        if user_id:
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            directories_list = await datastore.get_directories(cursor, str(user_id))

            # Close connection
            datastore.end_query(connection, cursor)

            result = {"folders": directories_list}
            return jsonify(result)
        else:
            raise MissingArgumentsError("Missing container name")

    except datastore.DatastoreError as error:
        print(error)
        return (
            jsonify([f"Datastore Error retrieving user directories : {str(error)}"]),
            400,
        )
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error retrieving user directories : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error retrieving user directories"]), 400


@app.post("/get-picture")
async def get_picture():
    """
    get all directories in the user's container with pictures names and number of pictures
    """
    try:
        data = await request.get_json()
        container_name = data.get("container_name")
        user_id = container_name
        picture_id = data.get("picture_id")

        if user_id and picture_id:
            container_client = await azure_storage.mount_container(
                CONNECTION_STRING, container_name, create_container=True
            )
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            picture = {}
            picture["picture_id"] = picture_id

            inference = await datastore.get_inference(
                cursor, str(user_id), str(picture_id)
            )
            picture["inference"] = inference

            blob = await datastore.get_picture_blob(
                cursor, str(user_id), container_client, str(picture_id)
            )
            image_base64 = base64.b64encode(blob)
            picture["image"] = "data:image/tiff;base64," + image_base64.decode("utf-8")

            # Close connection
            datastore.end_query(connection, cursor)
            return jsonify(picture)
        else:
            raise MissingArgumentsError("Missing container name")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error retrieving the picture : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error retrieving the picture : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error retrieving the picture"]), 400


@app.post("/create-dir")
async def create_directory():
    """
    creates a directory in the user's container
    """
    try:
        data = await request.get_json()
        container_name = data.get("container_name")
        user_id = container_name
        folder_name = data.get("folder_name")
        if container_name and folder_name:
            container_client = await azure_storage.mount_container(
                CONNECTION_STRING, container_name, create_container=True
            )
            # Open db connection
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)

            response = await datastore.create_picture_set(
                cursor, container_client, user_id, 0, folder_name
            )
            # Close connection
            datastore.end_query(connection, cursor)
            if response:
                return jsonify([response]), 200
            else:
                raise CreateDirectoryRequestError("Error while creating directory")
        else:
            raise MissingArgumentsError("missing container or directory name")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error creating directory : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error creating directory : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error creating directory"]), 400


@app.post("/image-validation")
async def image_validation():
    """
    Validates an image based on its extension, header, size, and resizability.

    Returns:
        A JSON response containing a validator hash.

    Raises:
        ImageValidationError: If the image fails any of the validation checks.
    """
    try:
        data = await request.get_json()
        image_base64 = data.get("image")

        if not image_base64:
            raise MissingArgumentsError("Missing image")

        header, encoded_image = image_base64.split(",", 1)
        image_bytes = base64.b64decode(encoded_image)

        image = Image.open(io.BytesIO(image_bytes))

        # size check
        if (
            image.size[0] > VALID_DIMENSION["width"]
            and image.size[1] > VALID_DIMENSION["height"]
        ):
            raise ImageValidationError(
                f"invalid file size: {image.size[0]}x{image.size[1]}"
            )

        # resizable check
        try:
            size = (100, 150)
            image.thumbnail(size)
        except IOError:
            raise ImageValidationError("invalid file not resizable")

        magic_header = magic.from_buffer(image_bytes, mime=True)
        image_extension = magic_header.split("/")[1]

        # extension check
        if image_extension not in VALID_EXTENSION:
            raise ImageValidationError(f"invalid file extension: {image_extension}")

        expected_header = f"data:image/{image_extension};base64"

        # header check
        if header.lower() != expected_header:
            raise ImageValidationError(f"invalid file header: {header}")

        validator = await azure_storage.generate_hash(image_bytes)
        CACHE["validators"].append(validator)

        return jsonify([validator]), 200

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error validating image : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error validating image : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error validating image"]), 400


@app.post("/inf")
async def inference_request():
    """
    Performs inference on an image, and returns the results.
    The image and inference results are uploaded to a folder in the user's container.
    """

    seconds = time.perf_counter()  # TODO: transform into logging
    try:
        print(
            f"{date.today()} Entering inference request"
        )  # TODO: Transform into logging
        data = await request.get_json()
        pipeline_name = data.get("model_name")
        validator = data.get("validator")
        folder_name = data.get("folder_name")
        container_name = data.get("container_name")
        imageDims = data.get("imageDims")
        image_base64 = data.get("image")
        user_id = container_name

        area_ratio = data.get("area_ratio", 0.5)
        color_format = data.get("color_format", "hex")

        print(f"Requested by user: {container_name}")  # TODO: Transform into logging
        pipelines_endpoints = CACHE.get("pipelines")
        validators = CACHE.get("validators")

        if not (folder_name and container_name and imageDims and image_base64):
            raise MissingArgumentsError(
                "missing request arguments: either folder_name, container_name, imageDims or image is missing"
            )

        if not pipelines_endpoints.get(pipeline_name):
            raise InferenceRequestError(f"model {pipeline_name} not found")

        _, encoded_data = image_base64.split(",", 1)

        if validator not in validators:
            warnings.warn("this picture was not validate", ImageWarning)
            # TODO: implement logic when frontend start returning validators

        # Keep track of every output given by the models
        # TODO: add it to CACHE variable
        cache_json_result = [encoded_data]
        image_bytes = base64.b64decode(encoded_data)

        print(f"Mounting containerb {container_name}")  # TODO: Transform into logging
        mount_container_time = time.perf_counter()
        container_client = await azure_storage.mount_container(
            CONNECTION_STRING, container_name, create_container=True
        )
        print(f"Time mount_container: {time.perf_counter() - mount_container_time} seconds")

        # Open db connection
        connection = datastore.get_connection()
        cursor = datastore.get_cursor(connection)

        print("Get picture id")  # TODO: Transform into logging
        get_picture_id_time = time.perf_counter()
        picture_id = await datastore.get_picture_id(
            cursor, user_id, image_bytes, container_client
        )
        print(f"Time get_picture_id: {time.perf_counter() - get_picture_id_time} seconds")
        
        # Close connection
        datastore.end_query(connection, cursor)

        pipeline = pipelines_endpoints.get(pipeline_name)

        
        for idx, model in enumerate(pipeline):
            model_time = time.perf_counter()
            print(
                f"Entering {model.name.upper()} model"
            )  
            print(f"Request function: {model.request_function}")  # TODO: Transform into logging
            result_json = await model.request_function(model, cache_json_result[idx])
            cache_json_result.append(result_json)
            print(f"Time {model.name}: {time.perf_counter() - model_time} seconds")
        print("End of inference request")  # TODO: Transform into logging
        
        print("Process results")  # TODO: Transform into logging
        processed_result_json = await inference.process_inference_results(
            cache_json_result[-1], imageDims, area_ratio, color_format
        )

        print("Record model")  # TODO: Transform into logging
        record_model_time = time.perf_counter()
        await record_model(pipeline, processed_result_json)
        print(f"Time record_model: {time.perf_counter() - record_model_time} seconds")

        # Open db connection
        connection = datastore.get_connection()
        cursor = datastore.get_cursor(connection)

        print("Save inference result")  # TODO: Transform into logging
        save_inference_time = time.perf_counter()
        saved_result_json = await datastore.save_inference_result(
            cursor, user_id, processed_result_json[0], picture_id, pipeline_name, 1
        )
        print(f"Time save_inference_result: {time.perf_counter() - save_inference_time} seconds")

        # Close connection
        datastore.end_query(connection, cursor)

        # return the inference results to the client
        print(
            f"Took: {'{:10.4f}'.format(time.perf_counter() - seconds)} seconds"
        )  # TODO: Transform into logging
        return jsonify(saved_result_json), 200

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error during classification : {str(error)}"]), 400
    except (KeyError, TypeError, APIError, ModelAPIError) as error:
        print(error)
        return jsonify([f"API Error during classification : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error during classification"]), 400


@app.get("/seed-data/<seed_name>")
async def get_seed_data(seed_name):
    """
    Returns JSON containing requested seed data
    """
    if seed_name in CACHE["seeds"]:
        return jsonify(CACHE["seeds"][seed_name]), 200
    else:
        return jsonify(f"No information found for {seed_name}."), 400


@app.get("/reload-seed-data")
async def reload_seed_data():
    """
    Reloads seed data JSON document from Nachet-Data
    """
    try:
        await fetch_json(NACHET_DATA, "seeds", "seeds/all.json")
        return jsonify(["Seed data reloaded successfully"]), 200
    except Exception as error:
        print(error)
        return (
            jsonify(
                [
                    f"Unhandled API error : An error happend when reloading the seed data: {error.args[0]}"
                ]
            ),
            400,
        )


@app.get("/model-endpoints-metadata")
async def get_model_endpoints_metadata():
    """
    Returns JSON containing the deployed endpoints' metadata
    """
    if CACHE["endpoints"]:
        return jsonify(CACHE["endpoints"]), 200
    else:
        return jsonify("Error retrieving model endpoints metadata.", 400)


@app.get("/seeds")
async def get_seeds():
    """
    Returns JSON containing the model seeds metadata
    """
    seeds = await datastore.get_all_seeds()
    CACHE["seeds"] = seeds
    if seeds:
        return jsonify(seeds), 200
    else:
        return jsonify("Error retrieving seeds", 400)


@app.post("/feedback-positive")
async def feedback_positive():
    """
       Receives inference feedback from the user and stores it in the database.
       --> Perfect Inference Feedback :
               - send the user_id and the inference_id to the datastore so the inference will be verified and not modified
    Params :
       - user_id : the user id that send the feedback
       - inference_id : the inference id that the user want to modify
       - boxes_id : the boxes id that the user want to modify
    """
    try:
        data = await request.get_json()

        if not ("userId" in data and "inferenceId" in data and "boxes" in data):
            raise BatchImportError(
                "missing request arguments: either userId, inferenceId or boxes is missing"
            )

        user_id = data["userId"]
        inference_id = data["inferenceId"]

        for box in data["boxes"]:
            if "boxId" not in box:
                raise BatchImportError(
                    "missing request arguments: boxId is missing in boxes"
                )

        boxes_id = [box["boxId"] for box in data["boxes"]]

        if inference_id and user_id and boxes_id:
            connection = datastore.get_connection()
            cursor = datastore.get_cursor(connection)
            await datastore.save_perfect_feedback(
                cursor, inference_id, user_id, boxes_id
            )
            inference = await datastore.get_inference(
                cursor, str(user_id), None, inference_id=str(inference_id)
            )
            datastore.end_query(connection, cursor)
            return jsonify(inference), 200
        else:
            raise MissingArgumentsError("missing argument(s)")
    except datastore.DatastoreError as error:
        print(error)
        return (
            jsonify([f"Datastore Error giving a positive feedback : {str(error)}"]),
            400,
        )
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error giving a positive feedback : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error giving a positive feedback"]), 400


@app.post("/feedback-negative")
async def feedback_negative():
    """
    Receives inference feedback from the user and stores it in the database.
    --> Annoted Inference Feedback :
            - send the user_id and the inference_id to the datastore so the inference will be verified
            - also send the feedback to the datastore to modified the inference

    Params :
    - inference_feedback : correction of the inference from the user if not a perfect inference
    - user_id : the user id that send the feedback
    - inference_id : the inference id that the user want to modify
    - boxes_id : the boxes id that the user want to modify
    """
    try:
        data = await request.get_json()

        if not ("userId" in data and "inferenceId" in data and "boxes" in data):
            raise MissingArgumentsError(
                "missing request arguments: either userId, inferenceId or boxes is missing"
            )
        user_id = data.get("userId")
        inference_id = data.get("inferenceId")
        boxes = data.get("boxes")
        for object in boxes:
            if not (
                "boxId" in object
                and "label" in object
                and "classId" in object
                and "box" in object
            ):
                raise MissingArgumentsError(
                    "missing request arguments: either boxId, label, box or classId is missing in boxes"
                )

        connection = datastore.get_connection()
        cursor = datastore.get_cursor(connection)
        await datastore.save_annoted_feedback(cursor, data)
        inference = await datastore.get_inference(
            cursor, str(user_id), None, inference_id=str(inference_id)
        )
        datastore.end_query(connection, cursor)
        return jsonify(inference), 200

    except datastore.DatastoreError as error:
        print(error)
        return (
            jsonify([f"Datastore Error giving a negative feedback : {str(error)}"]),
            400,
        )
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error giving a negative feedback : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error giving a negative feedback"]), 400


@app.post("/new-batch-import")
async def new_batch_import():
    """
    Uploads pictures to the user's container
    """
    try:
        data = await request.get_json()

        if not ("container_name" in data and "nb_pictures" in data):
            raise MissingArgumentsError(
                "missing request arguments: either container_name or nb_pictures is missing"
            )

        container_name = data.get("container_name")
        user_id = container_name
        folder_name = data.get("folder_name")
        if folder_name == "":
            folder_name = None
        nb_pictures = data.get("nb_pictures")

        if not container_name or not (isinstance(nb_pictures, int)) or nb_pictures <= 0:
            raise MissingArgumentsError(
                "wrong request arguments: either container_name or nb_pictures is wrong"
            )

        container_client = await azure_storage.mount_container(
            CONNECTION_STRING, container_name, create_container=True
        )

        connection = datastore.get_connection()
        cursor = datastore.get_cursor(connection)
        picture_set_id = await datastore.create_picture_set(
            cursor, container_client, user_id, nb_pictures, folder_name
        )
        datastore.end_query(connection, cursor)
        if picture_set_id:
            return jsonify({"session_id": picture_set_id}), 200
        else:
            raise APIError("failed to create picture set")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error initiating batch upload : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error initiating batch upload : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error initiating batch upload"]), 400


@app.post("/upload-picture")
async def upload_picture():
    """
    Uploads pictures to the user's container
    """
    try:
        data = await request.get_json()

        container_name = data.get("container_name")
        user_id = container_name
        seed_name = data.get("seed_name")
        seed_id = data.get("seed_id")
        zoom_level = data.get("zoom_level")
        nb_seeds = data.get("nb_seeds")
        image_base64 = data.get("image")
        picture_set_id = data.get("session_id")

        if not (
            container_name
            and (seed_name or seed_id)
            and image_base64
            and picture_set_id
        ):
            raise MissingArgumentsError(
                "missing request arguments: either seed_name, session_id, container_name or image is missing"
            )

        container_client = await azure_storage.mount_container(
            CONNECTION_STRING, container_name, create_container=True
        )

        _, encoded_data = image_base64.split(",", 1)

        image_bytes = base64.b64decode(encoded_data)

        connection = datastore.get_connection()
        cursor = datastore.get_cursor(connection)
        response = await datastore.upload_pictures(
            cursor,
            user_id,
            picture_set_id,
            container_client,
            [image_bytes],
            seed_name,
            seed_id,
            zoom_level,
            nb_seeds,
        )
        datastore.end_query(connection, cursor)

        if response:
            return jsonify([True]), 200
        else:
            raise APIError("failed to upload pictures")

    except datastore.DatastoreError as error:
        print(error)
        return jsonify([f"Datastore Error uploading picture : {str(error)}"]), 400
    except (KeyError, TypeError, APIError) as error:
        print(error)
        return jsonify([f"API Error uploading picture : {str(error)}"]), 400
    except Exception as error:
        print(error)
        return jsonify(["Unhandled API error : Error uploading picture"]), 400


@app.get("/health")
async def health():
    return "ok", 200


@app.get("/test")
async def test():
    # Build test pipeline
    CACHE["endpoints"] = [{"pipeline_name": "test_pipeline", "models": ["test_model1"]}]
    # Built test model
    m = Model(
        request_function["test"],
        "test_model1",
        1,
        "http://localhost:8080/test_model1",
        "test_api_key",
        "application/json",
        "test_platform",
    )

    CACHE["pipelines"]["test_pipeline"] = (m,)

    return CACHE["endpoints"], 200


async def record_model(pipeline: namedtuple, result: list):
    new_entry = [{"name": model.name, "version": model.version} for model in pipeline]
    result[0]["models"] = new_entry
    return json.dumps(result, indent=4)


async def fetch_json(repo_URL, key, file_path):
    """
    Fetches JSON document from a GitHub repository.

    Parameters:
    - repo_URL (str): The URL of the GitHub repository.
    - key (str): The key to identify the JSON document.
    - file_path (str): The path to the JSON document in the repository.

    Returns:
    - dict: The JSON document as a Python dictionary.
    """
    if key != "endpoints":
        json_url = os.path.join(repo_URL, file_path)
        with urllib.request.urlopen(json_url) as response:
            result = response.read()
            result_json = json.loads(result.decode("utf-8"))
        return result_json


# async def get_pipelines(cipher_suite=Fernet(FERNET_KEY)):
async def get_pipelines():
    """
    Retrieves the pipelines from the Azure storage API.

    Returns:
    - list: A list of dictionaries representing the pipelines.
    """
    result_json = await datastore.get_pipelines()

    models = ()
    for model in result_json.get("models"):
        m = Model(
            request_function.get(model.get("model_name")),
            model.get("model_name"),
            model.get("version"),
            # To protect sensible data (API key and model endpoint), we encrypt it when
            # it's pushed into the blob storage. Once we retrieve the data here in the
            # backend, we need to decrypt the byte format to recover the original
            # data.
            # cipher_suite.decrypt(model.get("endpoint").encode()).decode(),
            # cipher_suite.decrypt(model.get("api_key").encode()).decode(),
            model.get("endpoint"),
            model.get("api_key"),
            model.get("content_type"),
            model.get("deployment_platform"),
        )
        # if the model is not already in the tuple
        if m not in models:
            models += (m,)
    # Build the pipeline to call the models in order in the inference request
    for pipeline in result_json.get("pipelines"):
        CACHE["pipelines"][pipeline.get("pipeline_name")] = tuple(
            [m for m in models if m.name in pipeline.get("models")]
        )

    return result_json.get("pipelines")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
