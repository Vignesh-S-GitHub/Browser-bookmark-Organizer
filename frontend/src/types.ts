export type Folder = {
  id: number;
  name: string;
  parent_id: number | null;
  sort_order: number;
  created_at: string;
};

export type FolderTreeNode = Folder & {
  children: FolderTreeNode[];
};

export type Bookmark = {
  id: number;
  title: string;
  url: string;
  description: string | null;
  tags: string | null;
  summary: string | null;
  favicon_url: string | null;
  thumbnail_url: string | null;
  folder_id: number | null;
  created_at: string;
  updated_at: string;
};

export type BookmarkPayload = {
  title: string;
  url: string;
  description?: string | null;
  tags?: string | null;
  summary?: string | null;
  favicon_url?: string | null;
  thumbnail_url?: string | null;
  folder_id?: number | null;
};

export type ImportSummary = {
  folders_created: number;
  bookmarks_created: number;
  skipped_duplicates: number;
};

export type AIEnrichSummary = {
  bookmarks_updated: number;
};

export type ResetSummary = {
  folders_deleted: number;
  bookmarks_deleted: number;
};

export type SemanticSearchResult = {
  bookmark: Bookmark;
  score: number;
};

export type DuplicateGroup = {
  reason: string;
  bookmarks: Bookmark[];
};
