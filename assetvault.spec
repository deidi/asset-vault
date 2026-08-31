# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

project_dir = os.path.abspath(SPECPATH)
backend_dir = os.path.join(project_dir, "backend")
public_dir = os.path.join(project_dir, "public")

added_files = [
    (public_dir, "public"),
]

# Add backend directory to path during analysis
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

a = Analysis(
    ['desktop_app.py'],
    pathex=[project_dir, backend_dir],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespans',
        'uvicorn.lifespans.on',
        'app',
        'app.main',
        'app.config',
        'app.db.session',
        'app.models',
        'app.models.asset',
        'app.models.tag',
        'app.models.association',
        'app.models.library_folder',
        'app.repositories',
        'app.repositories.asset_repository',
        'app.repositories.tag_repository',
        'app.repositories.library_folder_repository',
        'app.services',
        'app.services.asset_service',
        'app.services.tag_service',
        'app.services.folder_service',
        'app.services.explorer_service',
        'app.services.watcher_service',
        'app.services.connection_manager',
        'app.services.thumbnail_service',
        'app.routes',
        'app.routes.asset_routes',
        'app.routes.inventory_routes',
        'app.routes.folder_routes',
        'app.routes.explorer_routes',
        'app.routes.ws_routes',
        'app.routes.thumbnail_routes',
        'webview',
        'webview.platforms.winforms',
        'pypdfium2',
        'send2trash',
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.winapi',
        'watchdog.observers.read_directory_changes',
        'watchdog.events',
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.WebPImagePlugin',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AssetVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
