import React, { useState } from 'react';
import {
  Folder,
  FolderPlus,
  RefreshCw,
  Trash2,
  HardDrive,
  Database,
  Search,
  ChevronRight,
  Layers
} from 'lucide-react';
import type { LibraryFolder } from '../types';
import { scanFolder, scanAllFolders, deleteFolder, revealInExplorer } from '../api';

interface SidebarProps {
  folders: LibraryFolder[];
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onOpenAddFolder: () => void;
  onOpenCacheManager: () => void;
  onRefreshLibrary: () => void;
  availableTags: string[];
  selectedTags: string[];
  onToggleTag: (tag: string) => void;
  onClearTags: () => void;
  isWsConnected: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  folders,
  selectedFolderId,
  onSelectFolder,
  onOpenAddFolder,
  onOpenCacheManager,
  onRefreshLibrary,
  availableTags,
  selectedTags,
  onToggleTag,
  onClearTags,
  isWsConnected,
}) => {
  const [tagSearch, setTagSearch] = useState('');
  const [isScanningAll, setIsScanningAll] = useState(false);
  const [scanningFolderId, setScanningFolderId] = useState<string | null>(null);

  const handleScanFolder = async (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setScanningFolderId(folderId);
    try {
      await scanFolder(folderId);
      onRefreshLibrary();
    } catch {
      // error handled in api
    } finally {
      setScanningFolderId(null);
    }
  };

  const handleScanAll = async () => {
    setIsScanningAll(true);
    try {
      await scanAllFolders();
      onRefreshLibrary();
    } catch {
      // error handled in api
    } finally {
      setIsScanningAll(false);
    }
  };

  const handleDeleteFolder = async (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Remove this folder from AssetVault? Files on your disk will NOT be deleted.')) {
      try {
        await deleteFolder(folderId);
        if (selectedFolderId === folderId) onSelectFolder(null);
        onRefreshLibrary();
      } catch {
        // handle error
      }
    }
  };

  const filteredTags = availableTags.filter((t) =>
    t.toLowerCase().includes(tagSearch.toLowerCase())
  );

  return (
    <aside className="w-64 lg:w-72 bg-[#090e1c] border-r border-slate-800 flex flex-col h-full shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white font-black text-base">
            AV
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100 tracking-tight">AssetVault</h1>
            <div className="flex items-center space-x-1.5 mt-0.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isWsConnected ? 'bg-emerald-400 shadow-xs shadow-emerald-400' : 'bg-amber-400'
                }`}
              />
              <span className="text-[11px] text-slate-400 font-medium">
                {isWsConnected ? 'Live Sync Active' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation & Folders */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* All Media View */}
        <div>
          <button
            onClick={() => onSelectFolder(null)}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
              selectedFolderId === null
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100'
            }`}
          >
            <div className="flex items-center space-x-2.5">
              <Layers className="w-4 h-4" />
              <span>All Assets Library</span>
            </div>
          </button>
        </div>

        {/* Library Folders Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Library Folders ({folders.length})
            </span>
            <div className="flex items-center space-x-1">
              <button
                onClick={handleScanAll}
                disabled={isScanningAll}
                className="p-1 rounded-md text-slate-400 hover:text-blue-400 hover:bg-slate-800 transition-colors"
                title="Scan All Folders"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isScanningAll ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={onOpenAddFolder}
                className="p-1 rounded-md text-slate-400 hover:text-blue-400 hover:bg-slate-800 transition-colors"
                title="Add Library Folder"
              >
                <FolderPlus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="space-y-1">
            {folders.map((f) => {
              const isSelected = selectedFolderId === f.id;
              const isScanning = scanningFolderId === f.id;

              return (
                <div
                  key={f.id}
                  onClick={() => onSelectFolder(f.id)}
                  className={`group relative flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-slate-800 text-blue-400 font-semibold border border-blue-500/30'
                      : 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 truncate pr-2">
                    <Folder className={`w-4 h-4 shrink-0 ${isSelected ? 'text-blue-400' : 'text-slate-400'}`} />
                    <span className="truncate">{f.name}</span>
                  </div>

                  <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handleScanFolder(f.id, e)}
                      disabled={isScanning}
                      className="p-1 text-slate-400 hover:text-blue-400 rounded-md hover:bg-slate-700/60"
                      title="Rescan this folder"
                    >
                      <RefreshCw className={`w-3 h-3 ${isScanning ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        revealInExplorer(undefined, f.id);
                      }}
                      className="p-1 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-700/60"
                      title="Open in Explorer"
                    >
                      <HardDrive className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteFolder(f.id, e)}
                      className="p-1 text-slate-400 hover:text-rose-400 rounded-md hover:bg-slate-700/60"
                      title="Remove folder"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })}

            {folders.length === 0 && (
              <div
                onClick={onOpenAddFolder}
                className="p-3 text-center rounded-xl border border-dashed border-slate-800 hover:border-slate-700 cursor-pointer text-slate-500 hover:text-slate-400 transition-colors"
              >
                <span className="text-[11px]">No folders added yet. Click to add.</span>
              </div>
            )}
          </div>
        </div>

        {/* Tags Section */}
        <div className="space-y-2 border-t border-slate-800/80 pt-4">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Filter Tags {selectedTags.length > 0 && `(${selectedTags.length})`}
            </span>
            {selectedTags.length > 0 && (
              <button
                onClick={onClearTags}
                className="text-[10px] text-blue-400 hover:text-blue-300 font-semibold"
              >
                Clear
              </button>
            )}
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search tags..."
              value={tagSearch}
              onChange={(e) => setTagSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex flex-wrap gap-1 max-h-48 overflow-y-auto pt-1">
            {filteredTags.map((tag) => {
              const isSelected = selectedTags.includes(tag);
              return (
                <button
                  key={tag}
                  onClick={() => onToggleTag(tag)}
                  className={`px-2 py-1 rounded-lg text-[11px] font-medium transition-all ${
                    isSelected
                      ? 'bg-blue-600 text-white font-semibold shadow-xs shadow-blue-500/20'
                      : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800/80'
                  }`}
                >
                  #{tag}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer Controls */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <button
          onClick={onOpenCacheManager}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-slate-800/60 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Database className="w-4 h-4 text-purple-400" />
            <span>Cache & Diagnostics</span>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
        </button>
      </div>
    </aside>
  );
};
