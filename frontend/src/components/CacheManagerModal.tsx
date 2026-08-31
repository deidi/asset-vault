import React, { useState, useEffect } from 'react';
import { RefreshCw, Trash2, Database, AlertTriangle, CheckCircle, X, HardDrive } from 'lucide-react';
import { getCacheStats, clearCache, rescanLibraryAndFixCache } from '../api';
import type { CacheStats } from '../types';

interface CacheManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefreshLibrary: () => void;
}

export const CacheManagerModal: React.FC<CacheManagerModalProps> = ({ isOpen, onClose, onRefreshLibrary }) => {
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadStats = async () => {
    try {
      const data = await getCacheStats();
      setStats(data);
    } catch {
      // ignore error
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadStats();
      setActionMessage(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleClearCache = async () => {
    setLoading(true);
    setActionMessage(null);
    try {
      const res = await clearCache();
      setActionMessage({
        type: 'success',
        text: `Flushed ${res.cleared_count} cached thumbnails (${res.freed_mb} MB freed).`,
      });
      await loadStats();
      onRefreshLibrary();
    } catch (e: any) {
      setActionMessage({ type: 'error', text: e.message || 'Failed to clear cache' });
    } finally {
      setLoading(false);
    }
  };

  const handleFullRescan = async () => {
    setLoading(true);
    setActionMessage(null);
    try {
      const res = await rescanLibraryAndFixCache();
      setActionMessage({
        type: 'success',
        text: `Rescan complete! Scanned ${res.total_scanned} files (${res.newly_indexed} new, ${res.purged_missing_files} purged).`,
      });
      await loadStats();
      onRefreshLibrary();
    } catch (e: any) {
      setActionMessage({ type: 'error', text: e.message || 'Failed to perform full rescan' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-100">Cache & Library Diagnostics</h3>
              <p className="text-xs text-slate-400">Manage WebP preview cache and fix indexing discrepancies</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {actionMessage && (
            <div
              className={`p-3.5 rounded-xl border flex items-center space-x-3 text-sm ${
                actionMessage.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'
              }`}
            >
              {actionMessage.type === 'success' ? (
                <CheckCircle className="w-5 h-5 shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 shrink-0" />
              )}
              <span>{actionMessage.text}</span>
            </div>
          )}

          {/* Cache Stats Card */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/90 space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center space-x-1.5">
                <HardDrive className="w-4 h-4 text-slate-500" />
                <span>Thumbnail Cache Disk Usage</span>
              </span>
              <span className="font-semibold text-slate-200">{stats ? `${stats.total_size_mb} MB` : 'Loading...'}</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Cached WebP Files</span>
              <span className="font-semibold text-slate-200">{stats ? stats.total_cached_thumbnails : 0} items</span>
            </div>
          </div>

          <div className="space-y-4">
            {/* Clear Cache Option */}
            <div className="flex items-start justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="pr-4 space-y-1">
                <h4 className="text-sm font-semibold text-slate-200">Delete Thumbnail Cache</h4>
                <p className="text-xs text-slate-400">
                  Flushes all generated WebP thumbnails from disk. Thumbnails will re-generate dynamically on demand.
                </p>
              </div>
              <button
                type="button"
                disabled={loading}
                onClick={handleClearCache}
                className="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-semibold shrink-0 transition-colors flex items-center space-x-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Cache</span>
              </button>
            </div>

            {/* Rescan & Fix Option */}
            <div className="flex items-start justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="pr-4 space-y-1">
                <h4 className="text-sm font-semibold text-slate-200">Rescan All & Fix Cache Errors</h4>
                <p className="text-xs text-slate-400">
                  Clears the cache, removes database entries for deleted or moved files, and re-indexes all active library folders.
                </p>
              </div>
              <button
                type="button"
                disabled={loading}
                onClick={handleFullRescan}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shrink-0 shadow-lg shadow-blue-500/20 transition-all flex items-center space-x-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Full Rescan</span>
              </button>
            </div>
          </div>

          <div className="flex items-center justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
