import React from 'react';
import {
  Maximize2,
  FolderOpen,
  CheckCircle2,
  Circle,
  FileText,
  Image as ImageIcon,
  Film,
  Music,
  File
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

  const getFormatIcon = (mime: string) => {
    if (mime.startsWith('image/')) return <ImageIcon className="w-3.5 h-3.5 text-blue-400" />;
    if (mime.startsWith('video/')) return <Film className="w-3.5 h-3.5 text-indigo-400" />;
    if (mime.startsWith('audio/')) return <Music className="w-3.5 h-3.5 text-emerald-400" />;
    if (mime.includes('pdf')) return <FileText className="w-3.5 h-3.5 text-rose-400" />;
    return <File className="w-3.5 h-3.5 text-slate-400" />;
  };

  return (
    <div className={`grid ${getGridColsClass()} p-6`}>
      {assets.map((asset) => {
        const isSelected = selectedAssetIds.includes(asset.id);
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
              <img
                src={thumbnailUrl}
                alt={asset.name}
                loading="lazy"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
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
                {getFormatIcon(asset.mime_type)}
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
    </div>
  );
};
