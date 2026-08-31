import sys
import os
import unittest
import tempfile
import shutil

# Add backend directory to module search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base, get_db
from app.main import app
from app.services.asset_service import AssetService


class TestAPIRoutes(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for API testing
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        
        self.temp_storage = tempfile.mkdtemp()

        # Override dependency get_db
        def _get_test_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = _get_test_db
        
        # Ensure a test library folder exists
        from app.models.library_folder import LibraryFolder
        test_folder = LibraryFolder(
            id="test-library-folder-id",
            path=self.temp_storage,
            name="Test Library",
            is_recursive=True,
            is_active=True
        )
        self.db.add(test_folder)
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        if os.path.exists(self.temp_storage):
            shutil.rmtree(self.temp_storage)

    def test_json_upload_and_inventory(self):
        """Test uploading asset via JSON payload and retrieving through paginated inventory."""
        asset_service = AssetService(self.db)
        asset = asset_service.upload_asset(
            AssetCreate_Mock(
                name="api_test_doc.pdf",
                originalName="api_test_doc.pdf",
                mimeType="application/pdf",
                sizeBytes=1024,
                storagePath="storage/api_test_doc.pdf",
                description="API integration test document",
                tags=["api", "test"]
            )
        )
        self.assertIsNotNone(asset.id)
        
        # Query inventory
        inv = asset_service.get_inventory(page=1, page_size=10, search="api_test_doc")
        self.assertEqual(inv["total"], 1)
        item = inv["items"][0]
        self.assertEqual(item.name, "api_test_doc.pdf")
        
        # Verify auto-tagging complete filename and filetype extension
        item_tags = [t.name for t in item.tags]
        self.assertIn("api_test_doc.pdf", item_tags)
        self.assertIn("pdf", item_tags)

    def test_verify_integrity_report(self):
        """Test generating integrity verification report."""
        asset_service = AssetService(self.db)
        asset_service.upload_asset(
            AssetCreate_Mock(
                name="integrity.txt",
                originalName="integrity.txt",
                mimeType="text/plain",
                sizeBytes=5,
                storagePath="storage/integrity.txt",
                description="Integrity check",
                tags=[]
            )
        )
        report = asset_service.verify_assets_integrity()
        self.assertIn("ASSETVAULT INTEGRITY REPORT", report)
        self.assertIn("Total Assets Registered: 1", report)


class AssetCreate_Mock:
    def __init__(self, name, originalName, mimeType, sizeBytes, storagePath, description, tags):
        self.name = name
        self.originalName = originalName
        self.mimeType = mimeType
        self.sizeBytes = sizeBytes
        self.storagePath = storagePath
        self.description = description
        self.tags = tags


if __name__ == "__main__":
    unittest.main()
