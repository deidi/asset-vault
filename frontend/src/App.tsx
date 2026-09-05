import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Search,
  LayoutGrid,
  Grid3X3,
  Layers,
  RefreshCw,
  FolderPlus,
  PanelRight,
  PanelRightClose,
  ArrowUpDown,
  CheckSquare,
  Square,
  X,
  Image as ImageIcon,
  Film,
  Music,
  FileText,
  Package,
  SlidersHorizontal
} from 'lucide-react';
import type { Asset, LibraryFolder, WebSocketEvent } from './types';
import { fetchAssets, fetchFolders } from './api';
import { useWebSocket } from './useWebSocket';
import { Sidebar } from './components/Sidebar';
import { MediaGrid } from './components/MediaGrid';
import { InspectorPanel } from './components/InspectorPanel';
import { BulkActionsBar } from './components/BulkActionsBar';
import { PreviewModal } from './components/PreviewModal';
import { AddFolderModal } from './components/AddFolderModal';
import { CacheManagerModal } from './components/CacheManagerModal';
import { FileTypeSettingsModal } from './components/FileTypeSettingsModal';

export const App: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [folders, setFolders] = useState<LibraryFolder[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedSubfolderPath, setSelectedSubfolderPath] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedFileType, setSelectedFileType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [gridSize, setGridSize] = useState<'small' | 'medium' | 'large'>('medium');

  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([]);
  const [activeAssetId, setActiveAssetId] = useState<string | null>(null);
  const [lastSelectedAssetId, setLastSelectedAssetId] = useState<string | null>(null);

  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [previewModalAsset, setPreviewModalAsset] = useState<Asset | null>(null);
  const [isAddFolderOpen, setIsAddFolderOpen] = useState(false);
  const [isCacheManagerOpen, setIsCacheManagerOpen] = useState(false);
  const [isFileTypeSettingsOpen, setIsFileTypeSettingsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [totalCount, setTotalCount] = useState<number>(0);

  // Load Library Data
  const loadLibrary = useCallback(async () => {
    setLoading(true);
    try {
      const foldersRes = await fetchFolders();
      const allAssetsCount = foldersRes.reduce((sum, f) => sum + (f.asset_count || 0), 0);
      const dynamicPageSize = Math.max(1000, allAssetsCount);

      const assetsRes = await fetchAssets({
        page: 1,
        pageSize: dynamicPageSize,
        search: searchQuery || undefined,
        folderId: selectedFolderId || undefined,
        subfolderPath: selectedSubfolderPath || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
        fileType: selectedFileType,
        sortBy,
        sortOrder,
      });

      const list = assetsRes.assets || assetsRes.items || [];
      setAssets(list);
      setTotalCount(assetsRes.total ?? list.length);
      setFolders(foldersRes);
    } catch (err) {
      console.error('Error loading library:', err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedFolderId, selectedSubfolderPath, selectedTags, selectedFileType, sortBy, sortOrder]);

  // Initial Load & Debounced Filter Trigger
  useEffect(() => {
    const handler = setTimeout(() => {
      loadLibrary();
    }, 150);
    return () => clearTimeout(handler);
  }, [loadLibrary]);

  // Live WebSocket Event Handler
  const handleWsEvent = useCallback((_event: WebSocketEvent) => {
    // When files are added, modified, renamed or deleted, silently reload
    loadLibrary();
  }, [loadLibrary]);

  // Global Keyboard Shortcuts (Ctrl+A to Select All, Escape to clear selection)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept when focusing on text input or textarea
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return;
      }

      // Do not trigger global selection if a modal is open
      if (previewModalAsset || isAddFolderOpen || isCacheManagerOpen) {
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
        e.preventDefault();
        if (assets.length > 0) {
          setSelectedAssetIds(assets.map((a) => a.id));
        }
      } else if (e.key === 'Escape') {
        setSelectedAssetIds([]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [assets, previewModalAsset, isAddFolderOpen, isCacheManagerOpen]);

  const { isConnected } = useWebSocket(handleWsEvent);

  // Extract all available tags across library
  const availableTags = useMemo(() => {
    const set = new Set<string>();
    assets.forEach((a) => (a.tags || []).forEach((t) => set.add(t.name.replace(/^#/, ''))));
    return Array.from(set).sort();
  }, [assets]);

  // Active Asset Object for Inspector
  const activeAsset = useMemo(() => {
    if (!activeAssetId) return assets.length > 0 ? assets[0] : null;
    return assets.find((a) => a.id === activeAssetId) || null;
  }, [assets, activeAssetId]);

  // Selection Handler (Single, Multi-select, Range)
  const handleSelectAsset = (asset: Asset, isMulti: boolean, isRange: boolean) => {
    setActiveAssetId(asset.id);

    if (isRange && lastSelectedAssetId) {
      const lastIdx = assets.findIndex((a) => a.id === lastSelectedAssetId);
      const currIdx = assets.findIndex((a) => a.id === asset.id);
      if (lastIdx !== -1 && currIdx !== -1) {
        const start = Math.min(lastIdx, currIdx);
        const end = Math.max(lastIdx, currIdx);
        const rangeIds = assets.slice(start, end + 1).map((a) => a.id);
        setSelectedAssetIds(Array.from(new Set([...selectedAssetIds, ...rangeIds])));
        return;
      }
    }

    if (isMulti) {
      if (selectedAssetIds.includes(asset.id)) {
        setSelectedAssetIds(selectedAssetIds.filter((id) => id !== asset.id));
      } else {
        setSelectedAssetIds([...selectedAssetIds, asset.id]);
      }
    } else {
      setSelectedAssetIds([asset.id]);
    }
    setLastSelectedAssetId(asset.id);
  };

  const handleSelectAll = () => {
    if (selectedAssetIds.length === assets.length) {
      setSelectedAssetIds([]);
    } else {
      setSelectedAssetIds(assets.map((a) => a.id));
    }
  };

  const handleToggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter((t) => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  const handleAssetUpdated = (updated: Asset) => {
    setAssets((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  };

  const handleAssetDeleted = (deletedId: string) => {
    setAssets((prev) => prev.filter((a) => a.id !== deletedId));
    setSelectedAssetIds((prev) => prev.filter((id) => id !== deletedId));
    if (activeAssetId === deletedId) {
      setActiveAssetId(null);
    }
  };

  const fileTypeOptions = useMemo(() => [
    { value: 'all', label: 'All Files', icon: Layers, activeColor: 'text-blue-400' },
    { value: 'image', label: 'Images', icon: ImageIcon, activeColor: 'text-blue-400' },
    { value: 'video', label: 'Videos', icon: Film, activeColor: 'text-indigo-400' },
    { value: 'audio', label: 'Audio', icon: Music, activeColor: 'text-emerald-400' },
    { value: 'document', label: 'Documents', icon: FileText, activeColor: 'text-rose-400' },
    { value: 'other', label: 'Other Files', icon: Package, activeColor: 'text-amber-400' },
  ], []);

  const activeFolderName = useMemo(() => {
    if (selectedSubfolderPath) {
      const parts = selectedSubfolderPath.split(/[\\/]/).filter(Boolean);
      return parts.length > 0 ? parts[parts.length - 1] : 'Subfolder';
    }
    if (selectedFolderId) {
      return folders.find((f) => f.id === selectedFolderId)?.name || 'Folder';
    }
    return 'All Library Assets';
  }, [selectedFolderId, selectedSubfolderPath, folders]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090e1c] text-slate-100 font-sans antialiased select-none">
      {/* 1. Left Sidebar */}
      <Sidebar
        folders={folders}
        totalAllAssetsCount={folders.reduce((sum, f) => sum + (f.asset_count || 0), 0)}
        selectedFolderId={selectedFolderId}
        selectedSubfolderPath={selectedSubfolderPath}
        onSelectFolder={(id, sPath) => {
          setSelectedFolderId(id);
          setSelectedSubfolderPath(sPath || null);
          setSelectedAssetIds([]);
        }}
        onOpenAddFolder={() => setIsAddFolderOpen(true)}
        onOpenCacheManager={() => setIsCacheManagerOpen(true)}
        onOpenFileTypes={() => setIsFileTypeSettingsOpen(true)}
        onRefreshLibrary={loadLibrary}
        availableTags={availableTags}
        selectedTags={selectedTags}
        onToggleTag={handleToggleTag}
        onClearTags={() => setSelectedTags([])}
        isWsConnected={isConnected}
      />

      {/* 2. Main Content Canvas */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-[#0b1329] overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-800/80 px-4 md:px-6 flex items-center justify-between gap-3 bg-slate-900/40 backdrop-blur-md shrink-0">
          {/* Left Title & Status */}
          <div className="flex items-center space-x-2.5 min-w-0 shrink truncate">
            <h2 className="text-sm md:text-base font-bold text-slate-100 truncate">{activeFolderName}</h2>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono font-medium shrink-0">
              {totalCount.toLocaleString()}
            </span>
          </div>

          {/* Dynamic Adaptive Search Input */}
          <div className="flex-1 min-w-[140px] sm:min-w-[200px] max-w-lg transition-all duration-300 ease-out focus-within:max-w-2xl focus-within:ring-1 focus-within:ring-blue-500/50 rounded-xl">
            <div className="relative flex items-center">
              <Search className="w-4 h-4 absolute left-3.5 text-slate-500 pointer-events-none shrink-0" />
              <input
                type="text"
                placeholder="Search assets, filenames, tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-9 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-500 shadow-inner"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors"
                  title="Clear search"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Right Toolbar Controls */}
          <div className="flex items-center space-x-1.5 md:space-x-2 shrink-0">
            {/* Select All Toggle */}
            <button
              onClick={handleSelectAll}
              className={`p-2 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                selectedAssetIds.length > 0
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
              title={selectedAssetIds.length === assets.length ? 'Deselect All' : 'Select All (Ctrl+A)'}
            >
              {selectedAssetIds.length === assets.length && assets.length > 0 ? (
                <CheckSquare className="w-4 h-4" />
              ) : (
                <Square className="w-4 h-4" />
              )}
            </button>

            {/* Sort Order Selector */}
            <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent text-slate-300 text-xs px-2 py-1 focus:outline-none cursor-pointer"
              >
                <option value="created_at" className="bg-slate-900">Date Added</option>
                <option value="name" className="bg-slate-900">Filename</option>
                <option value="size_bytes" className="bg-slate-900">File Size</option>
              </select>
              <button
                onClick={() => setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'))}
                className="p-1 text-slate-400 hover:text-slate-200 rounded-lg"
                title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Grid Size Toggle */}
            <div className="flex items-center space-x-0.5 bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
              <button
                onClick={() => setGridSize('small')}
                className={`p-1.5 rounded-lg transition-colors ${
                  gridSize === 'small' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Small Grid"
              >
                <Grid3X3 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setGridSize('medium')}
                className={`p-1.5 rounded-lg transition-colors ${
                  gridSize === 'medium' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Medium Grid"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={loadLibrary}
              disabled={loading}
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
              title="Refresh Library"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>

            {/* Inspector Toggle Button */}
            <button
              onClick={() => setIsInspectorOpen(!isInspectorOpen)}
              className={`p-2 rounded-xl transition-colors border ${
                isInspectorOpen
                  ? 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
              title="Toggle Inspector Panel (Ctrl+I)"
            >
              {isInspectorOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRight className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Sub-Header Filter Bar: File Types */}
        <div className="h-11 border-b border-slate-800/70 px-4 md:px-6 flex items-center justify-between gap-2 bg-slate-900/30 backdrop-blur-xs shrink-0 overflow-x-auto no-scrollbar">
          <div className="flex items-center space-x-1 sm:space-x-1.5">
            {fileTypeOptions.map((opt) => {
              const isSelected = selectedFileType === opt.value;
              const Icon = opt.icon;
              return (
                <button
                  key={opt.value}
                  onClick={() => setSelectedFileType(opt.value)}
                  className={`flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-medium transition-all duration-150 whitespace-nowrap cursor-pointer ${
                    isSelected
                      ? 'bg-blue-600/25 text-blue-300 border border-blue-500/40 shadow-xs shadow-blue-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isSelected ? opt.activeColor : 'text-slate-500'}`} />
                  <span>{opt.label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            {selectedFileType !== 'all' && (
              <button
                onClick={() => setSelectedFileType('all')}
                className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center space-x-1 px-2 py-0.5 rounded-lg hover:bg-slate-800/60 transition-colors cursor-pointer"
                title="Reset file type filter"
              >
                <span>Reset filter</span>
                <X className="w-3 h-3" />
              </button>
            )}

            <button
              onClick={() => setIsFileTypeSettingsOpen(true)}
              className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center space-x-1.5 px-2.5 py-1 rounded-lg hover:bg-slate-800/80 border border-slate-700/50 hover:border-slate-600 transition-all cursor-pointer"
              title="Configure Category File Types"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
              <span>Configure Types</span>
            </button>
          </div>
        </div>

        {/* Media Grid Canvas */}
        <div className="flex-1 overflow-y-auto">
          {assets.length > 0 ? (
            <MediaGrid
              assets={assets}
              selectedAssetIds={selectedAssetIds}
              activeAssetId={activeAssetId}
              onSelectAsset={handleSelectAsset}
              onOpenFullscreenPreview={(asset) => setPreviewModalAsset(asset)}
              gridSize={gridSize}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
                <Layers className="w-8 h-8" />
              </div>
              <div className="max-w-md">
                <h3 className="text-base font-bold text-slate-200">
                  {selectedFileType !== 'all' ? `No ${selectedFileType} assets found` : 'No assets found'}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  {selectedFileType !== 'all'
                    ? `There are no assets matching the '${selectedFileType}' filter in this view.`
                    : selectedFolderId
                    ? 'This folder does not contain any supported media files yet.'
                    : 'Add a library folder from the sidebar or drop media files to begin.'}
                </p>
              </div>
              {selectedFileType !== 'all' ? (
                <button
                  onClick={() => setSelectedFileType('all')}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 flex items-center space-x-2 transition-all cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Show All File Types</span>
                </button>
              ) : (
                <button
                  onClick={() => setIsAddFolderOpen(true)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/25 flex items-center space-x-2 transition-all cursor-pointer"
                >
                  <FolderPlus className="w-4 h-4" />
                  <span>Add Library Folder</span>
                </button>
              )}
            </div>
          )}
        </div>
      </main>

      {/* 3. Collapsible Right-Hand Inspector Panel */}
      <InspectorPanel
        asset={activeAsset}
        isOpen={isInspectorOpen && activeAsset !== null}
        onClose={() => setIsInspectorOpen(false)}
        onOpenFullscreenPreview={(asset) => setPreviewModalAsset(asset)}
        onAssetUpdated={handleAssetUpdated}
        onAssetDeleted={handleAssetDeleted}
      />

      {/* 4. Floating Bulk Actions Toolbar */}
      <BulkActionsBar
        selectedAssetIds={selectedAssetIds}
        assets={assets}
        onClearSelection={() => setSelectedAssetIds([])}
        onRefreshLibrary={loadLibrary}
      />

      {/* 5. Full-Screen Interactive Preview Modal */}
      {previewModalAsset && (
        <PreviewModal
          asset={previewModalAsset}
          assetsList={assets}
          onClose={() => setPreviewModalAsset(null)}
          onSelectAsset={(a) => setPreviewModalAsset(a)}
        />
      )}

      {/* 6. Modals */}
      <AddFolderModal
        isOpen={isAddFolderOpen}
        onClose={() => setIsAddFolderOpen(false)}
        onFolderAdded={(folder) => {
          setSelectedFolderId(folder.id);
          loadLibrary();
        }}
      />

      <CacheManagerModal
        isOpen={isCacheManagerOpen}
        onClose={() => setIsCacheManagerOpen(false)}
        onRefreshLibrary={loadLibrary}
      />

      <FileTypeSettingsModal
        isOpen={isFileTypeSettingsOpen}
        onClose={() => setIsFileTypeSettingsOpen(false)}
        onSaved={loadLibrary}
      />
    </div>
  );
};

export default App;
