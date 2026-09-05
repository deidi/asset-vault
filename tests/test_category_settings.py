import sys
import os
import unittest
import tempfile
import shutil
import json
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models.asset import Asset
from app.models.library_folder import LibraryFolder
from app.services.category_service import CategoryService, DEFAULT_CATEGORY_EXTENSIONS
from app.services.folder_service import categorize_file

class TestCategorySettings(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

        self.temp_dir = tempfile.mkdtemp()
        self.test_settings_path = os.path.join(self.temp_dir, "settings.json")
        self._orig_get_settings_path = CategoryService.get_settings_path
        CategoryService.get_settings_path = lambda: self.test_settings_path

        # Create a test library folder
        folder = LibraryFolder(
            id="test-folder-cat",
            path=self.temp_dir,
            name="Test Folder",
            is_recursive=True,
            is_active=True
        )
        self.db.add(folder)
        self.db.commit()

        # Reset to defaults
        CategoryService.reset_to_defaults(recategorize_existing=False)

    def tearDown(self):
        CategoryService.get_settings_path = self._orig_get_settings_path
        CategoryService.reset_to_defaults(recategorize_existing=False)
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_extensions_retrieval(self):
        defaults = CategoryService.get_default_extensions_map()
        self.assertIn("image", defaults)
        self.assertIn("video", defaults)
        self.assertIn("audio", defaults)
        self.assertIn("document", defaults)
        self.assertIn(".png", defaults["image"])
        self.assertIn(".mp4", defaults["video"])
        self.assertIn(".mp3", defaults["audio"])
        self.assertIn(".pdf", defaults["document"])

    def test_dynamic_categorization_with_custom_extension(self):
        # By default, .heic is not in image extensions
        self.assertEqual(categorize_file("photo.heic"), "other")

        # Add .heic to image extensions
        curr = CategoryService.get_extensions_map()
        curr["image"].append("heic")  # without dot
        CategoryService.save_extensions(curr, recategorize_existing=False)

        # Now .heic should be recognized as an image
        self.assertEqual(categorize_file("photo.heic"), "image")

        # Verify leading dot was normalized
        active_map = CategoryService.get_extensions_map()
        self.assertIn(".heic", active_map["image"])

    def test_recategorize_existing_database_assets(self):
        # Create an asset with .heic having category="other"
        asset = Asset(
            id="asset-heic-1",
            folder_id="test-folder-cat",
            name="vacation.heic",
            original_name="vacation.heic",
            storage_path=os.path.join(self.temp_dir, "vacation.heic"),
            category="other",
            size_bytes=1024,
            mime_type="application/octet-stream",
            created_at=datetime.utcnow()
        )
        self.db.add(asset)
        self.db.commit()

        # Verify initial category is other
        db_asset = self.db.query(Asset).filter_by(id="asset-heic-1").first()
        self.assertEqual(db_asset.category, "other")

        # Update settings to map .heic to images and recategorize
        curr = CategoryService.get_extensions_map()
        curr["image"].append(".heic")
        updated_map, recat_count = CategoryService.save_extensions(
            curr, recategorize_existing=True, db=self.db
        )

        self.assertEqual(recat_count, 1)
        self.db.refresh(db_asset)
        self.assertEqual(db_asset.category, "image")

    def test_persistence_in_settings_file(self):
        curr = CategoryService.get_extensions_map()
        curr["video"].append(".m2ts")
        CategoryService.save_extensions(curr, recategorize_existing=False)

        # Ensure file was created on disk
        self.assertTrue(os.path.exists(self.test_settings_path))
        with open(self.test_settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("category_extensions", data)
        self.assertIn(".m2ts", data["category_extensions"]["video"])

    def test_reset_to_defaults(self):
        curr = CategoryService.get_extensions_map()
        curr["document"].append(".customdoc")
        CategoryService.save_extensions(curr, recategorize_existing=False)
        self.assertIn(".customdoc", CategoryService.get_extensions_map()["document"])

        CategoryService.reset_to_defaults(recategorize_existing=False)
        self.assertNotIn(".customdoc", CategoryService.get_extensions_map()["document"])

    def test_api_settings_endpoints(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # 1. GET /api/settings/file-types
        res = client.get("/api/settings/file-types")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("categories", data)
        self.assertIn("defaults", data)
        self.assertIn("counts", data)

        # 2. PUT /api/settings/file-types
        categories = data["categories"]
        categories["image"].append(".xyzraw")
        put_res = client.put(
            "/api/settings/file-types",
            json={"categories": categories, "recategorize_existing": False}
        )
        self.assertEqual(put_res.status_code, 200)
        put_data = put_res.json()
        self.assertEqual(put_data["status"], "success")
        self.assertIn(".xyzraw", put_data["categories"]["image"])

        # 3. POST /api/settings/file-types/reset
        reset_res = client.post(
            "/api/settings/file-types/reset",
            json={"recategorize_existing": False}
        )
        self.assertEqual(reset_res.status_code, 200)
        reset_data = reset_res.json()
        self.assertNotIn(".xyzraw", reset_data["categories"]["image"])

    def test_heic_strict_category_enforcement(self):
        """
        Verify that unregistered extensions (e.g. .heic) NEVER appear under 'image'
        even if mime_type is 'image/heic', and strictly appear under 'other'.
        """
        from app.services.asset_service import AssetService

        # 1. By default, .heic is not in image extensions
        self.assertEqual(categorize_file("sample.heic", "image/heic"), "other")
        self.assertEqual(categorize_file("sample.HEIC", "image/heic"), "other")

        # 2. Insert test asset with mime_type="image/heic"
        heic_asset = Asset(
            id="heic-asset-strict-1",
            folder_id="test-folder-cat",
            name="photo.heic",
            original_name="photo.heic",
            storage_path=os.path.join(self.temp_dir, "photo.heic"),
            mime_type="image/heic",
            size_bytes=2048,
            category=categorize_file("photo.heic", "image/heic"),
            created_at=datetime.utcnow()
        )
        self.db.add(heic_asset)
        self.db.commit()

        self.assertEqual(heic_asset.category, "other")

        service = AssetService(self.db)

        # 3. Query under file_type="image" -> MUST NOT contain photo.heic
        res_img = service.get_inventory(file_type="image")
        image_names = [a.name for a in res_img["items"]]
        self.assertNotIn("photo.heic", image_names)

        # 4. Query under file_type="all" -> MUST NOT contain photo.heic (as it's non-media 'other')
        res_all = service.get_inventory(file_type="all")
        all_names = [a.name for a in res_all["items"]]
        self.assertNotIn("photo.heic", all_names)

        # 5. Query under file_type="other" -> MUST contain photo.heic
        res_other = service.get_inventory(file_type="other")
        other_names = [a.name for a in res_other["items"]]
        self.assertIn("photo.heic", other_names)

        # 6. Now register .heic under 'image'
        curr = CategoryService.get_extensions_map()
        curr["image"].append(".heic")
        CategoryService.save_extensions(curr, recategorize_existing=True, db=self.db)

        # Re-fetch asset
        self.db.refresh(heic_asset)
        self.assertEqual(heic_asset.category, "image")
        self.assertEqual(categorize_file("photo.heic", "image/heic"), "image")

        # 7. Query under file_type="image" -> MUST NOW contain photo.heic
        res_img2 = service.get_inventory(file_type="image")
        image_names2 = [a.name for a in res_img2["items"]]
        self.assertIn("photo.heic", image_names2)

        # 8. Query under file_type="other" -> MUST NOT contain photo.heic
        res_other2 = service.get_inventory(file_type="other")
        other_names2 = [a.name for a in res_other2["items"]]
        self.assertNotIn("photo.heic", other_names2)

        # 9. Now remove .heic from 'image'
        curr = CategoryService.get_extensions_map()
        curr["image"] = [e for e in curr["image"] if e != ".heic"]
        CategoryService.save_extensions(curr, recategorize_existing=True, db=self.db)

        self.db.refresh(heic_asset)
        self.assertEqual(heic_asset.category, "other")
        self.assertEqual(categorize_file("photo.heic", "image/heic"), "other")

        # 10. Query under file_type="image" -> MUST NOT contain photo.heic again
        res_img3 = service.get_inventory(file_type="image")
        image_names3 = [a.name for a in res_img3["items"]]
        self.assertNotIn("photo.heic", image_names3)

if __name__ == "__main__":
    unittest.main()
