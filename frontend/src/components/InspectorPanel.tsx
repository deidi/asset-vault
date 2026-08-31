import React, { useState } from 'react';
import {
  X,
  FolderOpen,
  Edit2,
  Trash2,
  Lock,
  Maximize2,
  AlertCircle,
  Layers
} from 'lucide-react';
import type { Asset } from '../types';
import { getThumbnailUrl, revealInExplorer, renameOnDisk, trashToRecycleBin, updateAssetTags } from '../api';

interface InspectorPanelProps {
  asset: Asset | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenFullscreenPreview: (asset: Asset) => void;
  onAssetUpdated: (updated: Asset) => void;
  onAssetDeleted: (assetId: string) => void;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  asset,
  isOpen,
  onClose,
  onOpenFullscreenPreview,
  onAssetUpdated,
  onAssetDeleted,
}) => {
  const [isRenaming, setIsRenaming] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTagInput, setNewTagInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConfirmingTrash, setIsConfirmingTrash] = useState(false);

  if (!isOpen || !asset) return null;

  const thumbnailUrl = getThumbnailUrl(asset.id, 400, 300);

  const isProtectedTag = (tagName: string) => {
    const ext = asset.original_name.split('.').pop()?.toLowerCase() || '';
    const cleanTag = tagName.toLowerCase().replace(/^#/, '');
    return cleanTag === ext || cleanTag === asset.original_name.toLowerCase();
  };

  const handleStartRename = () => {
    setNewName(asset.name);
    setIsRenaming(true);
    setError(null);
  };

  const handleSaveRename = async () => {
    if (!newName.trim() || newName.trim() === asset.name) {
      setIsRenaming(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const updated = await renameOnDisk(asset.id, newName.trim());
      onAssetUpdated(updated);
      setIsRenaming(false);
    } catch (err: any) {
      setError(err.message || 'Rename failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async () => {
    const trimmed = newTagInput.trim().replace(/^#/, '');
    if (!trimmed) return;
    const existingNames = (asset.tags || []).map((t) => t.name.replace(/^#/, ''));
    if (existingNames.includes(trimmed)) {
      setNewTagInput('');
      return;
    }

    setLoading(true);
    try {
      const updated = await updateAssetTags(asset.id, [...existingNames, trimmed]);
      onAssetUpdated(updated);
      setNewTagInput('');
    } catch (err: any) {
      setError(err.message || 'Failed to add tag');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveTag = async (tagToRemove: string) => {
    const existingNames = (asset.tags || []).map((t) => t.name);
    const filtered = existingNames.filter((t) => t !== tagToRemove);
    setLoading(true);
    try {
      const updated = await updateAssetTags(asset.id, filtered);
      onAssetUpdated(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to remove tag');
    } finally {
      setLoading(false);
    }
  };

  const handleTrash = async () => {
    setLoading(true);
    setError(null);
    try {
      await trashToRecycleBin([asset.id]);
      onAssetDeleted(asset.id);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to send file to Recycle Bin');
      setIsConfirmingTrash(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="w-84 lg:w-96 border-l border-slate-800 bg-[#0c1324] flex flex-col h-full overflow-hidden shrink-0 animate-in slide-in-from-right-10 duration-200">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
        <div className="flex items-center space-x-2 text-slate-200">
          <Layers className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold tracking-wide uppercase">File Inspector</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          title="Close Inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content Scrollable */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center space-x-2 text-xs text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Small Interactive Preview Pane */}
        <div className="relative group rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 aspect-video flex items-center justify-center shadow-inner">
          <img
            src={thumbnailUrl}
            alt={asset.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          <button
            onClick={() => onOpenFullscreenPreview(asset)}
            className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center space-x-2 text-white text-xs font-semibold backdrop-blur-xs transition-opacity duration-200"
          >
            <Maximize2 className="w-4 h-4" />
            <span>Full-Screen Preview</span>
          </button>
        </div>

        {/* Filename & Quick Actions */}
        <div className="space-y-3">
          {isRenaming ? (
            <div className="space-y-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-950 border border-blue-500 rounded-lg text-slate-100 text-sm focus:outline-none"
                autoFocus
              />
              <div className="flex space-x-2">
                <button
                  onClick={handleSaveRename}
                  disabled={loading}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg font-medium transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => setIsRenaming(false)}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-start justify-between">
              <h4 className="text-base font-bold text-slate-100 break-all pr-2">{asset.name}</h4>
              <button
                onClick={handleStartRename}
                className="p-1.5 text-slate-400 hover:text-blue-400 rounded-lg hover:bg-slate-800 transition-colors"
                title="Rename on Disk"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Action Buttons Grid */}
          {isConfirmingTrash ? (
            <div className="p-3 bg-rose-950/40 border border-rose-500/40 rounded-xl space-y-2">
              <p className="text-xs text-rose-300 font-medium">
                Move "{asset.name}" to Windows Recycle Bin?
              </p>
              <div className="flex space-x-2">
                <button
                  onClick={handleTrash}
                  disabled={loading}
                  className="flex-1 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>{loading ? 'Moving...' : 'Yes, Delete'}</span>
                </button>
                <button
                  onClick={() => setIsConfirmingTrash(false)}
                  disabled={loading}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => revealInExplorer(asset.id)}
                className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 transition-colors shadow-xs"
              >
                <FolderOpen className="w-3.5 h-3.5 text-blue-400" />
                <span>Show in Explorer</span>
              </button>

              <button
                onClick={() => setIsConfirmingTrash(true)}
                disabled={loading}
                className="px-3 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Recycle Bin</span>
              </button>
            </div>
          )}
        </div>

        {/* Detailed Metadata Grid */}
        <div className="space-y-3 border-t border-slate-800/80 pt-4 text-xs">
          <h5 className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Metadata</h5>
          
          <div className="space-y-2.5 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60">
            <div className="flex justify-between">
              <span className="text-slate-500">File Size</span>
              <span className="text-slate-200 font-mono">
                {(asset.size_bytes / (1024 * 1024)).toFixed(2)} MB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">MIME Type</span>
              <span className="text-slate-200 font-mono">{asset.mime_type}</span>
            </div>
            {asset.file_modified_at && (
              <div className="flex justify-between">
                <span className="text-slate-500">Date Modified</span>
                <span className="text-slate-300 font-mono">
                  {new Date(asset.file_modified_at).toLocaleDateString()}
                </span>
              </div>
            )}
            <div>
              <span className="text-slate-500 block mb-1">Disk Path</span>
              <span className="text-slate-400 font-mono break-all text-[10px] block bg-slate-900 p-2 rounded-lg border border-slate-800 select-all">
                {asset.absolute_path || asset.storage_path}
              </span>
            </div>
          </div>
        </div>

        {/* Tag Management */}
        <div className="space-y-3 border-t border-slate-800/80 pt-4">
          <div className="flex items-center justify-between">
            <h5 className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Tags</h5>
            <span className="text-[10px] text-slate-500">{(asset.tags || []).length} assigned</span>
          </div>

          {/* Add Tag Input */}
          <div className="flex space-x-1.5">
            <input
              type="text"
              placeholder="Add tag..."
              value={newTagInput}
              onChange={(e) => setNewTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddTag();
                }
              }}
              className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleAddTag}
              disabled={loading || !newTagInput.trim()}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors"
            >
              Add
            </button>
          </div>

          {/* Tags Chips */}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {(asset.tags || []).map((t) => {
              const protectedTag = isProtectedTag(t.name);
              return (
                <span
                  key={t.id}
                  className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium border ${
                    protectedTag
                      ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                      : 'bg-blue-500/10 text-blue-300 border-blue-500/20'
                  }`}
                >
                  {protectedTag && <Lock className="w-2.5 h-2.5 mr-1 text-amber-400" />}
                  #{t.name.replace(/^#/, '')}
                  {!protectedTag && (
                    <button
                      onClick={() => handleRemoveTag(t.name)}
                      className="ml-1.5 text-slate-400 hover:text-rose-400"
                      title="Remove Tag"
                    >
                      &times;
                    </button>
                  )}
                </span>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
};
