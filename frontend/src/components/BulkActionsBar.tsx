import React, { useState, useMemo } from 'react';
import {
  Trash2,
  FolderInput,
  FolderOpen,
  X,
  Plus,
  Minus,
  Tag as TagIcon
} from 'lucide-react';
import type { Asset } from '../types';
import { batchUpdateTags, trashToRecycleBin, batchMove, pickFolderDialog } from '../api';

interface BulkActionsBarProps {
  selectedAssetIds: string[];
  assets: Asset[];
  onClearSelection: () => void;
  onRefreshLibrary: () => void;
}

export const BulkActionsBar: React.FC<BulkActionsBarProps> = ({
  selectedAssetIds,
  assets,
  onClearSelection,
  onRefreshLibrary,
}) => {
  const [activeModal, setActiveModal] = useState<'add_tags' | 'remove_tags' | 'move' | 'trash' | null>(null);
  const [tagInput, setTagInput] = useState('');
  const [moveDestDir, setMoveDestDir] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedAssets = useMemo(() => {
    return assets.filter((a) => selectedAssetIds.includes(a.id));
  }, [assets, selectedAssetIds]);

  // Compute common tags across all selected assets
  const commonTags = useMemo(() => {
    if (selectedAssets.length === 0) return [];
    const tagSets = selectedAssets.map((asset) => {
      const set = new Set<string>();
      (asset.tags || []).forEach((t) => {
        const clean = t.name.replace(/^#/, '').trim();
        if (clean) set.add(clean);
      });
      return set;
    });

    const firstSet = tagSets[0];
    const intersection = Array.from(firstSet).filter((tag) =>
      tagSets.every((set) => set.has(tag))
    );
    return intersection.sort((a, b) => a.localeCompare(b));
  }, [selectedAssets]);

  if (selectedAssetIds.length === 0) return null;

  const count = selectedAssetIds.length;

  const handleApplyAddTags = async () => {
    const tags = tagInput
      .split(',')
      .map((t) => t.trim().replace(/^#/, ''))
      .filter(Boolean);

    if (tags.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      await batchUpdateTags(selectedAssetIds, 'add', tags);
      setActiveModal(null);
      setTagInput('');
      onRefreshLibrary();
    } catch (err: any) {
      setError(err.message || 'Tag update failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveSingleCommonTag = async (tagName: string) => {
    const cleanTag = tagName.replace(/^#/, '').trim();
    if (!cleanTag) return;

    setLoading(true);
    setError(null);
    try {
      await batchUpdateTags(selectedAssetIds, 'remove', [cleanTag]);
      onRefreshLibrary();
    } catch (err: any) {
      setError(err.message || 'Failed to remove tag');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveAllCommonTags = async () => {
    if (commonTags.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      await batchUpdateTags(selectedAssetIds, 'remove', commonTags);
      onRefreshLibrary();
    } catch (err: any) {
      setError(err.message || 'Failed to remove all common tags');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchMove = async () => {
    const cleanDir = moveDestDir.trim().replace(/^["']|["']$/g, '');
    if (!cleanDir) return;
    setLoading(true);
    setError(null);
    try {
      const res = await batchMove(selectedAssetIds, cleanDir);
      if (res && res.moved_count > 0) {
        setActiveModal(null);
        setMoveDestDir('');
        onClearSelection();
        onRefreshLibrary();
        return;
      }
      if (res && res.errors && res.errors.length > 0) {
        setError(res.errors.join(', '));
      } else {
        setError('Failed to move files');
      }
    } catch (err: any) {
      setError(err.message || 'Move failed');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchTrash = async () => {
    setLoading(true);
    setError(null);
    try {
      await trashToRecycleBin(selectedAssetIds);
      setActiveModal(null);
      onClearSelection();
      onRefreshLibrary();
    } catch (err: any) {
      setError(err.message || 'Failed to send items to Recycle Bin');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Action Bar */}
      <div className="fixed bottom-6 inset-x-0 z-40 flex justify-center px-4 pointer-events-none">
        <div className="bg-[#0f172a]/95 border border-slate-700/80 rounded-2xl shadow-2xl backdrop-blur-xl px-5 py-3 flex items-center space-x-3 text-slate-200 pointer-events-auto animate-in slide-in-from-bottom-6 duration-200">
          <div className="flex items-center space-x-2 pr-3 border-r border-slate-800">
            <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
              {count}
            </span>
            <span className="text-xs font-semibold text-slate-300">Selected</span>
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => {
                setError(null);
                setTagInput('');
                setActiveModal('add_tags');
              }}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-blue-400" />
              <span>Add Tags</span>
            </button>

            <button
              onClick={() => {
                setError(null);
                setActiveModal('remove_tags');
              }}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Minus className="w-3.5 h-3.5 text-amber-400" />
              <span>Remove Tags</span>
            </button>

            <button
              onClick={() => {
                setError(null);
                setActiveModal('move');
              }}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <FolderInput className="w-3.5 h-3.5 text-emerald-400" />
              <span>Move Files</span>
            </button>

            <button
              onClick={() => {
                setError(null);
                setActiveModal('trash');
              }}
              className="px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Recycle Bin</span>
            </button>
          </div>

          <button
            onClick={onClearSelection}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors ml-2 cursor-pointer"
            title="Deselect All"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Sub-modals for Bulk Operations */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-[#0f172a] border border-slate-750 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h4 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                {activeModal === 'add_tags' && (
                  <>
                    <Plus className="w-4 h-4 text-blue-400" />
                    <span>Add Tags to {count} Asset{count > 1 ? 's' : ''}</span>
                  </>
                )}
                {activeModal === 'remove_tags' && (
                  <>
                    <Minus className="w-4 h-4 text-amber-400" />
                    <span>Remove Common Tags ({count} Assets)</span>
                  </>
                )}
                {activeModal === 'move' && (
                  <>
                    <FolderInput className="w-4 h-4 text-emerald-400" />
                    <span>Move {count} Asset{count > 1 ? 's' : ''} to Another Folder</span>
                  </>
                )}
                {activeModal === 'trash' && (
                  <>
                    <Trash2 className="w-4 h-4 text-rose-400" />
                    <span>Send {count} Asset{count > 1 ? 's' : ''} to Recycle Bin</span>
                  </>
                )}
              </h4>
              <button
                onClick={() => setActiveModal(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-400">
                {error}
              </div>
            )}

            {/* Add Tags Modal */}
            {activeModal === 'add_tags' && (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">
                  Enter comma-separated tags to add to all {count} selected assets:
                </p>
                <input
                  type="text"
                  placeholder="marketing, hero, 2026..."
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleApplyAddTags();
                    }
                  }}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-blue-500"
                  autoFocus
                />
              </div>
            )}

            {/* Remove Common Tags Modal (No text box, just chips with X) */}
            {activeModal === 'remove_tags' && (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">
                  Click the <span className="font-semibold text-rose-400">✕</span> button on any shared tag to remove it from all {count} selected assets:
                </p>
                {commonTags.length > 0 ? (
                  <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    {commonTags.map((tagName) => (
                      <span
                        key={tagName}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800/90 text-slate-200 border border-slate-700/80 hover:border-slate-600 transition-all shadow-xs group"
                      >
                        <TagIcon className="w-3 h-3 text-amber-400/80" />
                        <span>#{tagName}</span>
                        <button
                          onClick={() => handleRemoveSingleCommonTag(tagName)}
                          disabled={loading}
                          className="p-1 -mr-1 rounded-lg text-slate-400 hover:text-white hover:bg-rose-600/80 transition-all cursor-pointer disabled:opacity-50"
                          title={`Remove #${tagName} from all selected assets`}
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center space-y-1.5">
                    <p className="text-xs font-semibold text-slate-300">No Common Tags</p>
                    <p className="text-[11px] text-slate-500">
                      The selected assets do not have any shared tags in common.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Move Modal */}
            {activeModal === 'move' && (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">
                  Select or enter the destination folder on your disk where the selected files will be relocated:
                </p>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    placeholder="D:\Projects\FinalAssets..."
                    value={moveDestDir}
                    onChange={(e) => setMoveDestDir(e.target.value)}
                    className="flex-1 px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-blue-500 font-mono"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={async () => {
                      const selected = await pickFolderDialog();
                      if (selected) setMoveDestDir(selected);
                    }}
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-750 hover:border-slate-600 text-slate-200 rounded-xl text-xs font-semibold flex items-center space-x-1.5 shrink-0 transition-colors border border-slate-700 shadow-xs cursor-pointer"
                    title="Browse Folder..."
                  >
                    <FolderOpen className="w-3.5 h-3.5 text-blue-400" />
                    <span>Browse...</span>
                  </button>
                </div>
              </div>
            )}

            {/* Trash Confirmation Modal */}
            {activeModal === 'trash' && (
              <div className="space-y-3">
                <p className="text-xs text-slate-300">
                  Are you sure you want to move <span className="font-bold text-rose-400">{count} selected file{count > 1 ? 's' : ''}</span> to the Windows Recycle Bin?
                </p>
                <p className="text-[11px] text-slate-500">
                  Files can be restored later from your Windows Recycle Bin if needed.
                </p>
              </div>
            )}

            <div className="flex justify-end space-x-2 pt-2">
              {activeModal === 'remove_tags' ? (
                <>
                  {commonTags.length > 0 && (
                    <button
                      onClick={handleRemoveAllCommonTags}
                      disabled={loading}
                      className="px-3.5 py-2 text-xs font-semibold text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded-xl transition-colors cursor-pointer disabled:opacity-50 mr-auto"
                    >
                      {loading ? 'Removing...' : 'Remove All Common Tags'}
                    </button>
                  )}
                  <button
                    onClick={() => setActiveModal(null)}
                    disabled={loading}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-xl transition-colors cursor-pointer"
                  >
                    Done
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setActiveModal(null)}
                    disabled={loading}
                    className="px-4 py-2 text-xs text-slate-400 hover:text-white rounded-xl cursor-pointer"
                  >
                    Cancel
                  </button>
                  {activeModal === 'trash' ? (
                    <button
                      onClick={handleBatchTrash}
                      disabled={loading}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>{loading ? 'Moving...' : 'Yes, Send to Recycle Bin'}</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        if (activeModal === 'move') handleBatchMove();
                        else if (activeModal === 'add_tags') handleApplyAddTags();
                      }}
                      disabled={loading || (activeModal === 'add_tags' && !tagInput.trim()) || (activeModal === 'move' && !moveDestDir.trim())}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors cursor-pointer"
                    >
                      {loading ? 'Applying...' : 'Apply'}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

