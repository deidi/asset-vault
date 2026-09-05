import type { Asset, LibraryFolder, FolderTreeNode, InventoryResponse, FolderScanResult, CacheStats } from './types';

const API_BASE = '/api';

export async function fetchAssets(params: {
  page?: number;
  pageSize?: number;
  tags?: string[];
  search?: string;
  folderId?: string;
  subfolderPath?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  fileType?: string;
}): Promise<InventoryResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.pageSize) query.append('page_size', params.pageSize.toString());
  if (params.search) query.append('search', params.search);
  if (params.folderId) query.append('folder_id', params.folderId);
  if (params.subfolderPath) query.append('subfolder_path', params.subfolderPath);
  if (params.sortBy) query.append('sort_by', params.sortBy);
  if (params.sortOrder) query.append('sort_order', params.sortOrder);
  if (params.fileType) query.append('file_type', params.fileType);
  if (params.tags && params.tags.length > 0) {
    params.tags.forEach(t => query.append('tags', t));
  }

  const res = await fetch(`${API_BASE}/assets?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch assets: ${res.statusText}`);
  const data: InventoryResponse = await res.json();
  const rawList = data.assets || data.items || [];
  const normalized = rawList.map((a) => ({
    ...a,
    tags: Array.isArray(a.tags) ? a.tags : []
  }));
  return {
    ...data,
    assets: normalized,
    items: normalized
  };
}

export async function fetchFolders(): Promise<LibraryFolder[]> {
  const res = await fetch(`${API_BASE}/folders`);
  if (!res.ok) throw new Error(`Failed to fetch library folders: ${res.statusText}`);
  return res.json();
}

export async function fetchFolderTree(folderId: string): Promise<FolderTreeNode> {
  const res = await fetch(`${API_BASE}/folders/${folderId}/tree`);
  if (!res.ok) throw new Error(`Failed to fetch folder tree: ${res.statusText}`);
  return res.json();
}

export async function createFolder(payload: {
  path: string;
  name?: string;
  is_recursive?: boolean;
  auto_tag_folder?: boolean;
  custom_tags?: string[];
}): Promise<LibraryFolder> {
  const res = await fetch(`${API_BASE}/folders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to add folder');
  }
  return res.json();
}

export async function updateFolder(id: string, payload: Partial<LibraryFolder>): Promise<LibraryFolder> {
  const res = await fetch(`${API_BASE}/folders/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update folder');
  return res.json();
}

export async function pickFolderDialog(): Promise<string | null> {
  try {
    if ((window as any).pywebview?.api?.choose_folder) {
      const res = await (window as any).pywebview.api.choose_folder();
      if (res) return String(res).replace(/^["']|["']$/g, '');
    }
  } catch (e) {
    console.warn('PyWebView folder picker error:', e);
  }
  try {
    const res = await fetch(`${API_BASE}/folders/picker`, { method: 'POST' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.selected_path ? String(data.selected_path).replace(/^["']|["']$/g, '') : null;
  } catch {
    return null;
  }
}

export async function deleteFolder(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/folders/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete folder');
}

export async function scanFolder(id: string): Promise<FolderScanResult> {
  const res = await fetch(`${API_BASE}/folders/${id}/scan`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to scan folder');
  return res.json();
}

export async function scanAllFolders(): Promise<{ total_scanned: number; newly_indexed: number; results: FolderScanResult[] }> {
  const res = await fetch(`${API_BASE}/folders/scan-all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to scan all folders');
  return res.json();
}

export async function revealInExplorer(assetId?: string, folderId?: string, rawPath?: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/explorer/reveal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        asset_id: assetId || undefined,
        folder_id: folderId || undefined,
        raw_path: rawPath || undefined,
        path: rawPath || undefined,
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function renameOnDisk(assetId: string, newFilename: string): Promise<Asset> {
  const res = await fetch(`${API_BASE}/explorer/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_id: assetId, new_filename: newFilename }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to rename file');
  }
  return res.json();
}

export async function trashToRecycleBin(assetIds: string[]): Promise<{ trashed_count: number; errors: string[] }> {
  const res = await fetch(`${API_BASE}/explorer/trash`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_ids: assetIds }),
  });
  if (!res.ok) throw new Error('Failed to send items to Recycle Bin');
  return res.json();
}

export async function batchMove(assetIds: string[], destinationDirectory: string): Promise<{ status?: string; moved_count: number; errors: string[] }> {
  const res = await fetch(`${API_BASE}/explorer/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      asset_ids: assetIds,
      destination_folder: destinationDirectory,
      destination_directory: destinationDirectory,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || 'Failed to move files');
  }
  return res.json();
}

export async function updateAssetTags(assetId: string, tags: string[]): Promise<Asset> {
  const res = await fetch(`${API_BASE}/assets/${assetId}/tags`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tags),
  });
  if (!res.ok) throw new Error('Failed to update tags');
  return res.json();
}

export async function batchUpdateTags(assetIds: string[], operation: 'add' | 'remove' | 'replace', tags: string[]): Promise<any> {
  const endpoint = operation === 'add' ? 'add' : operation === 'remove' ? 'remove' : 'set';
  const res = await fetch(`${API_BASE}/assets/tags/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_ids: assetIds, tags }),
  });
  if (!res.ok) throw new Error('Failed to perform batch tag operation');
  return res.json();
}

export async function getCacheStats(): Promise<CacheStats> {
  const res = await fetch(`${API_BASE}/cache/stats`);
  if (!res.ok) throw new Error('Failed to fetch cache stats');
  return res.json();
}

export async function clearCache(): Promise<{ cleared_count: number; freed_mb: number }> {
  const res = await fetch(`${API_BASE}/cache/clear`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to clear cache');
  return res.json();
}

export async function rescanLibraryAndFixCache(): Promise<any> {
  const res = await fetch(`${API_BASE}/library/rescan`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to perform library rescan');
  return res.json();
}

export function getThumbnailUrl(assetId: string, width = 350, height = 350): string {
  return `${API_BASE}/assets/${assetId}/thumbnail?width=${width}&height=${height}`;
}

export function getMediaFileUrl(assetId: string): string {
  return `${API_BASE}/assets/${assetId}/download`;
}
