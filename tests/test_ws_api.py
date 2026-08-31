import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure backend directory is in python module search path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app as fastapi_app

class TestWebSocketAPI(unittest.TestCase):
    def test_websocket_ping_pong(self):
        client = TestClient(fastapi_app)
        with client.websocket_connect("/api/ws/events") as websocket:
            websocket.send_text("ping")
            data = websocket.receive_text()
            self.assertEqual(data, "pong")

if __name__ == "__main__":
    unittest.main()
