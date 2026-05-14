import type {
  AIEnrichSummary,
  Bookmark,
  BookmarkPayload,
  DuplicateGroup,
  Folder,
  FolderTreeNode,
  ImportSummary,
  ResetSummary,
  SemanticSearchResult,
} from "./types";

const configuredApiUrl = import.meta.env.VITE_API_URL;
const apiCandidates = configuredApiUrl
  ? [configuredApiUrl]
  : ["http://localhost:8010", "http://127.0.0.1:8010", "http://localhost:8000"];
let activeApiUrl = apiCandidates[0];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response | null = null;
  let lastError: unknown = null;

  for (const baseUrl of [activeApiUrl, ...apiCandidates.filter((url) => url !== activeApiUrl)]) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        ...init,
        headers: {
          ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
          ...init?.headers,
        },
      });
      activeApiUrl = baseUrl;
      break;
    } catch (error) {
      lastError = error;
    }
  }

  if (!response) {
    throw lastError instanceof Error ? lastError : new Error("API server is not reachable");
  }

  if (!response.ok) {
    const message = await response.text();
    let detail = "";
    try {
      const parsed = JSON.parse(message) as { detail?: string };
      detail = parsed.detail || "";
    } catch {
      detail = message;
    }
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  listFolders: () => request<Folder[]>("/api/folders"),
  folderTree: () => request<FolderTreeNode[]>("/api/folders/tree"),
  createFolder: (payload: { name: string; parent_id?: number | null }) =>
    request<Folder>("/api/folders", { method: "POST", body: JSON.stringify(payload) }),
  updateFolder: (id: number, payload: { name?: string; parent_id?: number | null; sort_order?: number }) =>
    request<Folder>(`/api/folders/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteFolder: (id: number) => request<void>(`/api/folders/${id}`, { method: "DELETE" }),
  listBookmarks: (params: { search?: string; folderId?: number | null; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.folderId) query.set("folder_id", String(params.folderId));
    if (params.limit) query.set("limit", String(params.limit));
    if (params.offset) query.set("offset", String(params.offset));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<Bookmark[]>(`/api/bookmarks${suffix}`);
  },
  createBookmark: (payload: BookmarkPayload) =>
    request<Bookmark>("/api/bookmarks", { method: "POST", body: JSON.stringify(payload) }),
  updateBookmark: (id: number, payload: BookmarkPayload) =>
    request<Bookmark>(`/api/bookmarks/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteBookmark: (id: number) => request<void>(`/api/bookmarks/${id}`, { method: "DELETE" }),
  resetLibrary: () => request<ResetSummary>("/api/library", { method: "DELETE" }),
  importBookmarks: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<ImportSummary>("/api/import", { method: "POST", body: formData });
  },
  enrichAll: () => request<AIEnrichSummary>("/api/ai/enrich", { method: "POST" }),
  enrichBookmark: (id: number) =>
    request<Bookmark>(`/api/ai/bookmarks/${id}/enrich`, { method: "POST" }),
  autoCategorize: () => request<AIEnrichSummary>("/api/ai/auto-categorize", { method: "POST" }),
  semanticSearch: (query: string) =>
    request<SemanticSearchResult[]>(`/api/ai/semantic-search?query=${encodeURIComponent(query)}`),
  duplicates: () => request<DuplicateGroup[]>("/api/ai/duplicates"),
  get exportUrl() {
    return `${activeApiUrl}/api/export`;
  },
};
