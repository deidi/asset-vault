import React, { useState } from 'react';
import { FolderPlus, X, Check, AlertCircle, FolderSearch } from 'lucide-react';
import { createFolder, pickFolderDialog, scanFolder } from '../api';
import type { LibraryFolder } from '../types';

interface AddFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFolderAdded: (folder: LibraryFolder) => void;
}

export const AddFolderModal: React.FC<AddFolderModalProps> = ({ isOpen, onClose, onFolderAdded }) => {
  const [folderPath, setFolderPath] = useState('');
  const [folderName, setFolderName] = useState('');
  const [isRecursive, setIsRecursive] = useState(true);
  const [autoTagFolder, setAutoTagFolder] = useState(true);
  const [customTagInput, setCustomTagInput] = useState('');
  const [customTags, setCustomTags] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPicking, setIsPicking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleBrowseFolder = async () => {
    setIsPicking(true);
    try {
      const selected = await pickFolderDialog();
      if (selected) {
        setFolderPath(selected);
        if (!folderName) {
          const parts = selected.split(/[\\/]/).filter(Boolean);
          if (parts.length > 0) setFolderName(parts[parts.length - 1]);
        }
      }
    } finally {
      setIsPicking(false);
    }
  };

  const handleAddCustomTag = () => {
    const trimmed = customTagInput.trim().replace(/^#/, '');
    if (trimmed && !customTags.includes(trimmed)) {
      setCustomTags([...customTags, trimmed]);
      setCustomTagInput('');
    }
  };

  const handleRemoveCustomTag = (tagToRemove: string) => {
    setCustomTags(customTags.filter(t => t !== tagToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderPath.trim()) {
      setError('Please provide a valid folder path on your computer.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const created = await createFolder({
        path: folderPath.trim(),
        name: folderName.trim() || undefined,
        is_recursive: isRecursive,
        auto_tag_folder: autoTagFolder,
        custom_tags: customTags,
      });
      // Automatically scan newly created folder so all files and asset counts appear immediately
      try {
        await scanFolder(created.id);
      } catch (scanErr) {
        console.warn('Initial folder scan encountered an issue:', scanErr);
      }
      onFolderAdded(created);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to add library folder');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
              <FolderPlus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-100">Add Library Folder</h3>
              <p className="text-xs text-slate-400">Media stays in-place on your drive with live sync</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center space-x-3 text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Folder Directory Path <span className="text-red-400">*</span>
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="e.g. D:\DesignAssets or C:\Users\Media\Wallpapers"
                value={folderPath}
                onChange={(e) => {
                  setFolderPath(e.target.value);
                  if (!folderName) {
                    const parts = e.target.value.split(/[\\/]/).filter(Boolean);
                    if (parts.length > 0) setFolderName(parts[parts.length - 1]);
                  }
                }}
                className="flex-1 px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                required
              />
              <button
                type="button"
                onClick={handleBrowseFolder}
                disabled={isPicking}
                className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors flex items-center space-x-1.5 shrink-0"
                title="Browse folder on your computer"
              >
                <FolderSearch className="w-4 h-4 text-blue-400" />
                <span>{isPicking ? 'Browsing...' : 'Browse...'}</span>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Display Name (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Design Assets"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-3 pt-2">
            <label className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 cursor-pointer hover:bg-slate-900 transition-colors">
              <div className="pr-4">
                <span className="text-sm font-medium text-slate-200 block">Recursive Subfolder Scan</span>
                <span className="text-xs text-slate-400 block">Scan all nested subdirectories inside this folder</span>
              </div>
              <input
                type="checkbox"
                checked={isRecursive}
                onChange={(e) => setIsRecursive(e.target.checked)}
                className="w-4 h-4 rounded text-blue-600 bg-slate-950 border-slate-700 focus:ring-blue-500"
              />
            </label>

            <label className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 cursor-pointer hover:bg-slate-900 transition-colors">
              <div className="pr-4">
                <span className="text-sm font-medium text-slate-200 block">Auto-Tag Folder Name</span>
                <span className="text-xs text-slate-400 block">Automatically tag items with their enclosing folder name</span>
              </div>
              <input
                type="checkbox"
                checked={autoTagFolder}
                onChange={(e) => setAutoTagFolder(e.target.checked)}
                className="w-4 h-4 rounded text-blue-600 bg-slate-950 border-slate-700 focus:ring-blue-500"
              />
            </label>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Custom Folder Auto-Tags
            </label>
            <div className="flex space-x-2 mb-2">
              <input
                type="text"
                placeholder="e.g. ProjectAlpha, Marketing"
                value={customTagInput}
                onChange={(e) => setCustomTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddCustomTag();
                  }
                }}
                className="flex-1 px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-sm focus:outline-none focus:border-blue-500"
              />
              <button
                type="button"
                onClick={handleAddCustomTag}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-colors"
              >
                Add
              </button>
            </div>

            {customTags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {customTags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30"
                  >
                    #{tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveCustomTag(tag)}
                      className="ml-1.5 text-blue-400/70 hover:text-blue-200"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm rounded-xl shadow-lg shadow-blue-500/25 transition-all disabled:opacity-50 flex items-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Connecting & Scanning...</span>
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>Add & Index Folder</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
