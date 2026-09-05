import os
import sys
import unittest
import tempfile
import shutil
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in python module search path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import app.models
from app.db.session import Base, get_db
from app.models.asset import Asset
from app.models.library_folder import LibraryFolder
from app.repositories.asset_repository import AssetRepository
from app.repositories.library_folder_repository import LibraryFolderRepository
from app.services.thumbnail_service import ThumbnailService
from app.main import app as fastapi_app

class TestThumbnailAndCache(unittest.TestCase):
    def setUp(self):
        # Create isolated in-memory SQLite database
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

        # Temporary directories for files & cache
        self.temp_dir = tempfile.mkdtemp()
        self.temp_cache = tempfile.mkdtemp()
        self.thumbnail_service = ThumbnailService(cache_dir=self.temp_cache)

        # Create dummy test image
        self.img_path = os.path.join(self.temp_dir, "sample.jpg")
        img = Image.new("RGB", (600, 400), color=(73, 109, 137))
        img.save(self.img_path, "JPEG")

    def tearDown(self):
        fastapi_app.dependency_overrides.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.temp_cache, ignore_errors=True)

    def test_image_thumbnail_generation(self):
        db = self.TestSession()
        asset_repo = AssetRepository(db)

        asset = Asset(
            name="sample.jpg",
            original_name="sample.jpg",
            mime_type="image/jpeg",
            size_bytes=os.path.getsize(self.img_path),
            storage_path=self.img_path
        )
        saved = asset_repo.save(asset)

        # Generate thumbnail
        thumb_path = self.thumbnail_service.get_or_generate_thumbnail(
            db=db,
            asset_id=saved.id,
            width=200,
            height=200
        )

        self.assertIsNotNone(thumb_path)
        self.assertTrue(os.path.exists(thumb_path))
        self.assertTrue(thumb_path.endswith(".webp"))

        # Verify output image properties
        with Image.open(thumb_path) as thumb_img:
            self.assertEqual(thumb_img.format, "WEBP")
            self.assertLessEqual(thumb_img.width, 200)
            self.assertLessEqual(thumb_img.height, 200)

        # Verify stats
        stats = self.thumbnail_service.get_cache_stats()
        self.assertEqual(stats["total_cached_thumbnails"], 1)
        db.close()

    def test_video_thumbnail_generation(self):
        db = self.TestSession()
        asset_repo = AssetRepository(db)

        # Create dummy test video path
        video_path = os.path.join(self.temp_dir, "sample.mp4")
        with open(video_path, "wb") as f:
            f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")

        asset = Asset(
            name="sample.mp4",
            original_name="sample.mp4",
            mime_type="video/mp4",
            size_bytes=os.path.getsize(video_path),
            storage_path=video_path
        )
        saved = asset_repo.save(asset)

        # Generate video thumbnail
        thumb_path = self.thumbnail_service.get_or_generate_thumbnail(
            db=db,
            asset_id=saved.id,
            width=200,
            height=200
        )

        self.assertIsNotNone(thumb_path)
        self.assertTrue(os.path.exists(thumb_path))
        self.assertTrue(thumb_path.endswith(".webp"))

        with Image.open(thumb_path) as thumb_img:
            self.assertEqual(thumb_img.format, "WEBP")
            self.assertLessEqual(thumb_img.width, 200)
            self.assertLessEqual(thumb_img.height, 200)

        db.close()

    def test_cache_clearing(self):
        db = self.TestSession()
        asset_repo = AssetRepository(db)

        asset = Asset(
            name="sample.jpg",
            original_name="sample.jpg",
            mime_type="image/jpeg",
            size_bytes=os.path.getsize(self.img_path),
            storage_path=self.img_path
        )
        saved = asset_repo.save(asset)

        # Generate thumbnail
        self.thumbnail_service.get_or_generate_thumbnail(db, saved.id)
        self.assertEqual(self.thumbnail_service.get_cache_stats()["total_cached_thumbnails"], 1)

        # Clear cache
        clear_res = self.thumbnail_service.clear_all_cache(db)
        self.assertEqual(clear_res["status"], "success")
        self.assertEqual(clear_res["cleared_count"], 1)
        self.assertEqual(self.thumbnail_service.get_cache_stats()["total_cached_thumbnails"], 0)

        db.close()

    def test_thumbnail_and_cache_api_endpoints(self):
        db = self.TestSession()
        asset_repo = AssetRepository(db)

        asset = Asset(
            name="sample.jpg",
            original_name="sample.jpg",
            mime_type="image/jpeg",
            size_bytes=os.path.getsize(self.img_path),
            storage_path=self.img_path
        )
        saved = asset_repo.save(asset)
        asset_id = saved.id
        db.close()

        # 1. Test thumbnail endpoint
        res = self.client.get(f"/api/assets/{asset_id}/thumbnail?width=150&height=150")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "image/webp")

        # 2. Test cache stats endpoint
        stats_res = self.client.get("/api/cache/stats")
        self.assertEqual(stats_res.status_code, 200)
        self.assertGreaterEqual(stats_res.json()["total_cached_thumbnails"], 1)

        # 3. Test cache clear endpoint
        clear_res = self.client.post("/api/cache/clear")
        self.assertEqual(clear_res.status_code, 200)
        self.assertEqual(clear_res.json()["status"], "success")

        # 4. Test library rescan endpoint
        rescan_res = self.client.post("/api/library/rescan")
        self.assertEqual(rescan_res.status_code, 200)
        self.assertEqual(rescan_res.json()["status"], "success")

    def test_heic_image_fallback_thumbnail_generation(self):
        db = self.TestSession()
        asset_repo = AssetRepository(db)

        # Create dummy HEIC file
        heic_path = os.path.join(self.temp_dir, "vacation.heic")
        with open(heic_path, "wb") as f:
            f.write(b"\x00\x00\x00\x1cftypheic\x00\x00\x00\x00mif1heic")

        asset = Asset(
            name="vacation.heic",
            original_name="vacation.heic",
            mime_type="image/heic",
            size_bytes=os.path.getsize(heic_path),
            storage_path=heic_path,
            category="image"
        )
        saved = asset_repo.save(asset)

        # Generate thumbnail for HEIC - should cleanly generate fallback badge if no system codec is present
        thumb_path = self.thumbnail_service.get_or_generate_thumbnail(
            db=db,
            asset_id=saved.id,
            width=200,
            height=200
        )

        self.assertIsNotNone(thumb_path)
        self.assertTrue(os.path.exists(thumb_path))
        self.assertTrue(thumb_path.endswith(".webp"))

        with Image.open(thumb_path) as thumb_img:
            self.assertEqual(thumb_img.format, "WEBP")
        db.close()

if __name__ == "__main__":
    unittest.main()
