import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Maximize2,
  FolderOpen,
  CheckCircle2,
  Circle,
  FileText,
  Image as ImageIcon,
  Film,
  Music,
  Package
} from 'lucide-react';
import type { Asset } from '../types';
import { getThumbnailUrl, revealInExplorer } from '../api';

interface MediaGridProps {
  assets: Asset[];
  selectedAssetIds: string[];
  activeAssetId: string | null;
  onSelectAsset: (asset: Asset, isMulti: boolean, isRange: boolean) => void;
  onOpenFullscreenPreview: (asset: Asset) => void;
  gridSize: 'small' | 'medium' | 'large';
}

export const MediaGrid: React.FC<MediaGridProps> = ({
  assets,
  selectedAssetIds,
  activeAssetId,
  onSelectAsset,
  onOpenFullscreenPreview,
  gridSize,
}) => {
  // O(1) Fast Set lookup for selection checks across large catalogs (9,000+ assets)
  const selectedSet = useMemo(() => new Set(selectedAssetIds), [selectedAssetIds]);

  // Progressive chunked rendering: load first 150 items instantly, then append smoothly as user scrolls
  const [displayLimit, setDisplayLimit] = useState(150);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setDisplayLimit(150);
  }, [assets]);

  useEffect(() => {
    if (displayLimit >= assets.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setDisplayLimit((prev) => Math.min(prev + 150, assets.length));
        }
      },
      { rootMargin: '400px' }
    );

    const currentSentinel = sentinelRef.current;
    if (currentSentinel) observer.observe(currentSentinel);
    return () => {
      if (currentSentinel) observer.unobserve(currentSentinel);
    };
  }, [displayLimit, assets.length]);

  const visibleAssets = useMemo(() => assets.slice(0, displayLimit), [assets, displayLimit]);

  const getGridColsClass = () => {
    switch (gridSize) {
      case 'small':
        return 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3';
      case 'large':
        return 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6';
      case 'medium':
      default:
        return 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4';
    }
  };

  const getFormatIcon = (asset: Asset) => {
    const mime = (asset.mime_type || '').toLowerCase();
    const cat = asset.category || '';
    if (cat === 'image' || mime.startsWith('image/')) return <ImageIcon className="w-3.5 h-3.5 text-blue-400" />;
    if (cat === 'video' || mime.startsWith('video/')) return <Film className="w-3.5 h-3.5 text-indigo-400" />;
    if (cat === 'audio' || mime.startsWith('audio/')) return <Music className="w-3.5 h-3.5 text-emerald-400" />;
    if (cat === 'document' || mime.includes('pdf')) return <FileText className="w-3.5 h-3.5 text-rose-400" />;
    return <Package className="w-3.5 h-3.5 text-amber-400" />;
  };

  const renderPlaceholderIcon = (asset: Asset) => {
    const mime = (asset.mime_type || '').toLowerCase();
    const cat = asset.category || '';
    if (cat === 'image' || mime.startsWith('image/')) return <ImageIcon className="w-10 h-10 text-slate-800" />;
    if (cat === 'video' || mime.startsWith('video/')) return <Film className="w-10 h-10 text-slate-800" />;
    if (cat === 'audio' || mime.startsWith('audio/')) return <Music className="w-10 h-10 text-slate-800" />;
    if (cat === 'document' || mime.includes('pdf')) return <FileText className="w-10 h-10 text-slate-800" />;
    return <Package className="w-10 h-10 text-slate-800" />;
  };

  return (
    <div className={`grid ${getGridColsClass()} p-6`}>
      {visibleAssets.map((asset) => {
        const isSelected = selectedSet.has(asset.id);
        const isActive = activeAssetId === asset.id;
        const thumbnailUrl = getThumbnailUrl(asset.id, 350, 350);

        return (
          <div
            key={asset.id}
            onClick={(e) => {
              const isMulti = e.ctrlKey || e.metaKey;
              const isRange = e.shiftKey;
              onSelectAsset(asset, isMulti, isRange);
            }}
            onDoubleClick={() => onOpenFullscreenPreview(asset)}
            className={`group relative flex flex-col rounded-2xl overflow-hidden cursor-pointer select-none transition-all duration-200 border ${
              isActive
                ? 'bg-slate-800/90 border-blue-500 shadow-lg shadow-blue-500/20 ring-1 ring-blue-500 scale-[1.01]'
                : isSelected
                ? 'bg-slate-800/60 border-blue-500/60 shadow-md ring-1 ring-blue-500/30'
                : 'bg-slate-900/60 hover:bg-slate-800/50 border-slate-800/80 hover:border-slate-700'
            }`}
          >
            {/* Thumbnail Canvas */}
            <div className="relative aspect-square w-full bg-slate-950/80 overflow-hidden flex items-center justify-center">
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                {renderPlaceholderIcon(asset)}
              </div>
              <img
                src={thumbnailUrl}
                alt={asset.name}
                loading="lazy"
                className="relative z-1 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />

              {/* Selection Checkbox Pill */}
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectAsset(asset, true, false);
                }}
                className={`absolute top-2.5 left-2.5 p-1 rounded-lg backdrop-blur-xs transition-opacity ${
                  isSelected
                    ? 'opacity-100 bg-blue-600 text-white'
                    : 'opacity-0 group-hover:opacity-100 bg-black/40 text-slate-300 hover:text-white'
                }`}
              >
                {isSelected ? <CheckCircle2 className="w-4 h-4" /> : <Circle className="w-4 h-4" />}
              </div>

              {/* Quick Actions Shortcuts (Hover) */}
              <div className="absolute top-2.5 right-2.5 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    revealInExplorer(asset.id);
                  }}
                  className="p-1.5 rounded-lg bg-black/60 hover:bg-blue-600 text-slate-200 backdrop-blur-xs transition-colors shadow-xs"
                  title="Show in Explorer"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenFullscreenPreview(asset);
                  }}
                  className="p-1.5 rounded-lg bg-black/60 hover:bg-blue-600 text-slate-200 backdrop-blur-xs transition-colors shadow-xs"
                  title="Full-Screen Preview"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Asset Metadata Footer */}
            <div className="p-3 space-y-1 bg-slate-900/40 border-t border-slate-800/60">
              <div className="flex items-center space-x-1.5">
                {getFormatIcon(asset)}
                <h4 className="text-xs font-semibold text-slate-200 truncate flex-1" title={asset.name}>
                  {asset.name}
                </h4>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>{(asset.size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                <span>{(asset.tags || []).length > 0 ? `#${asset.tags[0].name.replace(/^#/, '')}` : ''}</span>
              </div>
            </div>
          </div>
        );
      })}

      {/* Progressive loading sentinel */}
      {displayLimit < assets.length && (
        <div ref={sentinelRef} className="col-span-full h-12 flex items-center justify-center text-xs text-slate-500 font-medium">
          Loading more assets...
        </div>
      )}
    </div>
  );
};
