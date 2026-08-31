import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCw,
  FolderOpen,
  Download,
  Info,
  Volume2
} from 'lucide-react';
import type { Asset } from '../types';
import { getMediaFileUrl, revealInExplorer } from '../api';

interface PreviewModalProps {
  asset: Asset | null;
  assetsList: Asset[];
  onClose: () => void;
  onSelectAsset: (asset: Asset) => void;
}

export const PreviewModal: React.FC<PreviewModalProps> = ({
  asset,
  assetsList,
  onClose,
  onSelectAsset,
}) => {
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [showInfo, setShowInfo] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const currentIndex = asset ? assetsList.findIndex((a) => a.id === asset.id) : -1;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < assetsList.length - 1;

  // Reset transform state when switching assets
  useEffect(() => {
    setZoom(1);
    setRotation(0);
  }, [asset?.id]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!asset) return;
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft' && hasPrev) {
        onSelectAsset(assetsList[currentIndex - 1]);
      } else if (e.key === 'ArrowRight' && hasNext) {
        onSelectAsset(assetsList[currentIndex + 1]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [asset, currentIndex, hasPrev, hasNext, assetsList, onClose, onSelectAsset]);

  if (!asset) return null;

  const ext = (asset.name.split('.').pop() || '').toLowerCase();
  const mime = (asset.mime_type || '').toLowerCase();
  const isImage = mime.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp', 'ico', 'jfif', 'tiff'].includes(ext);
  const isVideo = mime.startsWith('video/') || ['mp4', 'webm', 'mov', 'mkv', 'avi', 'wmv', 'flv', 'm4v'].includes(ext);
  const isAudio = mime.startsWith('audio/') || ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'].includes(ext);
  const isPdf = mime.includes('pdf') || ext === 'pdf';
  const mediaUrl = getMediaFileUrl(asset.id);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 4));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
  const handleRotate = () => setRotation((r) => (r + 90) % 360);
  const handleReset = () => {
    setZoom(1);
    setRotation(0);
  };

  const handleSpeedChange = (rate: number) => {
    setPlaybackRate(rate);
    if (videoRef.current) videoRef.current.playbackRate = rate;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md animate-in fade-in duration-200">
      {/* Top Toolbar */}
      <div className="absolute top-0 inset-x-0 h-16 px-6 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent z-20 pointer-events-auto">
        <div className="flex items-center space-x-3 text-slate-200">
          <span className="text-sm font-semibold truncate max-w-md">{asset.name}</span>
          <span className="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 font-mono">
            {currentIndex + 1} / {assetsList.length}
          </span>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center space-x-2">
          {isImage && (
            <>
              <button
                onClick={handleZoomIn}
                className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                title="Zoom In (+)"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomOut}
                className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                title="Zoom Out (-)"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={handleRotate}
                className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                title="Rotate 90°"
              >
                <RotateCw className="w-4 h-4" />
              </button>
              <button
                onClick={handleReset}
                className="px-2.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-mono transition-colors"
                title="Reset View"
              >
                {Math.round(zoom * 100)}%
              </button>
            </>
          )}

          {isVideo && (
            <div className="flex items-center space-x-1 bg-slate-800/80 rounded-xl p-1 text-xs">
              {[0.5, 1, 1.5, 2].map((rate) => (
                <button
                  key={rate}
                  onClick={() => handleSpeedChange(rate)}
                  className={`px-2 py-1 rounded-lg transition-colors ${
                    playbackRate === rate ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {rate}x
                </button>
              ))}
            </div>
          )}

          <button
            onClick={() => revealInExplorer(asset.id)}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-blue-600 text-slate-300 hover:text-white transition-colors"
            title="Show in File Explorer"
          >
            <FolderOpen className="w-4 h-4" />
          </button>

          <button
            onClick={() => setShowInfo(!showInfo)}
            className={`p-2 rounded-xl transition-colors ${
              showInfo ? 'bg-blue-600 text-white' : 'bg-slate-800/80 text-slate-300 hover:text-white'
            }`}
            title="Toggle File Info"
          >
            <Info className="w-4 h-4" />
          </button>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-red-600 text-slate-300 hover:text-white transition-colors ml-2"
            title="Close (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Preview Canvas */}
      <div className="relative w-full h-full flex items-center justify-center p-8 overflow-hidden select-none">
        {/* Previous Button */}
        {hasPrev && (
          <button
            onClick={() => onSelectAsset(assetsList[currentIndex - 1])}
            className="absolute left-6 top-1/2 -translate-y-1/2 p-3 rounded-2xl bg-black/60 hover:bg-blue-600 text-slate-300 hover:text-white border border-white/10 backdrop-blur-sm z-30 transition-all shadow-xl"
            title="Previous (Left Arrow)"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}

        {/* Media Render Engine */}
        <div className="max-w-full max-h-full flex items-center justify-center transition-transform duration-200">
          {isImage && (
            <img
              src={mediaUrl}
              alt={asset.name}
              style={{
                transform: `scale(${zoom}) rotate(${rotation}deg)`,
                maxHeight: '82vh',
                maxWidth: '85vw',
                objectFit: 'contain',
              }}
              className="rounded-lg shadow-2xl transition-transform ease-out duration-150"
            />
          )}

          {isVideo && (
            <video
              ref={videoRef}
              src={mediaUrl}
              controls
              autoPlay
              className="max-h-[82vh] max-w-[85vw] rounded-xl shadow-2xl bg-black border border-slate-800"
            />
          )}

          {isAudio && (
            <div className="p-8 rounded-3xl bg-slate-900/90 border border-slate-800 backdrop-blur-xl shadow-2xl w-full max-w-md flex flex-col items-center space-y-6">
              <div className="w-28 h-28 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <Volume2 className="w-12 h-12 text-white" />
              </div>
              <div className="text-center">
                <h4 className="text-lg font-bold text-slate-100">{asset.name}</h4>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  {(asset.size_bytes / (1024 * 1024)).toFixed(2)} MB • {asset.mime_type}
                </p>
              </div>
              <audio ref={audioRef} src={mediaUrl} controls autoPlay className="w-full" />
            </div>
          )}

          {isPdf && (
            <iframe
              src={mediaUrl}
              title={asset.name}
              className="w-[85vw] h-[82vh] rounded-2xl shadow-2xl bg-white border border-slate-800"
            />
          )}

          {!isImage && !isVideo && !isAudio && !isPdf && (
            <div className="p-10 rounded-3xl bg-slate-900 border border-slate-800 text-center space-y-4">
              <div className="w-20 h-20 mx-auto rounded-2xl bg-slate-800 flex items-center justify-center text-slate-400">
                <Download className="w-8 h-8" />
              </div>
              <div>
                <h4 className="text-lg font-bold text-slate-200">{asset.name}</h4>
                <p className="text-xs text-slate-400 mt-1">Preview not directly supported for this format.</p>
              </div>
              <button
                onClick={() => revealInExplorer(asset.id)}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center space-x-2 mx-auto"
              >
                <FolderOpen className="w-4 h-4" />
                <span>Show in Windows Explorer</span>
              </button>
            </div>
          )}
        </div>

        {/* Next Button */}
        {hasNext && (
          <button
            onClick={() => onSelectAsset(assetsList[currentIndex + 1])}
            className="absolute right-6 top-1/2 -translate-y-1/2 p-3 rounded-2xl bg-black/60 hover:bg-blue-600 text-slate-300 hover:text-white border border-white/10 backdrop-blur-sm z-30 transition-all shadow-xl"
            title="Next (Right Arrow)"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        )}

        {/* Metadata Sidebar Overlay */}
        {showInfo && (
          <div className="absolute right-6 top-20 bottom-6 w-80 bg-slate-900/95 border border-slate-800 rounded-2xl p-5 backdrop-blur-xl shadow-2xl z-40 overflow-y-auto space-y-4 text-xs animate-in slide-in-from-right-10 duration-200">
            <h4 className="text-sm font-bold text-slate-200 border-b border-slate-800 pb-2">Asset Details</h4>
            
            <div className="space-y-2.5">
              <div>
                <span className="text-slate-500 block font-medium">Filename</span>
                <span className="text-slate-200 break-all font-semibold">{asset.name}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-medium">File Size</span>
                <span className="text-slate-200 font-mono">
                  {(asset.size_bytes / (1024 * 1024)).toFixed(2)} MB ({asset.size_bytes.toLocaleString()} bytes)
                </span>
              </div>
              <div>
                <span className="text-slate-500 block font-medium">Content Type</span>
                <span className="text-slate-200 font-mono">{asset.mime_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-medium">Disk Location</span>
                <span className="text-slate-300 font-mono break-all text-[11px]">
                  {asset.absolute_path || asset.storage_path}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block font-medium">Tags</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {(asset.tags || []).map((t) => (
                    <span
                      key={t.id}
                      className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono text-[10px]"
                    >
                      #{t.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
