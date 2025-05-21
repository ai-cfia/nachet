import unittest
import asyncio

from app import app, json, base64, Image, io
from unittest.mock import patch, Mock


class TestImageValidation(unittest.TestCase):
    def setUp(self):
        self.test_client = app.test_client()

        self.img_byte_array = io.BytesIO()
        image = Image.new('RGB', (150, 150), 'blue')
        self.image_header = "data:image/PNG;base64,"
        image.save(self.img_byte_array, 'PNG')

    def test_real_image_validation(self):
        data = base64.b64encode(self.img_byte_array.getvalue())
        data = data.decode('utf-8')

        response = asyncio.run(
            self.test_client.post(
                '/image-validation',
                headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                },
                data= str.encode(json.dumps({'image': self.image_header + data})),
            ))

        data = json.loads(asyncio.run(response.get_data()))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data[0], str)

    def test_invalid_header(self):
        data = base64.b64encode(self.img_byte_array.getvalue()).decode('utf-8')

        response = asyncio.run(
            self.test_client.post(
                '/image-validation',
                headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                },
                data= str.encode(json.dumps({'image':"data:image/," + data})),
            ))

        data = json.loads(asyncio.run(response.get_data()))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data[0], 'API Error validating image : invalid file header: data:image/')

    @patch("magic.Magic.from_buffer")
    def test_invalid_extension(self, mock_magic_from_buffer):

        mock_magic_from_buffer.return_value = "text/plain"

        data = base64.b64encode(self.img_byte_array.getvalue()).decode('utf-8')

        response = asyncio.run(
            self.test_client.post(
                '/image-validation',
                headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                },
                data= str.encode(json.dumps({'image': self.image_header + data})),
            ))

        data = json.loads(asyncio.run(response.get_data()))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data[0], 'API Error validating image : invalid file extension: plain')

    @patch("PIL.Image.open")
    def test_invalid_size(self, mock_open):
        mock_image = Mock()
        mock_image.size = [2000, 2000]
        mock_image.format = "PNG"

        mock_open.return_value = mock_image

        data = base64.b64encode(self.img_byte_array.getvalue()).decode('utf-8')

        response = asyncio.run(
            self.test_client.post(
                '/image-validation',
                headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                },
                data= str.encode(json.dumps({'image': self.image_header + data})),
            ))

        data = json.loads(asyncio.run(response.get_data()))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data[0], 'API Error validating image : invalid file size: 2000x2000')

    @patch("PIL.Image.open")
    def test_resizable_error(self, mock_open):
        mock_image = Mock()
        mock_image.size = [1080, 1080]
        mock_image.format = "PNG"
        mock_image.thumbnail.side_effect = IOError("error can't resize")

        mock_open.return_value = mock_image

        data = base64.b64encode(self.img_byte_array.getvalue()).decode('utf-8')

        response = asyncio.run(
            self.test_client.post(
                '/image-validation',
                headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                },
                data= str.encode(json.dumps({'image': self.image_header + data})),
            ))

        data = json.loads(asyncio.run(response.get_data()))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data[0], 'API Error validating image : invalid file not resizable')

if __name__ == '__main__':
    unittest.main()
