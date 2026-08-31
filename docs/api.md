# AssetVault - API Documentation

The AssetVault API conforms to REST style conventions, returning and accepting JSON payloads (except binary file downloads and media thumbnails).

---

## 🏷️ Complete Endpoints Reference

### 1. Library Folders & In-Place Scanning
- **Create Library Folder**: `POST /api/folders`
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
- **Scan Single Folder**: `POST /api/folders/{id}/scan`
  - Response:
    ```json
    {
      "folder_id": "uuid-string",
      "folder_path": "D:\\Media\\Photos",
      "total_scanned": 150,
      "newly_indexed": 12,
      "already_indexed": 138,
      "errors": []
    }
    ```
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
  - Payload: `{ "asset_ids": ["uuid-1", "uuid-2"], "destination_folder": "D:\\Archive" }`

---

### 3. Inventory, Search & Pagination
- **URL**: `/api/assets`
- **Method**: `GET`
- **Query Parameters**:
  - `page`: `int` (default: `1`, minimum: `1`)
  - `pageSize`: `int` (default: `20`, range: `1` to `10000`)
  - `sortBy`: `str` (default: `"created_at"`, options: `"created_at"`, `"name"`, `"size"`)
  - `sortDir`: `str` (default: `"desc"`, options: `"asc"`, `"desc"`)
  - `search`: `str` (default: `""`)
  - `tags`: `str` (comma-separated list of tags for AND-logic filtering)
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
      "description": "Asset description",
      "folder_id": "folder-uuid",
      "file_modified_at": "2026-08-31T11:00:00.000Z",
      "thumbnail_path": null,
      "created_at": "2026-08-31T11:00:00.000Z",
      "absolute_path": "D:\\Media\\Photos\\sample.jpg",
      "tags": [
        { "id": "tag-1", "name": "jpg" },
        { "id": "tag-2", "name": "sample.jpg" },
        { "id": "tag-3", "name": "Photos" },
        { "id": "tag-4", "name": "2026" }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20,
  "totalPages": 1
}
```

---

### 4. File Upload (Internal Vault Mode)
- **URL**: `/api/upload`
- **Method**: `POST`
- **Content-Types**:
  - `multipart/form-data`: `file` (file payload), `description` (optional text), `tags` (optional comma-separated string). Automatically tags complete filename, filetype extension, and current year.
  - `application/json`: `AssetCreate` schema payload.
- **Response**: `201 Created` (returns created `AssetResponse`).

---

### 5. Single Asset Operations
- **Get Asset Details**: `GET /api/asset/{id}`
- **Update Asset**: `PUT /api/asset/{id}`
  - Payload: `{ "name": "new_name", "description": "new desc", "tags": ["tag1", "tag2"] }`
- **Delete Asset**: `DELETE /api/asset/{id}` (or `DELETE /api/file` with `{ "id": "uuid" }`)
- **Download Asset File**: `GET /api/asset/{id}/download` (returns raw file stream)

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

### 7. Multi-Asset ZIP Download
- **URL**: `/api/assets/download-zip?ids=id1,id2,id3`
- **Method**: `GET`
- **Response**: Binary `.zip` file stream containing all requested files.

---

### 8. Backup, Restore & Verification
- **Download Complete Backup Archive**: `GET /api/assets/backup`
- **Download CSV Database Export**: `GET /api/assets/backup/csv`
- **Restore Database from CSV**: `POST /api/assets/restore/csv` (multipart file upload)
- **Restore System from ZIP Archive**: `POST /api/assets/restore/zip` (multipart file upload)
- **Generate Integrity Verification Log**: `GET /api/assets/verify`

---

### 9. Settings & Storage Path Management
- **Get Storage Path**: `GET /api/settings/storage`
- **Update Storage Directory**: `POST /api/settings/storage`
  - Payload: `{ "storage_dir": "D:\\NewStorage", "password": "SYSTEM_PASSWORD" }`
- **Browse Storage Directories**: `GET /api/settings/storage/browse?path=D:\\`
- **Purge All Assets**: `POST /api/assets/purge`
  - Payload: `{ "password": "SYSTEM_PASSWORD" }`
