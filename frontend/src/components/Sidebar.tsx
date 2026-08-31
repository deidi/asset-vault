import React, { useState, useEffect } from 'react';
import {
  Folder,
  FolderOpen,
  FolderPlus,
  RefreshCw,
  Trash2,
  Database,
  Search,
  ChevronRight,
  ChevronDown,
  Layers,
  FolderTree as FolderTreeIcon
} from 'lucide-react';
import type { LibraryFolder, FolderTreeNode } from '../types';
import { scanFolder, scanAllFolders, deleteFolder, revealInExplorer, fetchFolderTree } from '../api';

interface SidebarProps {
  folders: LibraryFolder[];
  totalAllAssetsCount?: number;
  selectedFolderId: string | null;
  selectedSubfolderPath: string | null;
  onSelectFolder: (folderId: string | null, subfolderPath?: string | null) => void;
  onOpenAddFolder: () => void;
  onOpenCacheManager: () => void;
  onRefreshLibrary: () => void;
  availableTags: string[];
  selectedTags: string[];
  onToggleTag: (tag: string) => void;
  onClearTags: () => void;
  isWsConnected: boolean;
}

interface TreeNodeProps {
  node: FolderTreeNode;
  folderId: string;
  selectedFolderId: string | null;
  selectedSubfolderPath: string | null;
  onSelect: (folderId: string, path: string) => void;
  depth: number;
}

const SubfolderTreeNode: React.FC<TreeNodeProps> = ({
  node,
  folderId,
  selectedFolderId,
  selectedSubfolderPath,
  onSelect,
  depth
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedFolderId === folderId && selectedSubfolderPath === node.path;

  return (
    <div className="flex flex-col select-none">
      <div
        onClick={() => onSelect(folderId, node.path)}
        style={{ paddingLeft: `${Math.max(12, depth * 14)}px` }}
        className={`group flex items-center justify-between pr-2 py-1.5 rounded-lg text-xs cursor-pointer transition-all ${
          isSelected
            ? 'bg-blue-600/25 text-blue-300 font-semibold border border-blue-500/40'
            : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
        }`}
      >
        <div className="flex items-center space-x-1.5 truncate pr-1">
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              className="p-0.5 hover:bg-slate-700/60 rounded text-slate-400 hover:text-slate-200 transition-colors"
            >
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
            </button>
          ) : (
            <span className="w-3.5 h-3.5 shrink-0" />
          )}

          {isSelected ? (
            <FolderOpen className="w-3.5 h-3.5 text-blue-400 shrink-0" />
          ) : (
            <Folder className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300 shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </div>

        {node.asset_count > 0 && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/90 text-slate-400 group-hover:text-slate-300 shrink-0 ml-1">
            {node.asset_count.toLocaleString()}
          </span>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div className="flex flex-col space-y-0.5 mt-0.5 border-l border-slate-800/60 ml-3">
          {node.children.map((child) => (
            <SubfolderTreeNode
              key={child.path}
              node={child}
              folderId={folderId}
              selectedFolderId={selectedFolderId}
              selectedSubfolderPath={selectedSubfolderPath}
              onSelect={onSelect}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const Sidebar: React.FC<SidebarProps> = ({
  folders,
  totalAllAssetsCount,
  selectedFolderId,
  selectedSubfolderPath,
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
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [folderTrees, setFolderTrees] = useState<Record<string, FolderTreeNode>>({});
  const [loadingTrees, setLoadingTrees] = useState<Record<string, boolean>>({});

  // Auto-expand and load tree for selected folder
  const loadTree = async (folderId: string) => {
    if (folderTrees[folderId] || loadingTrees[folderId]) return;
    setLoadingTrees((prev) => ({ ...prev, [folderId]: true }));
    try {
      const tree = await fetchFolderTree(folderId);
      setFolderTrees((prev) => ({ ...prev, [folderId]: tree }));
    } catch (err) {
      console.warn(`Failed loading tree for folder ${folderId}:`, err);
    } finally {
      setLoadingTrees((prev) => ({ ...prev, [folderId]: false }));
    }
  };

  const toggleFolderExpansion = (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedFolders((prev) => {
      const next = !prev[folderId];
      if (next && !folderTrees[folderId]) {
        loadTree(folderId);
      }
      return { ...prev, [folderId]: next };
    });
  };

  useEffect(() => {
    if (selectedFolderId) {
      setExpandedFolders((prev) => ({ ...prev, [selectedFolderId]: true }));
      loadTree(selectedFolderId);
    }
  }, [selectedFolderId]);

  const handleScanFolder = async (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setScanningFolderId(folderId);
    try {
      await scanFolder(folderId);
      const tree = await fetchFolderTree(folderId);
      setFolderTrees((prev) => ({ ...prev, [folderId]: tree }));
      onRefreshLibrary();
    } catch (err) {
      console.error('Scan folder failed:', err);
    } finally {
      setScanningFolderId(null);
    }
  };

  const handleScanAll = async () => {
    setIsScanningAll(true);
    try {
      await scanAllFolders();
      for (const f of folders) {
        if (expandedFolders[f.id]) {
          try {
            const tree = await fetchFolderTree(f.id);
            setFolderTrees((prev) => ({ ...prev, [f.id]: tree }));
          } catch {
            // ignore
          }
        }
      }
      onRefreshLibrary();
    } catch (err) {
      console.error('Scan all failed:', err);
    } finally {
      setIsScanningAll(false);
    }
  };

  const handleDeleteFolder = async (folderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const folder = folders.find((f) => f.id === folderId);
    if (!folder) return;
    if (window.confirm(`Are you sure you want to remove '${folder.name}' from AssetVault? Disk files will NOT be deleted.`)) {
      try {
        await deleteFolder(folderId);
        if (selectedFolderId === folderId) {
          onSelectFolder(null, null);
        }
        onRefreshLibrary();
      } catch {
        // handle error
      }
    }
  };

  const filteredTags = availableTags.filter((t) =>
    t.toLowerCase().includes(tagSearch.toLowerCase())
  );

  const totalVaultCount = totalAllAssetsCount ?? folders.reduce((sum, f) => sum + (f.asset_count || 0), 0);

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
            onClick={() => onSelectFolder(null, null)}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
              selectedFolderId === null && selectedSubfolderPath === null
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100'
            }`}
          >
            <div className="flex items-center space-x-2.5">
              <Layers className="w-4 h-4" />
              <span>All Assets Library</span>
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-medium ${
              selectedFolderId === null && selectedSubfolderPath === null
                ? 'bg-blue-500/30 text-white border border-blue-400/30'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {totalVaultCount.toLocaleString()}
            </span>
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
              const isSelected = selectedFolderId === f.id && selectedSubfolderPath === null;
              const isScanning = scanningFolderId === f.id;
              const isExpanded = !!expandedFolders[f.id];
              const tree = folderTrees[f.id];
              const hasSubfolders = tree && tree.children && tree.children.length > 0;
              const count = f.asset_count ?? tree?.asset_count ?? 0;

              return (
                <div key={f.id} className="flex flex-col">
                  <div
                    onClick={() => onSelectFolder(f.id, null)}
                    className={`group relative flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-slate-800 text-blue-400 font-semibold border border-blue-500/30'
                        : 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100'
                    }`}
                  >
                    <div className="flex items-center space-x-2 truncate pr-2 flex-1 min-w-0">
                      <button
                        onClick={(e) => toggleFolderExpansion(f.id, e)}
                        className="p-0.5 hover:bg-slate-700/60 rounded text-slate-400 hover:text-slate-200 transition-colors"
                        title={isExpanded ? 'Collapse subfolders' : 'Expand subfolders'}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {isSelected ? (
                        <FolderOpen className="w-4 h-4 text-blue-400 shrink-0" />
                      ) : (
                        <Folder className="w-4 h-4 text-slate-400 shrink-0" />
                      )}
                      <span className="truncate flex-1">{f.name}</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-md font-medium shrink-0 ml-1 ${
                        isSelected
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          : 'bg-slate-800/80 text-slate-400 group-hover:text-slate-300'
                      }`}>
                        {count.toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button
                        onClick={(e) => handleScanFolder(f.id, e)}
                        disabled={isScanning}
                        className="p-1 rounded text-slate-400 hover:text-blue-400 hover:bg-slate-700 transition-colors"
                        title="Rescan this folder"
                      >
                        <RefreshCw className={`w-3 h-3 ${isScanning ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          revealInExplorer(undefined, f.id);
                        }}
                        className="p-1 rounded text-slate-400 hover:text-blue-400 hover:bg-slate-700 transition-colors"
                        title="Show folder in Explorer"
                      >
                        <FolderTreeIcon className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteFolder(f.id, e)}
                        className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-slate-700 transition-colors"
                        title="Remove folder"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {/* Subfolder Tree Nodes */}
                  {isExpanded && hasSubfolders && (
                    <div className="flex flex-col space-y-0.5 mt-1 ml-4 border-l border-slate-800/60 pl-1">
                      {tree.children.map((child) => (
                        <SubfolderTreeNode
                          key={child.path}
                          node={child}
                          folderId={f.id}
                          selectedFolderId={selectedFolderId}
                          selectedSubfolderPath={selectedSubfolderPath}
                          onSelect={(fId, sPath) => onSelectFolder(fId, sPath)}
                          depth={1}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {folders.length === 0 && (
              <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center space-y-2">
                <p className="text-xs text-slate-500">No media folders added yet.</p>
                <button
                  onClick={onOpenAddFolder}
                  className="px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 text-xs font-semibold rounded-lg transition-colors inline-flex items-center space-x-1.5"
                >
                  <FolderPlus className="w-3.5 h-3.5" />
                  <span>Add Folder</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tags Filter Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Tags ({availableTags.length})
            </span>
            {selectedTags.length > 0 && (
              <button
                onClick={onClearTags}
                className="text-[10px] text-blue-400 hover:underline font-medium"
              >
                Clear all ({selectedTags.length})
              </button>
            )}
          </div>

          {/* Search Tags */}
          {availableTags.length > 8 && (
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Filter tags..."
                value={tagSearch}
                onChange={(e) => setTagSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-900/80 border border-slate-800 rounded-lg text-slate-300 text-xs focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-600"
              />
            </div>
          )}

          {/* Tag List */}
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
            {filteredTags.map((tag) => {
              const isSelected = selectedTags.includes(tag);
              return (
                <button
                  key={tag}
                  onClick={() => onToggleTag(tag)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                    isSelected
                      ? 'bg-blue-600 text-white shadow-xs shadow-blue-500/30'
                      : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800/80'
                  }`}
                >
                  #{tag}
                </button>
              );
            })}

            {filteredTags.length === 0 && (
              <p className="text-xs text-slate-600 px-1 italic">No matching tags</p>
            )}
          </div>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
        <button
          onClick={onOpenCacheManager}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-800/60 hover:text-slate-200 transition-colors w-full"
        >
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span>Storage & Cache</span>
        </button>
      </div>
    </aside>
  );
};
