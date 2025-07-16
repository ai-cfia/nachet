import pytest
import asyncio

from app import app, json, base64, Image, io
from unittest.mock import patch, Mock


@pytest.fixture
def image_validation_setup():
    test_client = app.test_client()

    img_byte_array = io.BytesIO()
    image = Image.new('RGB', (150, 150), 'blue')
    image_header = "data:image/PNG;base64,"
    image.save(img_byte_array, 'PNG')

    return {
        "test_client": test_client,
        "img_byte_array": img_byte_array,
        "image_header": image_header
    }

@pytest.mark.asyncio
async def test_real_image_validation(image_validation_setup):
    setup = image_validation_setup
    data = base64.b64encode(setup["img_byte_array"].getvalue())
    data = data.decode('utf-8')

    response = await setup["test_client"].post(
        '/image-validation',
        headers={
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        },
        data= str.encode(json.dumps({'image': setup["image_header"] + data})),
    )

    data = json.loads(await response.get_data())

    assert response.status_code == 200
    assert isinstance(data[0], str)

@pytest.mark.asyncio
async def test_invalid_header(image_validation_setup):
    setup = image_validation_setup
    data = base64.b64encode(setup["img_byte_array"].getvalue()).decode('utf-8')

    response = await setup["test_client"].post(
        '/image-validation',
        headers={
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        },
        data= str.encode(json.dumps({'image':"data:image/," + data})),
    )

    data = json.loads(await response.get_data())

    assert response.status_code == 400
    assert data[0] == 'API Error validating image : invalid file header: data:image/'

@patch("magic.Magic.from_buffer")
@pytest.mark.asyncio
async def test_invalid_extension(mock_magic_from_buffer, image_validation_setup):
    setup = image_validation_setup
    mock_magic_from_buffer.return_value = "text/plain"

    data = base64.b64encode(setup["img_byte_array"].getvalue()).decode('utf-8')

    response = await setup["test_client"].post(
        '/image-validation',
        headers={
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        },
        data= str.encode(json.dumps({'image': setup["image_header"] + data})),
    )

    data = json.loads(await response.get_data())

    assert response.status_code == 400
    assert data[0] == 'API Error validating image : invalid file extension: plain'

@patch("PIL.Image.open")
@pytest.mark.asyncio
async def test_invalid_size(mock_open, image_validation_setup):
    setup = image_validation_setup
    mock_image = Mock()
    mock_image.size = [2000, 2000]
    mock_image.format = "PNG"

    mock_open.return_value = mock_image

    data = base64.b64encode(setup["img_byte_array"].getvalue()).decode('utf-8')

    response = await setup["test_client"].post(
        '/image-validation',
        headers={
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        },
        data= str.encode(json.dumps({'image': setup["image_header"] + data})),
    )

    data = json.loads(await response.get_data())

    assert response.status_code == 400
    assert data[0] == 'API Error validating image : invalid file size: 2000x2000'

@patch("PIL.Image.open")
@pytest.mark.asyncio
async def test_resizable_error(mock_open, image_validation_setup):
    setup = image_validation_setup
    mock_image = Mock()
    mock_image.size = [1080, 1080]
    mock_image.format = "PNG"
    mock_image.thumbnail.side_effect = IOError("error can't resize")

    mock_open.return_value = mock_image

    data = base64.b64encode(setup["img_byte_array"].getvalue()).decode('utf-8')

    response = await setup["test_client"].post(
        '/image-validation',
        headers={
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        },
        data= str.encode(json.dumps({'image': setup["image_header"] + data})),
    )

    data = json.loads(await response.get_data())

    assert response.status_code == 400
    assert data[0] == 'API Error validating image : invalid file not resizable'