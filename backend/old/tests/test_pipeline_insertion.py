import pytest
from azure.core.exceptions import ResourceExistsError
from unittest.mock import patch, Mock
from pipelines.pipelines_version_insertion import (
    insert_new_version_pipeline,
    pipeline_insertion,
    PipelineInsertionError,
)

@pytest.fixture
def setup_data():
    return {
        "key": Mock(),
        "account_name": "test_storage",
        "mock_pipeline": {
            "version": "0.0.1",
        }
    }

def test_insert_new_version_pipeline_success(setup_data):
    expected_message = "The pipeline was successfully uploaded to the blob storage"

    mock_container_client = Mock()
    mock_container_client.upload_blob.return_value = True

    mock_blob_service_client = Mock()
    mock_blob_service_client.get_container_client.return_value = (
        mock_container_client
    )

    result = insert_new_version_pipeline(
        setup_data["mock_pipeline"], mock_blob_service_client, setup_data["account_name"])

    assert result == expected_message

@patch("pipelines.pipelines_version_insertion.Data")
@patch("pipelines.pipelines_version_insertion.yaml_to_json")
@patch("os.path.exists")
def test_pipeline_insertion_resouce_exists_error(mock_os_path_exists, mock_yaml_to_json, mock_data, setup_data):

    mock_yaml_to_json.return_value = {
        "version": "0.0.0",
        "date": "2021-01-01",
        "pipelines": [{"models":1, "default": True}],
        "models": [],
    }
    mock_os_path_exists.return_value = True
    mock_data.return_value = Mock()

    mock_blob_client = Mock()
    mock_blob_client.get_container_client.side_effect = ResourceExistsError("Resource not found")

    with pytest.raises(PipelineInsertionError) as exc_info:
        pipeline_insertion("test_file.yaml", mock_blob_client, Mock(), setup_data["account_name"])
    assert str(exc_info.value) == """an error occurred while uploading the file to the blob storage:
            \n Resource not found"""

def test_pipeline_insertion_file_not_exist(setup_data):
    expected = """
            \nthe file does not exist, please check the file path
            \nprovided path: test_file.yaml
            """

    with pytest.raises(PipelineInsertionError) as exc_info:
        pipeline_insertion("test_file.yaml", Mock(), Mock(), setup_data["account_name"])
    assert str(exc_info.value) == expected

@patch("os.path.exists")
def test_pipeline_insertion_file_extension_not_supported(mock_os_path_exists, setup_data):
    expected = """\nthe file must be a json, a yaml or yml file,
            \nplease check the file extension\nprovided extension: md"""

    mock_os_path_exists.return_value = True

    with pytest.raises(PipelineInsertionError) as exc_info:
        pipeline_insertion("test_file.md", Mock(), Mock(), setup_data["account_name"])
    assert str(exc_info.value) == expected

@patch("pipelines.pipelines_version_insertion.yaml_to_json")
@patch("os.path.exists")
def test_pipeline_insertion_not_dict(mock_os_path_exists, mock_yaml_to_json, setup_data):
    expected = """\nthe file must contain a dictionary with the following keys:
            \n version, date, pipelines, models \n instead provided a <class 'list'>
            """
    mock_os_path_exists.return_value = True
    mock_yaml_to_json.return_value = []

    with pytest.raises(PipelineInsertionError) as exc_info:
        pipeline_insertion("test_file.yaml", Mock(), Mock(), setup_data["account_name"])
    assert str(exc_info.value) == expected

@patch("pipelines.pipelines_version_insertion.yaml_to_json")
@patch("os.path.exists")
def test_pipeline_insertion_fail_validation(mock_os_path_exists, mock_yaml_to_json, setup_data):
    mock_os_path_exists.return_value = True
    mock_yaml_to_json.return_value = {
        "version": "0.0.0",
        "date": "2021-01-01",
        "pipelines": [{"models":1}],
        "models": [],
    }

    # Missing argument and Wrong Type
    with pytest.raises(PipelineInsertionError) as exc_info:
        pipeline_insertion("test_file.yaml", Mock(), Mock(), setup_data["account_name"])

    assert "validation errors" in str(exc_info.value)

@patch("pipelines.pipelines_version_insertion.yaml_to_json")
@patch("os.path.exists")
def test_pipeline_insertion_fail_no_default(mock_os_path_exists, mock_yaml_to_json, setup_data):
    mock_os_path_exists.return_value = True
    mock_yaml_to_json.return_value = {
        "version": "0.0.0",
        "date": "2021-01-01",
        "pipelines": [
                {
                    "models": ["test_model"],
                    "pipeline_name": "p_test",
                    "created_by": "test",
                    "creation_date": "test",
                    "version": 1,
                    "description": "test",
                    "job_name": "test",
                    "dataset_description": "test",
                    "accuracy": 0.0,
                    "default": False
                }
            ],
        "models": [
            {
                "task": "test",
                "endpoint": "test",
                "api_key": "test",
                "content_type": "test",
                "deployment_platform": "test",
                "endpoint_name": "test",
                "model_name": "test_model",
                "created_by": "test",
                "creation_date": "test",
                "version": 1,
                "description": "test",
                "job_name": "test",
                "dataset_description": "test",
                "accuracy": 0.0
            }
        ],
    }

    expected = "no pipeline was set as default, please set one by setting the default value as True"
    with pytest.raises(PipelineInsertionError) as exc_info:
        pipeline_insertion("test_file.yaml", Mock(), Mock(), setup_data["account_name"])

    assert str(exc_info.value) == expected
