import unittest
import asyncio

from app import app

class TestQuartHealth(unittest.TestCase):
    def test_health(self):
        test = app.test_client()

        response = asyncio.run(
            test.get('/health')
        )
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
