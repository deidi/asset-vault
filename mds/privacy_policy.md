# Privacy Policy for AssetVault

**Last Updated:** September 4, 2026

**AssetVault** ("we", "our", or "the application") is committed to protecting your privacy. This Privacy Policy explains our practices regarding user data, media files, and application telemetry.

---

## 1. Summary: 100% Offline & Private by Design

AssetVault is built with a **local-first, zero-telemetry architecture**:
- **No Data Collection**: We do not collect, store, track, or share any personal information.
- **No Cloud Uploads**: Your media files, tags, thumbnails, and database records remain 100% on your local machine.
- **No Telemetry or Tracking**: The application contains zero analytical trackers, crash reporters, or advertising SDKs.
- **Zero Third-Party Sharing**: No data is ever transmitted to third parties or remote cloud servers.

---

## 2. Information We Handle Locally

All data processed by AssetVault is strictly confined to your local computer:

### A. Media Files & In-Place Library Folders
- AssetVault indexes directories that you explicitly select. Media files remain in their original disk locations.
- The application reads file metadata (e.g. filename, file size, modification timestamp, dimensions) strictly to render thumbnails and provide search capabilities.

### B. Local SQLite Database & Cache
- Application state, tag associations, and folder references are stored locally in an unencrypted SQLite database (`assetvault.sqlite`).
- Generated thumbnail previews are cached locally in your application cache directory (`.cache/thumbnails/`) for performance.
- You can clear this cache or delete the database at any time through the application settings or by deleting the files from disk.

---

## 3. Network Communications

AssetVault operates completely offline without an active internet connection. The only network operations are:
1. **Localhost Communication**: The desktop application communicates between its frontend interface and local backend server via standard local loopback (`http://127.0.0.1:8000` / `ws://127.0.0.1:8000`).
2. **Optional LAN Access**: If explicitly enabled by the user in settings, the local server can accept connections from devices on your private local area network (LAN). No connections to public external servers are established.

---

## 4. Third-Party Dependencies

AssetVault is built using reputable open-source libraries (e.g. FastAPI, SQLAlchemy, React, PyWebView, Pillow, Watchdog, pypdfium2). None of these bundled dependencies transmit personal telemetry or tracking metrics.

---

## 5. User Control & Data Deletion

You retain full ownership and control over your data:
- **Revoke Library Folders**: Removing a library folder in AssetVault unindexes the records immediately without modifying or deleting the underlying files on your disk.
- **Complete Uninstallation**: To completely remove all AssetVault data, simply delete the application folder and its local database / cache directories.

---

## 6. Open Source Transparency

AssetVault is open-source software released under the [MIT License](https://github.com/deidi/asset-vault/blob/main/LICENSE). The entire codebase is publicly auditable on [GitHub](https://github.com/deidi/asset-vault).

---

## 7. Contact & Inquiries

If you have any questions or feedback regarding this Privacy Policy, please open an issue on the official GitHub repository:
- **GitHub Issues**: [https://github.com/deidi/asset-vault/issues](https://github.com/deidi/asset-vault/issues)
- **Repository**: [https://github.com/deidi/asset-vault](https://github.com/deidi/asset-vault)
