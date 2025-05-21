"""
This module provides functionality to insert a new version of a pipeline
into an Azure Blob Storage container.

Usage:
1. Ensure that the required environment variables are set:
    - NACHET_BLOB_PIPELINE_DECRYPTION_KEY: The decryption key for the pipeline.
    - NACHET_BLOB_PIPELINE_NAME: The name of the Azure Blob Storage account.
    - NACHET_AZURE_STORAGE_CONNECTION_STRING: The connection string for the
      Azure Blob Storage account.

2. Call the `pipeline_version_insertion.py` file with the path to the file
    containing the pipeline data as an argument directly in the terminal.
    Example: pipelines/pipeline_version_insertion.py /path/to/pipeline.yaml

3. The function will read the file, encrypt the endpoint and API key, and
   upload the pipeline to the specified Azure Blob Storage container.

4. If successful, the function will return a message indicating that the
   pipeline was successfully uploaded.

Note:
- The file must be a dictionary with the following keys: version, date,
    pipelines, models.
- Supported formats are json, yaml and yml.
- At least one of the pipelines must be set as default (default: True).
- Refer to pipeline_template.yaml to see the expected structure of the file.
- The endpoint and API key in each model will be encrypted using the provided
    decryption key.
- The pipeline will be uploaded to the container named by the environment
    variable NACHET_BLOB_PIPELINE_NAME.
- The connection string for the Azure Blob Storage account is specified by the
    environment variable NACHET_AZURE_STORAGE_CONNECTION_STRING.
- External dependencies:
    - azure-storage-blob==12.8.0
    - cryptography==3.4.7
    - python-dotenv==0.17.1
    - pyyaml==5.4.1
    - pydantic==1.8.2
"""

import os
import json
import yaml
import datetime
import sys

from pydantic import BaseModel, ValidationError, field_validator
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("NACHET_BLOB_PIPELINE_DECRYPTION_KEY")
BLOB_STORAGE_ACCOUNT_NAME = os.getenv("NACHET_BLOB_PIPELINE_NAME")
CONNECTION_STRING = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")

NO_DEFAULT_MSG = "no pipeline was set as default, please set one by setting the default value as True"

class PipelineInsertionError(Exception):
    pass


class Pipeline(BaseModel):
    models: list
    pipeline_name: str
    created_by: str
    creation_date: str
    version: int
    description: str
    job_name: str
    dataset_description: str
    accuracy: float
    default: bool

    @field_validator ("*", mode="before", check_fields=True)
    def validate_data(cls, v):
        if v is None:
            return ""
        return v

    @field_validator ("models", mode="before", check_fields=True)
    def validate_list(cls, v):
        if v is None:
            return []
        return v

    class Config:
        protected_namespaces = ()


class Model(BaseModel):
    task: str
    endpoint: str
    api_key: str
    content_type: str
    deployment_platform: str
    endpoint_name: str
    model_name: str
    created_by: str
    creation_date: str
    version: int
    description: str
    job_name: str
    dataset_description: str
    accuracy: float

    @field_validator ("*", mode="before", check_fields=True)
    def validate_data(cls, v):
        if v is None:
            return ""
        return v

    @field_validator ("deployment_platform", mode="before", check_fields=True)
    def validate_dict(cls, v):
        if v is None:
            return {}
        return v

    class Config:
        protected_namespaces = ()


class Data(BaseModel):
    version: str
    date: datetime.date
    pipelines: list
    models: list

    @field_validator ("pipelines", mode="before", check_fields=True)
    def validate_pipelines(cls, v):
        for p in v:
            Pipeline(**p)
        return v

    @field_validator ("models", mode="before", check_fields=True)
    def validate_models(cls, v):
        for m in v:
            Model(**m)
        return v


def insert_new_version_pipeline(
        pipeline: dict,
        blob_service_client: BlobServiceClient,
        pipeline_container_name: str
    ) -> str:
    """
    Inserts a new version of a pipeline into an Azure Blob Storage
    container.

    Args:
        pipeline (dict): The data of the pipeline.
        blob_service_client (BlobServiceClient): The blob service client
            to insert the new pipelines.
        pipeline_container_name (str): The name of the container where the
            pipeline will be uploaded.
    Returns:
        str: A message indicating whether the pipeline was successfully uploaded.
    """
    container_client = blob_service_client.get_container_client(
        pipeline_container_name
    )

    name = "{}/{}.json".format("pipelines", pipeline.get("version"))
    container_client.upload_blob(
        name, json.dumps(pipeline, indent=4), overwrite=False)
    return "The pipeline was successfully uploaded to the blob storage"


def yaml_to_json(yaml_file:str) -> str:
    """
    Converts a YAML file to JSON format.

    Args:
        yaml_file (str): The path to the YAML file.

    Returns:
        str: The JSON representation of the YAML data.
    """

    def convert_datetime_to_string(data: dict) -> dict:
        """
        Converts datetime objects in a dictionary to string format.

        Args:
            data (dict): The dictionary containing the data.

        Returns:
            dict: The dictionary with datetime objects converted to string format.
        """
        for key in data:
            if isinstance(data[key], datetime.date):
              data[key] = data[key].strftime("%Y-%m-%d")
            if isinstance(data[key], list):
                for elem in data[key]:
                    for key, value in elem.items():
                        if isinstance(value, datetime.date):
                            elem[key] = value.strftime("%Y-%m-%d")

    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)
        convert_datetime_to_string(data)
    return data


def pipeline_insertion(
        file_path: str,
        blob_service_client: BlobServiceClient,
        cipher_suite: Fernet,
        account_name: str
) -> str:
    """
    Inserts a new version of a pipeline into an Azure Blob Storage container.

    Args:
        file_path (str): The path to the file containing the pipeline data.
        blob_service_client (BlobServiceClient): The BlobServiceClient object for accessing Azure Blob Storage.
        cipher_suite (Fernet): The Fernet cipher suite for encrypting sensitive data.

    Returns:
        str: A message indicating the success or failure of the pipeline insertion.

    Raises:
        PipelineInsertionError: If the file does not exist, has an invalid extension, or contains invalid data.
    """
    if not os.path.exists(file_path):
        raise PipelineInsertionError(
            f"""
            \nthe file does not exist, please check the file path
            \nprovided path: {file_path}
            """
        )

    extension = file_path.split(".")[-1]

    if extension not in {"json", "JSON","yaml", "yml"}:
        raise PipelineInsertionError(
            f"""\nthe file must be a json, a yaml or yml file,
            \nplease check the file extension\nprovided extension: {extension}""")

    if extension not in {"json", "JSON"}:
        pipelines = yaml_to_json(file_path)

    else:
        with (open(file_path, "r")) as file:
            data = file.read()
            pipelines = json.loads(data)

    if not isinstance(pipelines, dict):
        raise PipelineInsertionError(
            f"""\nthe file must contain a dictionary with the following keys:
            \n version, date, pipelines, models \n instead provided a {type(pipelines)}
            """
        )
    try:
        # Validate the data given by the users
        Data(**pipelines)
        for pipeline in pipelines["pipelines"]:
            if pipeline.get("default"):
                print(f"pipeline {pipeline.get('pipeline_name')} is set as default")
                break
        else:
            raise PipelineInsertionError(NO_DEFAULT_MSG)
    except ValidationError as error:
        raise PipelineInsertionError(error) from error

    try:
        for model in pipelines["models"]:
            # The encryption of the endpoint and the API Key is important
            # because they are sensible data that should not be exposed
            endpoint = model["endpoint"].encode()
            model["endpoint"] = cipher_suite.encrypt(endpoint).decode()
            api_key = model["api_key"].encode()
            model["api_key"] = cipher_suite.encrypt(api_key).decode()


        return insert_new_version_pipeline(
            pipelines, blob_service_client, account_name)

    except ResourceExistsError as error:
        raise PipelineInsertionError(
            f"""an error occurred while uploading the file to the blob storage:
            \n {error.args[0]}""") from error


def main():
    if CONNECTION_STRING == "" or KEY == "" or BLOB_STORAGE_ACCOUNT_NAME == "":
        raise ValueError(
            "please set the environment variables NACHET_BLOB_PIPELINE_DECRYPTION_KEY, \
            NACHET_BLOB_PIPELINE_NAME and NACHET_AZURE_STORAGE_CONNECTION_STRING"
        )

    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            CONNECTION_STRING
        )
        print(pipeline_insertion(sys.argv[1], blob_service_client, Fernet(KEY), BLOB_STORAGE_ACCOUNT_NAME))
    except (IndexError, PipelineInsertionError) as error:
        if isinstance(error, IndexError):
            print("please provide the path to the file as an argument")

        if isinstance(error, PipelineInsertionError):
            print(error.args[0])


if __name__ == "__main__":
    sys.exit(main())
