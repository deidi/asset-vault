import os
import sys
import unittest
import tempfile
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from watchdog.events import FileCreatedEvent, FileMovedEvent, FileDeletedEvent

# Ensure backend directory is in python module search path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import app.models
from app.db.session import Base, init_db, engine
from app.models.library_folder import LibraryFolder
from app.repositories.library_folder_repository import LibraryFolderRepository
from app.repositories.asset_repository import AssetRepository
from app.services.watcher_service import WatcherService, LibraryEventHandler

class TestWatcherService(unittest.TestCase):
    def setUp(self):
        init_db(engine)
        self.temp_dir = tempfile.mkdtemp()
        self.watcher = WatcherService()

    def tearDown(self):
        self.watcher.stop_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_watcher_lifecycle(self):
        from unittest.mock import MagicMock
        mock_observer = MagicMock()
        mock_observer.is_alive.return_value = True
        mock_observer.schedule.return_value = "mock-watch-object"
        self.watcher._observer = mock_observer

        folder = LibraryFolder(
            id="test-folder-lifecycle-id",
            path=self.temp_dir,
            name="Lifecycle Test",
            is_recursive=True,
            auto_tag_folder=True,
            custom_tags="LiveTest",
            is_active=True
        )

        # Start watcher for folder
        self.watcher.watch_folder(folder)
        self.assertIn("test-folder-lifecycle-id", self.watcher._watches)
        mock_observer.schedule.assert_called_once()

        # Unwatch folder
        self.watcher.unwatch_folder("test-folder-lifecycle-id")
        self.assertNotIn("test-folder-lifecycle-id", self.watcher._watches)
        mock_observer.unschedule.assert_called_once_with("mock-watch-object")

        # Stop all
        self.watcher.stop_all()
        mock_observer.stop.assert_called_once()
        self.assertIsNone(self.watcher._observer)

    def test_handler_events_simulation(self):
        from app.db.session import SessionLocal
        db = SessionLocal()
        folder_repo = LibraryFolderRepository(db)
        asset_repo = AssetRepository(db)

        # Clean existing test folder if present
        existing = folder_repo.find_by_path(self.temp_dir)
        if existing:
            folder_repo.delete(existing.id)

        folder = LibraryFolder(
            path=self.temp_dir,
            name="Handler Test Dir",
            is_recursive=True,
            auto_tag_folder=True,
            custom_tags="HandlerLive",
            is_active=True
        )
        saved_folder = folder_repo.create(folder)
        handler = LibraryEventHandler(folder_id=saved_folder.id)

        try:
            # 1. Create file on disk and simulate on_created event
            file_path = os.path.join(self.temp_dir, "handler_img.png")
            with open(file_path, "wb") as f:
                f.write(b"PNG test bytes")

            handler.on_created(FileCreatedEvent(file_path))

            # Verify asset was indexed
            asset = asset_repo.find_by_storage_path(file_path)
            self.assertIsNotNone(asset)
            self.assertEqual(asset.name, "handler_img.png")
            tag_names = {t.name for t in asset.tags}
            self.assertIn("png", tag_names)
            self.assertIn("handler_img.png", tag_names)
            self.assertIn("HandlerLive", tag_names)

            # 2. Simulate rename (on_moved)
            renamed_path = os.path.join(self.temp_dir, "handler_renamed.png")
            os.replace(file_path, renamed_path)

            handler.on_moved(FileMovedEvent(file_path, renamed_path))

            # Verify rename in DB (expire cache to get fresh DB state)
            db.expire_all()
            renamed_asset = asset_repo.find_by_storage_path(renamed_path)
            self.assertIsNotNone(renamed_asset)
            self.assertEqual(renamed_asset.name, "handler_renamed.png")
            updated_tags = {t.name for t in renamed_asset.tags}
            self.assertIn("handler_renamed.png", updated_tags)
            self.assertNotIn("handler_img.png", updated_tags)

            # 3. Simulate deletion (on_deleted)
            os.remove(renamed_path)
            handler.on_deleted(FileDeletedEvent(renamed_path))

            # Verify removal from DB
            db.expire_all()
            deleted_check = asset_repo.find_by_storage_path(renamed_path)
            self.assertIsNone(deleted_check)

        finally:
            folder_repo.delete(saved_folder.id)
            db.close()

if __name__ == "__main__":
    unittest.main()
