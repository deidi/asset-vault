export interface Tag {
  id: string;
  name: string;
}

export interface LibraryFolder {
  id: string;
  path: string;
  name: string;
  is_recursive: boolean;
  auto_tag_folder: boolean;
  custom_tags: string;
  is_active: boolean;
  created_at: string;
  asset_count?: number;
}

export interface FolderTreeNode {
  name: string;
  path: string;
  relative_path: string;
  asset_count: number;
  children: FolderTreeNode[];
}

export interface Asset {
  id: string;
  name: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  storage_path: string;
  description?: string | null;
  folder_id?: string | null;
  category?: string | null;
  file_modified_at?: string | null;
  file_hash?: string | null;
  thumbnail_path?: string | null;
  created_at: string;
  tags: Tag[];
  absolute_path?: string;
}

export interface InventoryResponse {
  total: number;
  page: number;
  page_size?: number;
  pageSize?: number;
  total_pages?: number;
  totalPages?: number;
  assets?: Asset[];
  items?: Asset[];
}

export interface FolderScanResult {
  folder_id: string;
  folder_path: string;
  folder_name: string;
  total_scanned: number;
  newly_indexed: number;
  already_indexed: number;
  errors: string[];
}

export interface CacheStats {
  total_cached_thumbnails: number;
  cache_directory: string;
  total_size_bytes: number;
  total_size_mb: number;
}

export interface WebSocketEvent {
  event: 'file_added' | 'file_modified' | 'file_renamed' | 'file_deleted' | 'folder_scanned';
  data: any;
}

export interface CategoryExtensionsMap {
  image: string[];
  video: string[];
  audio: string[];
  document: string[];
  [key: string]: string[];
}

export interface FileTypeSettingsResponse {
  categories: CategoryExtensionsMap;
  defaults: CategoryExtensionsMap;
  counts: Record<string, number>;
}

export interface UpdateFileTypeSettingsRequest {
  categories: CategoryExtensionsMap;
  recategorize_existing?: boolean;
}

export interface UpdateFileTypeSettingsResponse {
  status: string;
  categories: CategoryExtensionsMap;
  recategorized_count: number;
}
