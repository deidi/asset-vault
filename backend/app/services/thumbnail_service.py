import os
import sys
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageOps, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.repositories.asset_repository import AssetRepository
from app.services.folder_service import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    DOCUMENT_EXTENSIONS
)

logger = logging.getLogger("assetvault.thumbnail")

class ThumbnailService:
    def __init__(self, cache_dir: Optional[str] = None):
        self._custom_cache_dir = cache_dir

    def get_cache_dir(self) -> str:
        """Returns the resolved thumbnail cache directory on disk, ensuring it exists."""
        if self._custom_cache_dir:
            target_dir = os.path.abspath(self._custom_cache_dir)
        else:
            if getattr(sys, "frozen", False):
                exe_dir = os.path.dirname(sys.executable)
                target_dir = os.path.abspath(os.path.join(exe_dir, ".cache", "thumbnails"))
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                target_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".cache", "thumbnails"))

        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def compute_cache_key(self, file_path: str, mtime: float, width: int = 350, height: int = 350) -> str:
        """Generates a unique SHA-256 hash based on normalized path, timestamp, dimensions, and generator version."""
        key_content = f"v2_{os.path.normpath(file_path)}_{mtime}_{width}x{height}"
        return hashlib.sha256(key_content.encode("utf-8")).hexdigest()

    def get_or_generate_thumbnail(self, db: Session, asset_id: str, width: int = 350, height: int = 350) -> Optional[str]:
        """Retrieves an existing cached thumbnail or generates a new one on-demand."""
        asset_repo = AssetRepository(db)
        asset = asset_repo.find_by_id(asset_id)
        if not asset or not asset.storage_path:
            return None

        file_path = os.path.normpath(asset.storage_path)
        if not os.path.exists(file_path):
            return None

        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            mtime = 0.0

        cache_key = self.compute_cache_key(file_path, mtime, width, height)
        cache_dir = self.get_cache_dir()
        cached_file_path = os.path.join(cache_dir, f"{cache_key}.webp")

        if os.path.exists(cached_file_path) and os.path.getsize(cached_file_path) > 0:
            return cached_file_path

        # Generate fresh thumbnail
        generated_path = self.generate_thumbnail(file_path, cached_file_path, width, height)
        if generated_path:
            asset.thumbnail_path = generated_path
            asset_repo.save(asset)
            return generated_path

        return None

    def generate_thumbnail(self, source_path: str, output_path: str, width: int = 350, height: int = 350) -> Optional[str]:
        """Renders and optimizes a thumbnail into WebP format."""
        norm_source = os.path.normpath(source_path)
        _, ext = os.path.splitext(norm_source)
        clean_ext = ext.lower()

        try:
            # 1. Image Formats
            if clean_ext in IMAGE_EXTENSIONS:
                return self._render_image_thumbnail(norm_source, output_path, width, height)

            # 2. PDF Documents
            elif clean_ext in DOCUMENT_EXTENSIONS:
                return self._render_pdf_thumbnail(norm_source, output_path, width, height)

            # 3. Video Formats
            elif clean_ext in VIDEO_EXTENSIONS:
                return self._render_video_thumbnail(norm_source, output_path, width, height)

            # 4. Audio Formats
            elif clean_ext in AUDIO_EXTENSIONS:
                return self._render_audio_thumbnail(norm_source, output_path, width, height)

            # 5. Default Fallback Badge
            else:
                return self._render_generic_badge(norm_source, output_path, width, height, label="FILE")

        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {source_path}: {e}")
            return None

    def _render_image_thumbnail(self, source_path: str, output_path: str, width: int, height: int) -> Optional[str]:
        with Image.open(source_path) as img:
            # Auto-rotate based on EXIF tag if present
            img = ImageOps.exif_transpose(img)
            
            # Convert palette/transparency to RGBA or RGB
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            img.save(output_path, "WEBP", quality=82, method=6)
            return output_path

    def _render_pdf_thumbnail(self, source_path: str, output_path: str, width: int, height: int) -> Optional[str]:
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(source_path)
            if len(pdf) > 0:
                page = pdf[0]
                pil_image = page.render(scale=2.0).to_pil_image()
                pil_image = pil_image.convert("RGB")
                pil_image.thumbnail((width, height), Image.Resampling.LANCZOS)
                pil_image.save(output_path, "WEBP", quality=82)
                return output_path
        except Exception as e:
            logger.warning(f"pypdfium2 failed for {source_path}: {e}, falling back to badge.")
        
        return self._render_generic_badge(source_path, output_path, width, height, label="PDF", bg_color=(220, 53, 69))

    def _extract_windows_shell_thumbnail(self, source_path: str, max_dimension: int = 350) -> Optional[Image.Image]:
        """Extracts native Windows Shell video frame thumbnail via IThumbnailProvider."""
        try:
            import ctypes
            from ctypes import wintypes, POINTER, c_void_p, c_int, c_ulong, Structure, byref, c_wchar_p

            class GUID(Structure):
                _fields_ = [('Data1', c_ulong), ('Data2', wintypes.WORD), ('Data3', wintypes.WORD), ('Data4', wintypes.BYTE * 8)]

            IID_IShellItem = GUID(0x43826d1e, 0xe718, 0x42ee, (wintypes.BYTE * 8)(0xbc, 0x55, 0xa1, 0xe2, 0x61, 0xc3, 0x7b, 0xfe))
            BHID_ThumbnailHandler = GUID(0x7b2e650a, 0x8e20, 0x4f4a, (wintypes.BYTE * 8)(0xb0, 0x9e, 0x65, 0x97, 0xaf, 0xc7, 0x2f, 0xb0))
            IID_IThumbnailProvider = GUID(0xe357fccd, 0xa995, 0x4576, (wintypes.BYTE * 8)(0xb0, 0x1f, 0x23, 0x46, 0x30, 0x15, 0x4e, 0x96))

            class IShellItem(Structure):
                pass

            class IShellItemVtbl(Structure):
                _fields_ = [
                    ('QueryInterface', ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, POINTER(GUID), POINTER(c_void_p))),
                    ('AddRef', c_void_p),
                    ('Release', c_void_p),
                    ('BindToHandler', ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, c_void_p, POINTER(GUID), POINTER(GUID), POINTER(c_void_p)))
                ]

            IShellItem._fields_ = [('lpVtbl', POINTER(IShellItemVtbl))]

            class IThumbnailProvider(Structure):
                pass

            class IThumbnailProviderVtbl(Structure):
                _fields_ = [
                    ('QueryInterface', ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, POINTER(GUID), POINTER(c_void_p))),
                    ('AddRef', c_void_p),
                    ('Release', ctypes.WINFUNCTYPE(c_ulong, c_void_p)),
                    ('GetThumbnail', ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, wintypes.UINT, POINTER(wintypes.HBITMAP), POINTER(c_int)))
                ]

            IThumbnailProvider._fields_ = [('lpVtbl', POINTER(IThumbnailProviderVtbl))]

            shell32 = ctypes.windll.shell32
            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            ole32 = ctypes.windll.ole32

            # COINIT_APARTMENTTHREADED = 0x2, COINIT_MULTITHREADED = 0x0
            hr_init = ole32.CoInitializeEx(None, 0x2)
            needs_uninit = (hr_init == 0 or hr_init == 1)

            p_item = POINTER(IShellItem)()
            p_thumb = c_void_p()
            hbitmap = wintypes.HBITMAP()

            try:
                hr = shell32.SHCreateItemFromParsingName(
                    c_wchar_p(os.path.abspath(source_path)),
                    None,
                    byref(IID_IShellItem),
                    byref(p_item)
                )
                if hr != 0 or not p_item:
                    return None

                hr_bth = p_item.contents.lpVtbl.contents.BindToHandler(
                    p_item,
                    None,
                    byref(BHID_ThumbnailHandler),
                    byref(IID_IThumbnailProvider),
                    byref(p_thumb)
                )
                if hr_bth != 0 or not p_thumb.value:
                    return None

                thumb_provider = ctypes.cast(p_thumb, POINTER(IThumbnailProvider))
                alpha_type = c_int()
                hr_gt = thumb_provider.contents.lpVtbl.contents.GetThumbnail(thumb_provider, max_dimension, byref(hbitmap), byref(alpha_type))
                if hr_gt != 0 or not hbitmap.value:
                    return None

                class BITMAP(Structure):
                    _fields_ = [
                        ('bmType', wintypes.LONG),
                        ('bmWidth', wintypes.LONG),
                        ('bmHeight', wintypes.LONG),
                        ('bmWidthBytes', wintypes.LONG),
                        ('bmPlanes', wintypes.WORD),
                        ('bmBitsPixel', wintypes.WORD),
                        ('bmBits', wintypes.LPVOID)
                    ]
                bmp = BITMAP()
                gdi32.GetObjectW(hbitmap, ctypes.sizeof(BITMAP), byref(bmp))

                class BITMAPINFOHEADER(Structure):
                    _fields_ = [
                        ('biSize', wintypes.DWORD),
                        ('biWidth', wintypes.LONG),
                        ('biHeight', wintypes.LONG),
                        ('biPlanes', wintypes.WORD),
                        ('biBitCount', wintypes.WORD),
                        ('biCompression', wintypes.DWORD),
                        ('biSizeImage', wintypes.DWORD),
                        ('biXPelsPerMeter', wintypes.LONG),
                        ('biYPelsPerMeter', wintypes.LONG),
                        ('biClrUsed', wintypes.DWORD),
                        ('biClrImportant', wintypes.DWORD)
                    ]
                bih = BITMAPINFOHEADER()
                bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bih.biWidth = bmp.bmWidth
                bih.biHeight = -bmp.bmHeight
                bih.biPlanes = 1
                bih.biBitCount = 32
                bih.biCompression = 0

                buf_size = bmp.bmWidth * bmp.bmHeight * 4
                buf = (ctypes.c_char * buf_size)()

                hdc = user32.GetDC(None)
                gdi32.GetDIBits(hdc, hbitmap, 0, bmp.bmHeight, buf, byref(bih), 0)
                user32.ReleaseDC(None, hdc)
                gdi32.DeleteObject(hbitmap)
                hbitmap.value = None

                img = Image.frombuffer('RGBA', (bmp.bmWidth, bmp.bmHeight), buf, 'raw', 'BGRA', 0, 1)
                return img
            finally:
                if p_thumb:
                    try:
                        ctypes.cast(p_thumb, POINTER(IThumbnailProvider)).contents.lpVtbl.contents.Release(p_thumb)
                    except Exception:
                        pass
                if p_item:
                    try:
                        p_item.contents.lpVtbl.contents.Release(p_item)
                    except Exception:
                        pass
                if hbitmap:
                    try:
                        gdi32.DeleteObject(hbitmap)
                    except Exception:
                        pass
                if needs_uninit:
                    try:
                        ole32.CoUninitialize()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Windows Shell thumbnail extraction failed: {e}")
            return None

    def _render_video_thumbnail(self, source_path: str, output_path: str, width: int, height: int) -> Optional[str]:
        """Renders actual extracted video frame thumbnail with play overlay badge."""
        if sys.platform == "win32":
            try:
                frame_img = self._extract_windows_shell_thumbnail(source_path, max(width, height))
                if frame_img:
                    frame_img = frame_img.convert("RGB")
                    frame_img.thumbnail((width, height), Image.Resampling.LANCZOS)

                    # Draw subtle video play indicator badge in center
                    overlay = Image.new("RGBA", frame_img.size, (0, 0, 0, 0))
                    draw = ImageDraw.Draw(overlay)
                    cx, cy = frame_img.width // 2, frame_img.height // 2
                    r = min(frame_img.width, frame_img.height) // 7
                    if r >= 12:
                        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 23, 42, 180), outline=(255, 255, 255, 220), width=2)
                        tri_r = r * 0.48
                        points = [
                            (cx - tri_r * 0.6, cy - tri_r),
                            (cx - tri_r * 0.6, cy + tri_r),
                            (cx + tri_r * 0.9, cy)
                        ]
                        draw.polygon(points, fill=(255, 255, 255, 240))

                    frame_rgba = frame_img.convert("RGBA")
                    final_img = Image.alpha_composite(frame_rgba, overlay).convert("RGB")
                    final_img.save(output_path, "WEBP", quality=85, method=6)
                    return output_path
            except Exception as e:
                logger.warning(f"Native video thumbnail extraction failed for {source_path}: {e}")

        # Fallback to styled generic video badge
        return self._render_generic_badge(source_path, output_path, width, height, label="VIDEO", bg_color=(99, 102, 241))

    def _render_audio_thumbnail(self, source_path: str, output_path: str, width: int, height: int) -> Optional[str]:
        return self._render_generic_badge(source_path, output_path, width, height, label="AUDIO", bg_color=(16, 185, 129))

    def _render_generic_badge(
        self,
        source_path: str,
        output_path: str,
        width: int,
        height: int,
        label: str,
        bg_color: Tuple[int, int, int] = (71, 85, 105)
    ) -> str:
        filename = os.path.basename(source_path)
        img = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Draw decorative inner card
        padding = 24
        draw.rectangle(
            [padding, padding, width - padding, height - padding],
            outline=(255, 255, 255, 120),
            width=2
        )

        # Draw Type Label Text
        draw.text((width // 2, height // 2 - 20), label, fill=(255, 255, 255), anchor="mm")
        
        # Draw Short Filename Text
        short_name = filename if len(filename) <= 24 else f"{filename[:20]}..."
        draw.text((width // 2, height // 2 + 25), short_name, fill=(241, 245, 249), anchor="mm")

        img.save(output_path, "WEBP", quality=80)
        return output_path

    def clear_all_cache(self, db: Session) -> Dict[str, Any]:
        """Deletes all generated WebP thumbnail files and resets DB cache paths."""
        cache_dir = self.get_cache_dir()
        cleared_count = 0
        freed_bytes = 0
        errors = []

        if os.path.exists(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.endswith(".webp"):
                    file_path = os.path.join(cache_dir, fname)
                    try:
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleared_count += 1
                        freed_bytes += size
                    except Exception as e:
                        errors.append(f"{fname}: {str(e)}")

        # Reset thumbnail_path on all assets
        try:
            asset_repo = AssetRepository(db)
            all_assets = asset_repo.find_all()
            for asset in all_assets:
                if asset.thumbnail_path:
                    asset.thumbnail_path = None
                    asset_repo.save(asset)
        except Exception as e:
            logger.error(f"Error resetting database thumbnail paths: {e}")

        return {
            "status": "success" if not errors else "partial",
            "cleared_count": cleared_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "errors": errors
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Returns statistics on the thumbnail cache on disk."""
        cache_dir = self.get_cache_dir()
        total_files = 0
        total_bytes = 0

        if os.path.exists(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.endswith(".webp"):
                    total_files += 1
                    try:
                        total_bytes += os.path.getsize(os.path.join(cache_dir, fname))
                    except Exception:
                        pass

        return {
            "total_cached_thumbnails": total_files,
            "cache_directory": cache_dir,
            "total_size_bytes": total_bytes,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2)
        }

# Global singleton thumbnail service instance
thumbnail_service = ThumbnailService()
