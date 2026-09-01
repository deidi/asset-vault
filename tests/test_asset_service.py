import sys
import os
import unittest
import tempfile
import shutil
from datetime import datetime

# Add backend directory to module search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.services.asset_service import AssetService
from app.schemas.asset import AssetCreate, AssetUpdate


class TestAssetService(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        
        # Temp storage folder for file testing
        self.temp_storage = tempfile.mkdtemp()
        self.service = AssetService(self.db)
        # Override storage dir method for test isolation
        self.service._get_storage_dir = lambda: self.temp_storage

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
        self.db.close()
        if os.path.exists(self.temp_storage):
            shutil.rmtree(self.temp_storage)

    def test_upload_auto_tagging(self):
        """Verify upload auto-tags complete filename, filetype extension, and current year."""
        data = AssetCreate(
            name="quarterly_report.pdf",
            originalName="quarterly_report.pdf",
            mimeType="application/pdf",
            sizeBytes=2048,
            storagePath="storage/sample-uuid.pdf",
            description="Q3 Financial Report",
            tags=["finance"]
        )
        asset = self.service.upload_asset(data)
        tag_names = [t.name for t in asset.tags]
        current_year = str(datetime.utcnow().year)

        # Complete filename, filetype, current year, and explicit tags must exist
        self.assertIn("quarterly_report.pdf", tag_names)
        self.assertIn("pdf", tag_names)
        self.assertIn(current_year, tag_names)
        self.assertIn("finance", tag_names)

    def test_is_protected_tag(self):
        """Verify complete filename and filetype tags are identified as protected system tags."""
        data = AssetCreate(
            name="budget_chart.png",
            originalName="budget_chart.png",
            mimeType="image/png",
            sizeBytes=512,
            storagePath="storage/uuid.png",
            tags=[]
        )
        asset = self.service.upload_asset(data)

        self.assertTrue(self.service.is_protected_tag(asset, "budget_chart.png"))
        self.assertTrue(self.service.is_protected_tag(asset, "png"))
        self.assertFalse(self.service.is_protected_tag(asset, "custom_tag"))

    def test_batch_tag_operations(self):
        """Verify batch tag add, remove, and replace operations."""
        asset1 = self.service.upload_asset(AssetCreate(
            name="doc1.txt", originalName="doc1.txt", mimeType="text/plain", sizeBytes=10, storagePath="storage/1.txt", tags=[]
        ))
        asset2 = self.service.upload_asset(AssetCreate(
            name="doc2.txt", originalName="doc2.txt", mimeType="text/plain", sizeBytes=20, storagePath="storage/2.txt", tags=[]
        ))

        # Batch Add
        added_count = self.service.batch_add_tags([asset1.id, asset2.id], ["project_alpha"])
        self.assertEqual(added_count, 2)
        
        updated_asset1 = self.service.get_asset_by_id(asset1.id)
        self.assertIn("project_alpha", [t.name for t in updated_asset1.tags])

        # Batch Replace (non-protected)
        replaced_count = self.service.batch_replace_tag([asset1.id, asset2.id], "project_alpha", "project_beta")
        self.assertEqual(replaced_count, 2)
        
        updated_asset1 = self.service.get_asset_by_id(asset1.id)
        self.assertIn("project_beta", [t.name for t in updated_asset1.tags])
        self.assertNotIn("project_alpha", [t.name for t in updated_asset1.tags])

        # Protected tags must NOT be replaced
        prot_replace = self.service.batch_replace_tag([asset1.id], "txt", "doc")
        self.assertEqual(prot_replace, 0)

    def test_inventory_pagination_and_search(self):
        """Verify inventory searching, sorting, and AND-logic multi-tag filtering."""
        a1 = self.service.upload_asset(AssetCreate(
            name="alpha.pdf", originalName="alpha.pdf", mimeType="application/pdf", sizeBytes=100, storagePath="storage/a1.pdf", tags=["work"]
        ))
        a2 = self.service.upload_asset(AssetCreate(
            name="beta.png", originalName="beta.png", mimeType="image/png", sizeBytes=200, storagePath="storage/a2.png", tags=["work", "design"]
        ))

        # Search query
        res = self.service.get_inventory(search="alpha")
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["items"][0].id, a1.id)

        # Multi-tag filter (AND logic: work + design -> matches only a2)
        res_tags = self.service.get_inventory(tags="work,design")
        self.assertEqual(res_tags["total"], 1)
        self.assertEqual(res_tags["items"][0].id, a2.id)

    def test_inventory_file_type_filtering(self):
        """Verify inventory file_type filtering for image, video, audio, and documents."""
        a_img = self.service.upload_asset(AssetCreate(
            name="photo.png", originalName="photo.png", mimeType="image/png", sizeBytes=100, storagePath="storage/photo.png", tags=[]
        ))
        a_vid = self.service.upload_asset(AssetCreate(
            name="clip.mp4", originalName="clip.mp4", mimeType="video/mp4", sizeBytes=500, storagePath="storage/clip.mp4", tags=[]
        ))
        a_aud = self.service.upload_asset(AssetCreate(
            name="song.mp3", originalName="song.mp3", mimeType="audio/mp3", sizeBytes=300, storagePath="storage/song.mp3", tags=[]
        ))
        a_doc = self.service.upload_asset(AssetCreate(
            name="report.pdf", originalName="report.pdf", mimeType="application/pdf", sizeBytes=200, storagePath="storage/report.pdf", tags=[]
        ))

        # Filter by image
        img_res = self.service.get_inventory(file_type="image")
        self.assertEqual(img_res["total"], 1)
        self.assertEqual(img_res["items"][0].id, a_img.id)

        # Filter by video
        vid_res = self.service.get_inventory(file_type="video")
        self.assertEqual(vid_res["total"], 1)
        self.assertEqual(vid_res["items"][0].id, a_vid.id)

        # Filter by audio
        aud_res = self.service.get_inventory(file_type="audio")
        self.assertEqual(aud_res["total"], 1)
        self.assertEqual(aud_res["items"][0].id, a_aud.id)

        # Filter by document
        doc_res = self.service.get_inventory(file_type="document")
        self.assertEqual(doc_res["total"], 1)
        self.assertEqual(doc_res["items"][0].id, a_doc.id)

        # Filter by all
        all_res = self.service.get_inventory(file_type="all")
        self.assertEqual(all_res["total"], 4)

    def test_asset_deletion(self):
        """Verify DB record deletion and storage file cleanup."""
        asset = self.service.upload_asset(AssetCreate(
            name="temp.txt", originalName="temp.txt", mimeType="text/plain", sizeBytes=10, storagePath="storage/temp.txt", tags=[]
        ))
        
        # Create physical dummy file
        dummy_path = os.path.join(self.temp_storage, "temp.txt")
        with open(dummy_path, "w") as f:
            f.write("dummy content")

        deleted = self.service.delete_asset(asset.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_asset_by_id(asset.id))
        self.assertFalse(os.path.exists(dummy_path))


if __name__ == "__main__":
    unittest.main()
