import os
import sys
import json
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger("assetvault.category_service")

# Canonical default extensions per category
DEFAULT_CATEGORY_EXTENSIONS: Dict[str, List[str]] = {
    "image": [
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".ico", ".jfif"
    ],
    "video": [
        ".mp4", ".webm", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".m4v"
    ],
    "audio": [
        ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"
    ],
    "document": [
        ".pdf", ".txt", ".doc", ".docx", ".rtf", ".md", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"
    ]
}

VALID_CATEGORIES = ("image", "video", "audio", "document")

class CategoryService:
    _active_extensions: Dict[str, Set[str]] = {
        cat: set(exts) for cat, exts in DEFAULT_CATEGORY_EXTENSIONS.items()
    }
    _initialized: bool = False

    @classmethod
    def get_settings_path(cls) -> str:
        """Resolves the persistent settings.json file path across development and frozen standalone modes."""
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            return os.path.abspath(os.path.join(exe_dir, "db", "settings.json"))
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.abspath(os.path.join(current_dir, "..", "..", "db", "settings.json"))

    @classmethod
    def initialize(cls) -> None:
        """Loads customized category extension sets from settings.json if present."""
        cls._initialized = True
        cls.load_extensions()

    @classmethod
    def get_active_extensions(cls) -> Dict[str, Set[str]]:
        """Returns the in-memory active extension sets."""
        if not cls._initialized:
            cls.initialize()
        return cls._active_extensions

    @classmethod
    def get_extensions_map(cls) -> Dict[str, List[str]]:
        """Returns the active extensions formatted as sorted lists."""
        if not cls._initialized:
            cls.initialize()
        return {
            cat: sorted(list(cls._active_extensions.get(cat, set())))
            for cat in VALID_CATEGORIES
        }

    @classmethod
    def get_default_extensions_map(cls) -> Dict[str, List[str]]:
        """Returns the canonical factory default extension mapping."""
        return {
            cat: sorted(list(DEFAULT_CATEGORY_EXTENSIONS[cat]))
            for cat in VALID_CATEGORIES
        }

    @classmethod
    def load_extensions(cls) -> Dict[str, List[str]]:
        """Reads settings.json and populates _active_extensions in memory."""
        settings_path = cls.get_settings_path()
        new_active: Dict[str, Set[str]] = {
            cat: set(exts) for cat, exts in DEFAULT_CATEGORY_EXTENSIONS.items()
        }

        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    custom_map = data.get("category_extensions")
                    if isinstance(custom_map, dict):
                        for cat in VALID_CATEGORIES:
                            if cat in custom_map and isinstance(custom_map[cat], list):
                                cleaned_set = set()
                                for ext in custom_map[cat]:
                                    if isinstance(ext, str):
                                        clean = ext.strip().lower()
                                        if clean:
                                            if not clean.startswith("."):
                                                clean = f".{clean}"
                                            cleaned_set.add(clean)
                                new_active[cat] = cleaned_set
            except Exception as e:
                logger.warning(f"Failed to load category_extensions from {settings_path}: {e}")

        cls._active_extensions = new_active
        cls._sync_with_folder_service()
        return cls.get_extensions_map()

    @classmethod
    def save_extensions(
        cls,
        categories: Dict[str, List[str]],
        recategorize_existing: bool = True,
        db: Optional[Session] = None
    ) -> Tuple[Dict[str, List[str]], int]:
        """
        Validates, normalizes, and saves category extensions to settings.json.
        Optionally re-evaluates all existing assets in the database.
        """
        cleaned_map: Dict[str, Set[str]] = {}
        assigned_extensions: Dict[str, str] = {}  # ext -> category (collision detection)

        for cat in VALID_CATEGORIES:
            ext_list = categories.get(cat, [])
            clean_set: Set[str] = set()
            for raw in ext_list:
                if isinstance(raw, str):
                    clean = raw.strip().lower()
                    if clean:
                        if not clean.startswith("."):
                            clean = f".{clean}"
                        clean_set.add(clean)
                        assigned_extensions[clean] = cat
            cleaned_map[cat] = clean_set

        cls._active_extensions = cleaned_map
        cls._sync_with_folder_service()

        # Persist to settings.json
        settings_path = cls.get_settings_path()
        settings_dir = os.path.dirname(settings_path)
        if settings_dir:
            os.makedirs(settings_dir, exist_ok=True)

        existing_data: Dict[str, Any] = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        existing_data["category_extensions"] = {
            cat: sorted(list(cleaned_map[cat])) for cat in VALID_CATEGORIES
        }

        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)

        recategorized_count = 0
        if recategorize_existing and db is not None:
            recategorized_count = cls.recategorize_assets(db)

        return cls.get_extensions_map(), recategorized_count

    @classmethod
    def reset_to_defaults(
        cls,
        recategorize_existing: bool = True,
        db: Optional[Session] = None
    ) -> Tuple[Dict[str, List[str]], int]:
        """Resets configured extensions to defaults."""
        defaults = {cat: list(exts) for cat, exts in DEFAULT_CATEGORY_EXTENSIONS.items()}
        return cls.save_extensions(defaults, recategorize_existing=recategorize_existing, db=db)

    @classmethod
    def recategorize_assets(cls, db: Session) -> int:
        """
        Re-evaluates asset.category for all stored assets based on current active extensions.
        Updates changed records in batches.
        """
        from app.models.asset import Asset
        from app.services.folder_service import categorize_file

        recategorized_count = 0
        batch_size = 500
        uncommitted = 0

        # Query all assets
        assets = db.query(Asset).all()
        for asset in assets:
            path_or_name = asset.storage_path or asset.name
            new_cat = categorize_file(path_or_name, asset.mime_type)
            if asset.category != new_cat:
                asset.category = new_cat
                recategorized_count += 1
                uncommitted += 1

                if uncommitted >= batch_size:
                    db.commit()
                    uncommitted = 0

        if uncommitted > 0:
            db.commit()

        logger.info(f"Recategorization complete. Updated {recategorized_count} assets.")
        return recategorized_count

    @classmethod
    def _sync_with_folder_service(cls) -> None:
        """Keeps folder_service global extension sets synchronized with active category extensions."""
        try:
            import app.services.folder_service as fs
            active = cls._active_extensions
            fs.IMAGE_EXTENSIONS = set(active.get("image", set()))
            fs.VIDEO_EXTENSIONS = set(active.get("video", set()))
            fs.AUDIO_EXTENSIONS = set(active.get("audio", set()))
            fs.DOCUMENT_EXTENSIONS = set(active.get("document", set()))
            fs.MEDIA_EXTENSIONS = (
                fs.IMAGE_EXTENSIONS
                | fs.VIDEO_EXTENSIONS
                | fs.AUDIO_EXTENSIONS
                | fs.DOCUMENT_EXTENSIONS
            )
            fs.SUPPORTED_EXTENSIONS = fs.MEDIA_EXTENSIONS
        except Exception as e:
            logger.debug(f"Sync with folder_service skipped or deferred: {e}")
