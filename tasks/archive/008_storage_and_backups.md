# Task 008: Storage Migration, Backups & Verification

## Goal
Implement custom storage directory migration, system backup/restore, and integrity logging.

## Requirements
- Storage path update endpoint (`POST /api/settings/storage`) with auto file migration
- Full system backup archive (`GET /api/assets/backup` and `POST /api/assets/restore/zip`)
- CSV database export & restore (`GET /api/assets/backup/csv` and `POST /api/assets/restore/csv`)
- Integrity verification endpoint (`GET /api/assets/verify`)

## Acceptance
- Users can migrate storage folders, export/import full system backups, and download integrity reports.

---

## 💎 Completion & Verification Status

### Status: COMPLETED

1. **Storage Path Migration**: Implemented `update_storage_dir` in `AssetService` migrating files and saving new directory to `backend/db/settings.json`.
2. **System Backup & Restore**: Built ZIP backup archiving database and physical files, and restoration handler.
3. **CSV Export & Restore**: Built CSV exporter and parser for spreadsheet backup.
4. **Integrity Verification**: Built `verify_assets_integrity` comparing DB records with disk files and generating log reports.

### Verification Metrics
- Storage folder updates move files cleanly without data loss.
- Backup ZIP/CSV exports and restores verify successfully.
