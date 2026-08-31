import os
import sys
import unittest
import tempfile
import shutil
from fastapi.testclient import TestClient

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app as fastapi_app
from app.db.session import Base, engine, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

class TestFolderAndExplorerAPI(unittest.TestCase):
    def setUp(self):
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        self.TestSession = sessionmaker(bind=self.test_engine)

        def override_get_db():
            db = self.TestSession()
            try:
                yield db
            finally:
                db.close()

        fastapi_app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(fastapi_app)

        self.temp_dir = tempfile.mkdtemp()
        self.test_img = os.path.join(self.temp_dir, "sample.jpg")
        with open(self.test_img, "wb") as f:
            f.write(b"dummy image bytes")

    def tearDown(self):
        fastapi_app.dependency_overrides.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_folder_crud_and_scan_api(self):
        # 1. Create folder
        create_res = self.client.post("/api/folders", json={
            "path": self.temp_dir,
            "name": "My Photo Album",
            "is_recursive": True,
            "auto_tag_folder": True,
            "custom_tags": ["Album2026"]
        })
        self.assertEqual(create_res.status_code, 201)
        folder_data = create_res.json()
        folder_id = folder_data["id"]
        self.assertEqual(folder_data["name"], "My Photo Album")

        # 2. Get list of folders
        list_res = self.client.get("/api/folders")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()), 1)

        # 3. Scan folder
        scan_res = self.client.post(f"/api/folders/{folder_id}/scan")
        self.assertEqual(scan_res.status_code, 200)
        scan_data = scan_res.json()
        self.assertEqual(scan_data["newly_indexed"], 1)

        # 4. Fetch assets via inventory to check tags
        inv_res = self.client.get("/api/assets")
        self.assertEqual(inv_res.status_code, 200)
        assets = inv_res.json()["items"]
        self.assertEqual(len(assets), 1)
        asset_id = assets[0]["id"]
        tags = [t["name"] for t in assets[0]["tags"]]
        self.assertIn("#jpg", tags)
        self.assertIn("#Album2026", tags)

        # 5. Rename via explorer API
        rename_res = self.client.post("/api/explorer/rename", json={
            "asset_id": asset_id,
            "new_name": "renamed_sample.jpg"
        })
        self.assertEqual(rename_res.status_code, 200)
        self.assertEqual(rename_res.json()["name"], "renamed_sample.jpg")

        # 6. Delete folder
        del_res = self.client.delete(f"/api/folders/{folder_id}")
        self.assertEqual(del_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
