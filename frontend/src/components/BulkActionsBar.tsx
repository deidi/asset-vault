import React, { useState } from 'react';
import {
  Trash2,
  FolderInput,
  X,
  Plus,
  Minus
} from 'lucide-react';
import { batchUpdateTags, trashToRecycleBin, batchMove } from '../api';

interface BulkActionsBarProps {
  selectedAssetIds: string[];
  onClearSelection: () => void;
  onRefreshLibrary: () => void;
}

export const BulkActionsBar: React.FC<BulkActionsBarProps> = ({
  selectedAssetIds,
  onClearSelection,
  onRefreshLibrary,
}) => {
  const [activeModal, setActiveModal] = useState<'add_tags' | 'remove_tags' | 'move' | null>(null);
  const [tagInput, setTagInput] = useState('');
  const [moveDestDir, setMoveDestDir] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (selectedAssetIds.length === 0) return null;

  const count = selectedAssetIds.length;

  const handleApplyTags = async (operation: 'add' | 'remove') => {
    const tags = tagInput
      .split(',')
      .map((t) => t.trim().replace(/^#/, ''))
      .filter(Boolean);

    if (tags.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      await batchUpdateTags(selectedAssetIds, operation, tags);
      setActiveModal(null);
      setTagInput('');
      onRefreshLibrary();
    } catch (err: any) {
      setError(err.message || 'Tag update failed');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchMove = async () => {
    if (!moveDestDir.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await batchMove(selectedAssetIds, moveDestDir.trim());
      setActiveModal(null);
      setMoveDestDir('');
      onClearSelection();
      onRefreshLibrary();
    } catch (err: any) {
      setError(err.message || 'Move failed');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchTrash = async () => {
    if (
      window.confirm(
        `Are you sure you want to send ${count} selected item${count > 1 ? 's' : ''} to the Windows Recycle Bin?`
      )
    ) {
      setLoading(true);
      try {
        await trashToRecycleBin(selectedAssetIds);
        onClearSelection();
        onRefreshLibrary();
      } catch (err: any) {
        alert(err.message || 'Failed to trash items');
      } finally {
        setLoading(false);
      }
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
              onClick={() => setActiveModal('add_tags')}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            >
              <Plus className="w-3.5 h-3.5 text-blue-400" />
              <span>Add Tags</span>
            </button>

            <button
              onClick={() => setActiveModal('remove_tags')}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            >
              <Minus className="w-3.5 h-3.5 text-amber-400" />
              <span>Remove Tags</span>
            </button>

            <button
              onClick={() => setActiveModal('move')}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            >
              <FolderInput className="w-3.5 h-3.5 text-emerald-400" />
              <span>Move Files</span>
            </button>

            <button
              onClick={handleBatchTrash}
              className="px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-medium flex items-center space-x-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Recycle Bin</span>
            </button>
          </div>

          <button
            onClick={onClearSelection}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors ml-2"
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
              <h4 className="text-sm font-bold text-slate-100">
                {activeModal === 'add_tags' && `Add Tags to ${count} Assets`}
                {activeModal === 'remove_tags' && `Remove Tags from ${count} Assets`}
                {activeModal === 'move' && `Move ${count} Assets to Another Folder`}
              </h4>
              <button onClick={() => setActiveModal(null)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {error && <div className="text-xs text-red-400 bg-red-500/10 p-2.5 rounded-lg">{error}</div>}

            {activeModal === 'move' ? (
              <div className="space-y-2">
                <label className="block text-xs text-slate-300">Destination Directory Path</label>
                <input
                  type="text"
                  placeholder="e.g. D:\Media\Archive"
                  value={moveDestDir}
                  onChange={(e) => setMoveDestDir(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>
            ) : (
              <div className="space-y-2">
                <label className="block text-xs text-slate-300">Tags (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g. Marketing, 2026, Featured"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>
            )}

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (activeModal === 'move') handleBatchMove();
                  else if (activeModal === 'add_tags') handleApplyTags('add');
                  else if (activeModal === 'remove_tags') handleApplyTags('remove');
                }}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold"
              >
                {loading ? 'Applying...' : 'Apply'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
