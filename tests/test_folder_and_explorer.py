import os
import sys
import unittest
import tempfile
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.session import Base
from app.services.folder_service import FolderService
from app.services.explorer_service import ExplorerService
from app.schemas.library_folder import LibraryFolderCreate, LibraryFolderUpdate
from app.repositories.asset_repository import AssetRepository

class TestFolderAndExplorerService(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Create temporary media directory
        self.temp_dir = tempfile.mkdtemp()
        self.sub_dir = os.path.join(self.temp_dir, "subfolder")
        os.makedirs(self.sub_dir, exist_ok=True)

        # Create dummy media files
        self.img1_path = os.path.join(self.temp_dir, "banner.png")
        with open(self.img1_path, "wb") as f:
            f.write(b"fake png content")

        self.vid_path = os.path.join(self.sub_dir, "clip.mp4")
        with open(self.vid_path, "wb") as f:
            f.write(b"fake mp4 content")

        self.txt_path = os.path.join(self.temp_dir, "notes.txt")
        with open(self.txt_path, "w") as f:
            f.write("text content should be ignored by media filter")

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_scan_folder(self):
        folder_service = FolderService(self.db)
        asset_repo = AssetRepository(self.db)

        # Add library folder with custom tags and auto_tag_folder enabled
        folder_res = folder_service.add_folder(LibraryFolderCreate(
            path=self.temp_dir,
            name="Test Media Library",
            is_recursive=True,
            auto_tag_folder=True,
            custom_tags=["ClientWork", "Q1"]
        ))

        self.assertIsNotNone(folder_res.id)
        self.assertEqual(folder_res.name, "Test Media Library")

        # Scan folder
        scan_res = folder_service.scan_folder(folder_res.id)
        self.assertEqual(scan_res.total_scanned, 2)  # banner.png and clip.mp4 (notes.txt ignored)
        self.assertEqual(scan_res.newly_indexed, 2)
        self.assertEqual(scan_res.already_indexed, 0)

        # Verify indexed assets
        assets = asset_repo.find_all()
        self.assertEqual(len(assets), 2)

        banner_asset = next(a for a in assets if a.name == "banner.png")
        tag_names = {t.name for t in banner_asset.tags}

        # Verify auto-tags: #png, #banner.png, #<year>, #ClientWork, #Q1
        self.assertIn("#png", tag_names)
        self.assertIn("#banner.png", tag_names)
        self.assertIn("#ClientWork", tag_names)
        self.assertIn("#Q1", tag_names)

        # Second scan should not duplicate
        scan_res_2 = folder_service.scan_folder(folder_res.id)
        self.assertEqual(scan_res_2.already_indexed, 2)
        self.assertEqual(scan_res_2.newly_indexed, 0)

    def test_in_place_rename_on_disk(self):
        folder_service = FolderService(self.db)
        explorer_service = ExplorerService(self.db)
        asset_repo = AssetRepository(self.db)

        folder_res = folder_service.add_folder(LibraryFolderCreate(
            path=self.temp_dir,
            name="Test",
            is_recursive=False
        ))
        folder_service.scan_folder(folder_res.id)

        asset = asset_repo.find_by_storage_path(self.img1_path)
        self.assertIsNotNone(asset)

        # Rename asset to hero_banner.png
        updated = explorer_service.rename_on_disk(asset.id, "hero_banner.png")
        self.assertEqual(updated.name, "hero_banner.png")
        self.assertTrue(os.path.exists(updated.storage_path))
        self.assertFalse(os.path.exists(self.img1_path))

        # Check that filename tag was updated
        tag_names = {t.name for t in updated.tags}
        self.assertIn("#hero_banner.png", tag_names)
        self.assertNotIn("#banner.png", tag_names)

    def test_trash_to_recycle_bin(self):
        folder_service = FolderService(self.db)
        explorer_service = ExplorerService(self.db)
        asset_repo = AssetRepository(self.db)

        folder_res = folder_service.add_folder(LibraryFolderCreate(
            path=self.temp_dir,
            name="Test",
            is_recursive=False
        ))
        folder_service.scan_folder(folder_res.id)

        asset = asset_repo.find_by_storage_path(self.img1_path)
        self.assertIsNotNone(asset)
        asset_id = asset.id

        # Trash file
        result = explorer_service.trash_to_recycle_bin(asset_id)
        self.assertEqual(result["status"], "success")

        # Verify asset is removed from DB
        self.assertIsNone(asset_repo.find_by_id(asset_id))
        self.assertFalse(os.path.exists(self.img1_path))

if __name__ == "__main__":
    unittest.main()
