import React, { useState, useEffect, useMemo } from 'react';
import {
  SlidersHorizontal,
  X,
  Plus,
  RotateCcw,
  Check,
  AlertCircle,
  ImageIcon,
  Film,
  Music,
  FileText,
  Search,
  CheckCircle2
} from 'lucide-react';
import { getFileTypeSettings, updateFileTypeSettings, resetFileTypeSettings } from '../api';
import type { CategoryExtensionsMap, FileTypeSettingsResponse } from '../types';

interface FileTypeSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

type CategoryKey = 'image' | 'video' | 'audio' | 'document';

interface CategoryConfig {
  key: CategoryKey;
  label: string;
  icon: React.ElementType;
  accentColor: string;
  bgLight: string;
  borderLight: string;
  badgeColor: string;
  description: string;
}

const CATEGORIES: CategoryConfig[] = [
  {
    key: 'image',
    label: 'Images',
    icon: ImageIcon,
    accentColor: 'text-blue-400',
    bgLight: 'bg-blue-500/10',
    borderLight: 'border-blue-500/30',
    badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    description: 'Visual photos, vectors, icons, and textures',
  },
  {
    key: 'video',
    label: 'Videos',
    icon: Film,
    accentColor: 'text-indigo-400',
    bgLight: 'bg-indigo-500/10',
    borderLight: 'border-indigo-500/30',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    description: 'Motion clips, movies, animations, and captures',
  },
  {
    key: 'audio',
    label: 'Audio',
    icon: Music,
    accentColor: 'text-emerald-400',
    bgLight: 'bg-emerald-500/10',
    borderLight: 'border-emerald-500/30',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    description: 'Soundtracks, effects, voice recordings, and samples',
  },
  {
    key: 'document',
    label: 'Documents',
    icon: FileText,
    accentColor: 'text-rose-400',
    bgLight: 'bg-rose-500/10',
    borderLight: 'border-rose-500/30',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    description: 'PDFs, spreadsheets, text files, presentations, and docs',
  },
];

export const FileTypeSettingsModal: React.FC<FileTypeSettingsModalProps> = ({
  isOpen,
  onClose,
  onSaved,
}) => {
  const [activeTab, setActiveTab] = useState<CategoryKey>('image');
  const [extensions, setExtensions] = useState<CategoryExtensionsMap>({
    image: [],
    video: [],
    audio: [],
    document: [],
  });
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [newExtInput, setNewExtInput] = useState('');
  const [filterQuery, setFilterQuery] = useState('');
  const [recategorize, setRecategorize] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [bannerMessage, setBannerMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
      setNewExtInput('');
      setFilterQuery('');
      setBannerMessage(null);
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setIsLoading(true);
    try {
      const data: FileTypeSettingsResponse = await getFileTypeSettings();
      setExtensions({
        image: [...(data.categories.image || [])],
        video: [...(data.categories.video || [])],
        audio: [...(data.categories.audio || [])],
        document: [...(data.categories.document || [])],
      });
      setCounts(data.counts || {});
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err.message || 'Failed to load settings.' });
    } finally {
      setIsLoading(false);
    }
  };

  const currentCategoryConfig = useMemo(
    () => CATEGORIES.find((c) => c.key === activeTab) || CATEGORIES[0],
    [activeTab]
  );

  const currentCategoryExtensions = useMemo(
    () => extensions[activeTab] || [],
    [extensions, activeTab]
  );

  const filteredExtensions = useMemo(() => {
    if (!filterQuery.trim()) return currentCategoryExtensions;
    const q = filterQuery.toLowerCase().trim();
    return currentCategoryExtensions.filter((ext) => ext.toLowerCase().includes(q));
  }, [currentCategoryExtensions, filterQuery]);

  const handleAddExtensions = () => {
    if (!newExtInput.trim()) return;

    // Support comma or space separated inputs (e.g. "heic, raw, .cr2")
    const rawTokens = newExtInput
      .split(/[,;\s]+/)
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);

    if (rawTokens.length === 0) return;

    const normalizedTokens = rawTokens.map((t) => (t.startsWith('.') ? t : `.${t}`));

    setExtensions((prev) => {
      const next: CategoryExtensionsMap = {
        image: [...prev.image],
        video: [...prev.video],
        audio: [...prev.audio],
        document: [...prev.document],
      };

      let transferredCount = 0;

      normalizedTokens.forEach((token) => {
        // Remove token from any other category if present (auto-transfer)
        CATEGORIES.forEach((cat) => {
          if (cat.key !== activeTab) {
            const idx = next[cat.key].indexOf(token);
            if (idx !== -1) {
              next[cat.key].splice(idx, 1);
              transferredCount++;
            }
          }
        });

        // Add to active category if not already present
        if (!next[activeTab].includes(token)) {
          next[activeTab].push(token);
        }
      });

      next[activeTab].sort();

      if (transferredCount > 0) {
        setBannerMessage({
          type: 'info',
          text: `Moved ${transferredCount} extension(s) from other categories to ${currentCategoryConfig.label}.`,
        });
      } else {
        setBannerMessage(null);
      }

      return next;
    });

    setNewExtInput('');
  };

  const handleRemoveExtension = (extToRemove: string) => {
    setExtensions((prev) => ({
      ...prev,
      [activeTab]: prev[activeTab].filter((e) => e !== extToRemove),
    }));
    setBannerMessage(null);
  };

  const handleResetToDefaults = async () => {
    if (!window.confirm('Reset all category file extensions to their default configurations?')) {
      return;
    }

    setIsSaving(true);
    setBannerMessage(null);
    try {
      const res = await resetFileTypeSettings(recategorize);
      setExtensions({
        image: [...(res.categories.image || [])],
        video: [...(res.categories.video || [])],
        audio: [...(res.categories.audio || [])],
        document: [...(res.categories.document || [])],
      });
      setBannerMessage({
        type: 'success',
        text: `Reset to defaults successfully! ${res.recategorized_count} asset(s) re-classified.`,
      });
      onSaved();
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err.message || 'Failed to reset defaults.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setBannerMessage(null);
    try {
      const res = await updateFileTypeSettings(extensions, recategorize);
      setBannerMessage({
        type: 'success',
        text: `Saved changes successfully! ${res.recategorized_count} asset(s) re-classified.`,
      });
      onSaved();
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err.message || 'Failed to save settings.' });
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <SlidersHorizontal className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">Category File Types & Filters</h2>
              <p className="text-xs text-slate-400">
                Configure which extensions map to each category. Unlisted files appear in Other Files.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Banner Message */}
        {bannerMessage && (
          <div
            className={`px-6 py-2.5 text-xs flex items-center space-x-2 border-b transition-all ${
              bannerMessage.type === 'success'
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/40'
                : bannerMessage.type === 'error'
                ? 'bg-rose-950/40 text-rose-300 border-rose-800/40'
                : 'bg-blue-950/40 text-blue-300 border-blue-800/40'
            }`}
          >
            {bannerMessage.type === 'success' && <CheckCircle2 className="w-4 h-4 shrink-0" />}
            {bannerMessage.type === 'error' && <AlertCircle className="w-4 h-4 shrink-0" />}
            {bannerMessage.type === 'info' && <SlidersHorizontal className="w-4 h-4 shrink-0" />}
            <span>{bannerMessage.text}</span>
          </div>
        )}

        {/* Category Tabs */}
        <div className="grid grid-cols-4 border-b border-slate-800/80 bg-slate-950/20">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeTab === cat.key;
            const extCount = (extensions[cat.key] || []).length;
            const assetCount = counts[cat.key] || 0;

            return (
              <button
                key={cat.key}
                onClick={() => {
                  setActiveTab(cat.key);
                  setBannerMessage(null);
                  setFilterQuery('');
                }}
                className={`py-3 px-2 flex flex-col items-center justify-center space-y-1 transition-all border-b-2 cursor-pointer ${
                  isActive
                    ? `border-blue-500 bg-slate-800/40 ${cat.accentColor}`
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/20'
                }`}
              >
                <div className="flex items-center space-x-1.5">
                  <Icon className="w-4 h-4" />
                  <span className="text-xs font-medium">{cat.label}</span>
                </div>
                <div className="flex items-center space-x-1 text-[10px] text-slate-400">
                  <span>{extCount} ext</span>
                  <span>•</span>
                  <span>{assetCount} assets</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Tab Body */}
        <div className="p-6 flex-1 overflow-y-auto space-y-5">
          {/* Active Category Description & Quick Add Form */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
                  <span>{currentCategoryConfig.label} File Types</span>
                  <span className="text-xs font-normal text-slate-400">
                    ({currentCategoryExtensions.length} assigned)
                  </span>
                </h3>
                <p className="text-xs text-slate-400">{currentCategoryConfig.description}</p>
              </div>
            </div>

            {/* Input form */}
            <div className="flex items-center space-x-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={newExtInput}
                  onChange={(e) => setNewExtInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddExtensions();
                    }
                  }}
                  placeholder="Enter extension(s), e.g. .heic, .raw, .cr2"
                  className="w-full bg-slate-950/70 border border-slate-700/70 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-blue-500/80 transition-colors"
                />
              </div>
              <button
                type="button"
                onClick={handleAddExtensions}
                disabled={!newExtInput.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white rounded-xl text-xs font-medium transition-colors flex items-center space-x-1 cursor-pointer shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-400">
              Tip: You can paste comma-separated extensions. Missing dots (<code className="text-slate-400">.</code>) are automatically prefixed.
            </p>
          </div>

          {/* Extension Chips Filter & List */}
          <div className="space-y-2.5 pt-2 border-t border-slate-800/60">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-slate-300">Registered Extensions</span>
              {currentCategoryExtensions.length > 8 && (
                <div className="relative w-48">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={filterQuery}
                    onChange={(e) => setFilterQuery(e.target.value)}
                    placeholder="Search extensions..."
                    className="w-full bg-slate-950/50 border border-slate-800 rounded-lg pl-8 pr-2.5 py-1 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-blue-500/60"
                  />
                </div>
              )}
            </div>

            {/* Chips Container */}
            <div className="bg-slate-950/40 border border-slate-800/70 rounded-xl p-3.5 min-h-[140px] max-h-[220px] overflow-y-auto flex flex-wrap gap-1.5 items-start content-start">
              {filteredExtensions.length === 0 ? (
                <div className="w-full h-28 flex flex-col items-center justify-center text-slate-400 space-y-1">
                  <AlertCircle className="w-5 h-5 text-slate-400" />
                  <span className="text-xs">
                    {filterQuery ? `No extensions matching "${filterQuery}"` : 'No extensions configured.'}
                  </span>
                </div>
              ) : (
                filteredExtensions.map((ext) => (
                  <span
                    key={ext}
                    className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-mono border transition-all ${currentCategoryConfig.badgeColor}`}
                  >
                    <span>{ext}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveExtension(ext)}
                      className="hover:text-rose-400 transition-colors cursor-pointer"
                      title={`Remove ${ext}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800/80 bg-slate-950/50 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={handleResetToDefaults}
            disabled={isLoading || isSaving}
            className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-800/60 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>

          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={recategorize}
                onChange={(e) => setRecategorize(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
              />
              <span>Re-classify library assets</span>
            </label>

            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl transition-colors cursor-pointer"
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || isLoading}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium rounded-xl shadow-xs shadow-blue-500/20 transition-all flex items-center space-x-1.5 cursor-pointer"
            >
              {isSaving ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Save & Apply</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
