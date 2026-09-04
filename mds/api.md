# AssetVault - API Documentation

The AssetVault API conforms to REST style conventions, returning and accepting JSON payloads (except binary file downloads and media thumbnails).

---

## 🏷️ Complete Endpoints Reference

### 1. Library Folders & In-Place Scanning
- **Create Library Folder**: `POST /api/folders`
  - Automatically scans and indexes the target folder on disk upon creation.
  - Payload:
    ```json
    {
      "path": "D:\\Media\\Photos",
      "name": "My Photos Album",
      "is_recursive": true,
      "auto_tag_folder": true,
      "custom_tags": ["Vacation", "2026"]
    }
    ```
- **List All Library Folders**: `GET /api/folders?active_only=false`
- **Get Folder Details**: `GET /api/folders/{id}`
- **Update Folder Settings**: `PATCH /api/folders/{id}`
  - Payload: `{ "name": "New Name", "is_recursive": false, "auto_tag_folder": true, "custom_tags": ["Work"] }`
- **Remove Folder from Library**: `DELETE /api/folders/{id}`
- **Get Subfolder Hierarchy Tree**: `GET /api/folders/{id}/tree`
  - Returns nested subdirectories with recursive `asset_count` badges:
    ```json
    {
      "path": "D:\\Media",
      "name": "Media",
      "asset_count": 8289,
      "children": [
        {
          "path": "D:\\Media\\2024",
          "name": "2024",
          "asset_count": 1250,
          "children": []
        }
      ]
    }
    ```
- **Scan Single Folder**: `POST /api/folders/{id}/scan`
- **Scan All Active Folders**: `POST /api/folders/scan-all`
- **Open Native Folder Picker Dialog**: `POST /api/folders/picker`

---

### 2. Windows File Explorer & In-Place Actions
- **Reveal File in Explorer**: `POST /api/explorer/reveal`
  - Payload: `{ "asset_id": "uuid-string" }` or `{ "path": "D:\\Media\\photo.jpg" }`
  - Action: Invokes `explorer.exe /select,"<path>"` to highlight the item in Windows File Explorer.
- **Rename File On Disk**: `POST /api/explorer/rename`
  - Payload: `{ "asset_id": "uuid-string", "new_name": "renamed_photo.jpg" }`
  - Action: Safely renames file on disk (`os.replace`), updates database paths, and migrates `#filename` protected system tag.
- **Trash File to Recycle Bin**: `POST /api/explorer/trash`
  - Payload: `{ "asset_id": "uuid-string" }`
  - Action: Moves the physical file into the Windows Recycle Bin (`send2trash`) and deletes the asset database record.
- **Batch Trash Files**: `POST /api/explorer/batch-trash`
  - Payload: `{ "asset_ids": ["uuid-1", "uuid-2"] }`
- **Batch Move Files**: `POST /api/explorer/batch-move`
  - Payload: `{ "asset_ids": ["uuid-1", "uuid-2"], "destination_folder": "D:\\Archive" }` (Accepts `destination_folder` or `destination_directory`, handles quoted Windows paths, and auto-resolves naming collisions).
  - Response:
    ```json
    {
      "status": "success",
      "moved_count": 2,
      "errors": []
    }
    ```

---

### 3. Inventory, Search & Pagination
- **URL**: `/api/assets`
- **Method**: `GET`
- **Query Parameters**:
  - `page`: `int` (default: `1`, minimum: `1`)
  - `pageSize` / `page_size`: `Optional[int]` (default: `50`, dynamic library sizing, or unconstrained when not set)
  - `sortBy` / `sort_by`: `str` (default: `"created_at"`, options: `"created_at"`, `"name"`, `"size"`)
  - `sortDir` / `sort_dir`: `str` (default: `"desc"`, options: `"asc"`, `"desc"`)
  - `file_type` / `fileType`: `Optional[str]` (filters strictly by media family: `"image"`, `"video"`, `"audio"`, `"document"`, `"all"`)
  - `search`: `str` (full-text search query across filenames, descriptions, and tags)
  - `folder_id`: `Optional[str]` (filters strictly to a registered parent library folder)
  - `subfolder_path`: `Optional[str]` (filters strictly to a specific subfolder path prefix)
  - `tags`: `Optional[List[str]]` (comma-separated or list of tags for AND-logic filtering, matching both `#tag` and `tag`)
- **Response**: `200 OK`
```json
{
  "items": [
    {
      "id": "uuid-string",
      "name": "sample.jpg",
      "original_name": "sample.jpg",
      "mime_type": "image/jpeg",
      "size_bytes": 204800,
      "storage_path": "D:\\Media\\Photos\\sample.jpg",
      "description": "",
      "folder_id": "folder-uuid",
      "file_modified_at": "2026-08-31T11:00:00.000Z",
      "thumbnail_path": "D:\\Projects\\asset-vault\\.cache\\thumbnails\\...webp",
      "created_at": "2026-08-31T11:00:00.000Z",
      "absolute_path": "D:\\Media\\Photos\\sample.jpg",
      "tags": [
        { "id": "tag-1", "name": "#jpg" },
        { "id": "tag-2", "name": "#sample.jpg" },
        { "id": "tag-3", "name": "#Photos" },
        { "id": "tag-4", "name": "#2026" }
      ]
    }
  ],
  "total": 8289,
  "page": 1,
  "pageSize": 50,
  "totalPages": 166
}
```

---

### 4. Media Thumbnails & Cache Management
- **Get Media Thumbnail**: `GET /api/assets/{id}/thumbnail?width=350&height=350`
  - Generates/serves high-performance WebP thumbnail with disk caching.
  - Supports Images, PDFs (`pypdfium2`), and Videos (native Windows Shell `IThumbnailProvider` frame extraction with play badge overlay).
- **Get Cache Statistics**: `GET /api/cache/stats`
  - Returns `{ "total_cached_thumbnails": 120, "total_size_bytes": 4500000, "total_size_mb": 4.29 }`.
- **Clear Thumbnail Cache**: `POST /api/cache/clear`
  - Flushes all cached `.webp` files from disk and resets database cache paths.
- **Full Library Rescan & Integrity Flush**: `POST /api/library/rescan`
  - Flushes thumbnail cache, purges missing files, and re-indexes all active library folders.

---

### 5. Single Asset Operations
- **Get Asset Details**: `GET /api/asset/{id}`
- **Update Asset**: `PUT /api/asset/{id}`
  - Payload: `{ "name": "new_name", "description": "new desc", "tags": ["tag1", "tag2"] }`
- **Delete Asset**: `DELETE /api/asset/{id}`
- **Download Asset File**: `GET /api/asset/{id}/download` (or `/content`)

---

### 6. Tag Operations & Batch Tag Management
- **List All Tags**: `GET /api/tags`
- **Create Tag**: `POST /api/tags` (`{ "name": "tag-name" }`)
- **Delete Tag**: `DELETE /api/tag/{id}`
- **Update Tag**: `PUT /api/tag/{id}`
- **Delete Unused Tags**: `DELETE /api/tags/unused`
- **Batch Add Tags**: `POST /api/assets/tags/add`
  - Payload: `{ "asset_ids": ["id1", "id2"], "tags": ["tagA", "tagB"] }`
- **Batch Remove Tags**: `POST /api/assets/tags/remove`
  - Payload: `{ "asset_ids": ["id1"], "tags": ["tagA"] }`
- **Batch Replace Tag**: `POST /api/assets/tags/replace`
  - Payload: `{ "asset_ids": ["id1"], "old_tag": "old", "new_tag": "new" }`
- **Batch Set Tags**: `POST /api/assets/tags/set`
  - Payload: `{ "asset_ids": ["id1"], "tags": ["tag1", "tag2"] }`

---

### 7. Multi-Asset ZIP Download & Backups
- **Download ZIP Selection**: `GET /api/assets/download-zip?ids=id1,id2,id3`
- **Download Complete Backup Archive**: `GET /api/assets/backup`
- **Download CSV Database Export**: `GET /api/assets/backup/csv`
- **Restore Database from CSV**: `POST /api/assets/restore/csv`
- **Generate Integrity Verification Log**: `GET /api/assets/verify`

---

### 8. Real-Time File System Events (WebSocket)
- **URL**: `ws://127.0.0.1:8000/api/ws/events`
- **Protocol**: JSON event stream broadcasted by `WatchdogHandler`:
  ```json
  {
    "event": "created",
    "asset_id": "uuid-string",
    "file_path": "D:\\Media\\new_file.jpg",
    "timestamp": "2026-08-31T12:00:00.000Z"
  }
  ```
