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

    def test_folder_tree_and_subfolder_filtering(self):
        folder_service = FolderService(self.db)
        from app.services.asset_service import AssetService
        asset_service = AssetService(self.db)

        folder_res = folder_service.add_folder(LibraryFolderCreate(
            path=self.temp_dir,
            name="TreeTest",
            is_recursive=True
        ))
        folder_service.scan_folder(folder_res.id)

        # 1. Fetch tree
        tree = folder_service.get_folder_tree(folder_res.id)
        self.assertEqual(tree.name, "TreeTest")
        self.assertEqual(tree.asset_count, 2)
        self.assertEqual(len(tree.children), 1)
        self.assertEqual(tree.children[0].name, "subfolder")
        self.assertEqual(tree.children[0].asset_count, 1)

        # 2. Query inventory with subfolder path
        subfolder_inventory = asset_service.get_inventory(
            folder_id=folder_res.id,
            subfolder_path=self.sub_dir
        )
        self.assertEqual(subfolder_inventory["total"], 1)
        self.assertEqual(subfolder_inventory["items"][0].name, "clip.mp4")

    def test_batch_move_assets(self):
        folder_service = FolderService(self.db)
        explorer_service = ExplorerService(self.db)
        asset_repo = AssetRepository(self.db)

        folder_res = folder_service.add_folder(LibraryFolderCreate(
            path=self.temp_dir,
            name="MoveSource",
            is_recursive=False
        ))
        folder_service.scan_folder(folder_res.id)

        assets = asset_repo.find_all()
        banner_asset = next(a for a in assets if a.name == "banner.png")

        # Destination newly created folder
        target_dest = os.path.join(self.temp_dir, "moved_assets_folder")

        res = explorer_service.batch_move([banner_asset.id], target_dest)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["moved_count"], 1)

        updated_asset = asset_repo.find_by_id(banner_asset.id)
        expected_new_path = os.path.normpath(os.path.join(target_dest, "banner.png"))
        self.assertEqual(os.path.normpath(updated_asset.storage_path), expected_new_path)
        self.assertTrue(os.path.exists(expected_new_path))

    def test_excluded_paths_and_app_folders(self):
        """Verify that internal app directories like .cache, db, storage, node_modules are ignored while root media files scan properly."""
        from app.services.folder_service import is_excluded_path, is_excluded_dir_name

        self.assertTrue(is_excluded_dir_name(".cache"))
        self.assertTrue(is_excluded_dir_name("cache"))
        self.assertTrue(is_excluded_dir_name("db"))
        self.assertTrue(is_excluded_dir_name("storage"))
        self.assertTrue(is_excluded_dir_name("node_modules"))
        self.assertFalse(is_excluded_dir_name("MyPhotos"))
        self.assertFalse(is_excluded_dir_name("Renders"))

        # Create dummy internal directories inside the library folder
        cache_dir = os.path.join(self.temp_dir, ".cache", "thumbnails")
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "thumb123.webp"), "wb") as f:
            f.write(b"fake thumb")

        db_dir = os.path.join(self.temp_dir, "db")
        os.makedirs(db_dir, exist_ok=True)
        with open(os.path.join(db_dir, "assetvault.sqlite"), "wb") as f:
            f.write(b"fake sqlite db")

        storage_dir = os.path.join(self.temp_dir, "storage")
        os.makedirs(storage_dir, exist_ok=True)
        with open(os.path.join(storage_dir, "internal_upload.png"), "wb") as f:
            f.write(b"fake internal upload")

        folder_service = FolderService(self.db)
        asset_repo = AssetRepository(self.db)

        folder_res = folder_service.add_folder(LibraryFolderCreate(
            path=self.temp_dir,
            name="AppRootTest",
            is_recursive=True
        ))

        scan_res = folder_service.scan_folder(folder_res.id)
        # Should only scan the 2 user files (root banner.png and subfolder/clip.mp4), ignoring .cache/, db/, and storage/
        self.assertEqual(scan_res.total_scanned, 2)
        self.assertEqual(scan_res.newly_indexed, 2)

        # Check tree does not contain .cache, db, or storage
        tree = folder_service.get_folder_tree(folder_res.id)
        child_names = [c.name for c in tree.children]
        self.assertIn("subfolder", child_names)
        self.assertNotIn(".cache", child_names)
        self.assertNotIn("db", child_names)
        self.assertNotIn("storage", child_names)

if __name__ == "__main__":
    unittest.main()

