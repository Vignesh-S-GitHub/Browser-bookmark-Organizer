import {
  Brain,
  Download,
  FolderPlus,
  Grid2X2,
  Import,
  Keyboard,
  Link2,
  List,
  Moon,
  Pencil,
  Plus,
  Search,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { api } from "./api";
import type { Bookmark, DuplicateGroup, Folder, FolderTreeNode, SemanticSearchResult } from "./types";

type Notice = {
  kind: "success" | "error";
  message: string;
};

type ViewMode = "list" | "grid";

type LlmSuggestion = {
  id: number;
  category: string;
  tags: string[];
  summary: string;
};

const localModels = [
  {
    id: "HuggingFaceTB/SmolLM2-135M-Instruct",
    label: "SmolLM2 135M",
  },
  {
    id: "HuggingFaceTB/SmolLM2-360M-Instruct",
    label: "SmolLM2 360M",
  },
  {
    id: "Qwen/Qwen2.5-0.5B-Instruct",
    label: "Qwen2.5 0.5B",
  },
  {
    id: "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    label: "TinyLlama 1.1B",
  },
  {
    id: "meta-llama/Llama-3.2-1B-Instruct",
    label: "Llama 3.2 1B",
  },
];

const emptyBookmark = {
  title: "",
  url: "",
  description: "",
  folder_id: "",
};

const pageSize = 24;

export default function App() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [tree, setTree] = useState<FolderTreeNode[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [semanticQuery, setSemanticQuery] = useState("");
  const [semanticResults, setSemanticResults] = useState<SemanticSearchResult[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [llmModelId, setLlmModelId] = useState(localModels[0].id);
  const [llmStatus, setLlmStatus] = useState("Not loaded");
  const [llmOutput, setLlmOutput] = useState("");
  const [llmSuggestions, setLlmSuggestions] = useState<LlmSuggestion[]>([]);
  const [llmBusy, setLlmBusy] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [folderParent, setFolderParent] = useState("");
  const [bookmarkForm, setBookmarkForm] = useState(emptyBookmark);
  const [editingBookmarkId, setEditingBookmarkId] = useState<number | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    return (localStorage.getItem("viewMode") as ViewMode) || "list";
  });
  const [darkMode, setDarkMode] = useState(getInitialDarkMode);
  const [draggedFolderId, setDraggedFolderId] = useState<number | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const llmWorkerRef = useRef<Worker | null>(null);

  const selectedFolderName = useMemo(
    () => folders.find((folder) => folder.id === selectedFolder)?.name ?? "All bookmarks",
    [folders, selectedFolder],
  );

  const flatFolderOptions = useMemo(() => flattenFolders(tree), [tree]);

  useEffect(() => {
    applyTheme(darkMode);
    localStorage.setItem("darkMode", String(darkMode));
  }, [darkMode]);

  useEffect(() => {
    return () => llmWorkerRef.current?.terminate();
  }, []);

  useEffect(() => {
    localStorage.setItem("viewMode", viewMode);
  }, [viewMode]);

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    loadBookmarks(true).catch(showError);
  }, [search, selectedFolder]);

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || !hasMore || loading || loadingMore || semanticResults.length > 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          loadBookmarks(false).catch(showError);
        }
      },
      { rootMargin: "220px" },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [bookmarks.length, hasMore, loading, loadingMore, semanticResults.length]);

  useEffect(() => {
    function handleKeys(event: globalThis.KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isTyping = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.tagName === "SELECT";
      if (event.key === "Escape") {
        resetBookmarkForm();
        setSemanticResults([]);
        return;
      }
      if (isTyping) return;
      if (event.key === "/") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key.toLowerCase() === "n") {
        titleRef.current?.focus();
      }
      if (event.key.toLowerCase() === "g") {
        setViewMode((mode) => (mode === "grid" ? "list" : "grid"));
      }
      if (event.key.toLowerCase() === "d") {
        setDarkMode((mode) => !mode);
      }
    }
    window.addEventListener("keydown", handleKeys);
    return () => window.removeEventListener("keydown", handleKeys);
  }, []);

  async function loadFolders() {
    const [nextFolders, nextTree] = await Promise.all([api.listFolders(), api.folderTree()]);
    setFolders(nextFolders);
    setTree(nextTree);
  }

  async function loadBookmarks(reset = false) {
    const offset = reset ? 0 : bookmarks.length;
    if (!reset) setLoadingMore(true);
    try {
      const nextBookmarks = await api.listBookmarks({
        search,
        folderId: selectedFolder,
        limit: pageSize,
        offset,
      });
      setBookmarks(reset ? nextBookmarks : [...bookmarks, ...nextBookmarks]);
      setHasMore(nextBookmarks.length === pageSize);
    } finally {
      if (!reset) setLoadingMore(false);
    }
  }

  async function refreshAll() {
    setLoading(true);
    try {
      await loadFolders();
      const nextBookmarks = await api.listBookmarks({
        search,
        folderId: selectedFolder,
        limit: pageSize,
        offset: 0,
      });
      setBookmarks(nextBookmarks);
      setHasMore(nextBookmarks.length === pageSize);
    } catch (error) {
      showError(error);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateFolder(event: FormEvent) {
    event.preventDefault();
    if (!folderName.trim()) return;

    try {
      await api.createFolder({
        name: folderName.trim(),
        parent_id: folderParent ? Number(folderParent) : null,
      });
      setFolderName("");
      setFolderParent("");
      await loadFolders();
      setNotice({ kind: "success", message: "Folder added" });
    } catch (error) {
      showError(error);
    }
  }

  async function handleCreateBookmark(event: FormEvent) {
    event.preventDefault();
    if (!bookmarkForm.title.trim() || !bookmarkForm.url.trim()) return;

    try {
      const payload = {
        title: bookmarkForm.title.trim(),
        url: bookmarkForm.url.trim(),
        description: bookmarkForm.description.trim() || null,
        folder_id: bookmarkForm.folder_id ? Number(bookmarkForm.folder_id) : null,
      };
      if (editingBookmarkId) {
        await api.updateBookmark(editingBookmarkId, payload);
      } else {
        await api.createBookmark(payload);
      }
      resetBookmarkForm();
      await loadBookmarks(true);
      setNotice({ kind: "success", message: editingBookmarkId ? "Bookmark updated" : "Bookmark added" });
    } catch (error) {
      showError(error);
    }
  }

  function handleEditBookmark(bookmark: Bookmark) {
    setEditingBookmarkId(bookmark.id);
    setBookmarkForm({
      title: bookmark.title,
      url: bookmark.url,
      description: bookmark.description ?? "",
      folder_id: bookmark.folder_id ? String(bookmark.folder_id) : "",
    });
    titleRef.current?.focus();
  }

  function resetBookmarkForm() {
    setBookmarkForm(emptyBookmark);
    setEditingBookmarkId(null);
  }

  async function handleDeleteBookmark(id: number) {
    try {
      await api.deleteBookmark(id);
      await loadBookmarks(true);
    } catch (error) {
      showError(error);
    }
  }

  async function handleDeleteFolder(id: number) {
    try {
      await api.deleteFolder(id);
      if (selectedFolder === id) setSelectedFolder(null);
      await refreshAll();
    } catch (error) {
      showError(error);
    }
  }

  async function handleMoveFolder(folderId: number, parentId: number | null) {
    if (folderId === parentId) return;
    try {
      await api.updateFolder(folderId, { parent_id: parentId });
      await loadFolders();
      setNotice({ kind: "success", message: "Folder moved" });
    } catch (error) {
      showError(error);
    } finally {
      setDraggedFolderId(null);
    }
  }

  async function handleImport(file: File | undefined) {
    if (!file) return;

    try {
      const summary = await api.importBookmarks(file);
      await refreshAll();
      setNotice({
        kind: "success",
        message: `Imported ${summary.bookmarks_created} bookmarks, skipped ${summary.skipped_duplicates} duplicates`,
      });
    } catch (error) {
      showError(error);
    }
  }

  async function handleResetLibrary() {
    const confirmed = window.confirm(
      "Clear all folders and bookmarks? This is useful before importing a new bookmark HTML file.",
    );
    if (!confirmed) return;

    try {
      const summary = await api.resetLibrary();
      setSelectedFolder(null);
      setSemanticResults([]);
      setDuplicates([]);
      resetBookmarkForm();
      await refreshAll();
      setNotice({
        kind: "success",
        message: `Cleared ${summary.bookmarks_deleted} bookmarks and ${summary.folders_deleted} folders`,
      });
    } catch (error) {
      showError(error);
    }
  }

  async function runLocalLlm() {
    const input = bookmarks.slice(0, 12).map((bookmark) => ({
      id: bookmark.id,
      title: bookmark.title,
      url: bookmark.url,
      description: bookmark.description,
    }));

    if (input.length === 0) {
      setNotice({ kind: "error", message: "Import bookmarks before running the local LLM" });
      return;
    }

    setLlmBusy(true);
    setLlmOutput("");
    setLlmSuggestions([]);

    try {
      const worker = getLocalLlmWorker();
      const requestId = crypto.randomUUID();
      const text = await new Promise<string>((resolve, reject) => {
        worker.onmessage = (event: MessageEvent) => {
          if (event.data.id !== requestId) return;
          if (event.data.type === "status") {
            setLlmStatus(event.data.message);
          }
          if (event.data.type === "result") {
            resolve(event.data.text);
          }
          if (event.data.type === "error") {
            reject(new Error(event.data.message));
          }
        };
        worker.postMessage({ id: requestId, modelId: llmModelId, bookmarks: input });
      });

      const suggestions = parseLlmSuggestions(text);
      setLlmOutput(text);
      setLlmSuggestions(suggestions);
      setLlmStatus(`Generated ${suggestions.length} suggestions locally`);
      setNotice({ kind: "success", message: `Local LLM generated ${suggestions.length} bookmark suggestions` });
    } catch (error) {
      showError(error);
      setLlmStatus("Local LLM failed");
    } finally {
      setLlmBusy(false);
    }
  }

  async function applyLocalLlmSuggestions() {
    const suggestions = llmSuggestions.length > 0 ? llmSuggestions : parseLlmSuggestions(llmOutput);
    if (suggestions.length === 0) {
      setNotice({ kind: "error", message: "No valid local LLM suggestions to apply" });
      return;
    }

    setLlmBusy(true);
    try {
      const latestFolders = await api.listFolders();
      const folderByName = new Map(latestFolders.map((folder) => [folder.name.toLowerCase(), folder]));
      let applied = 0;

      for (const suggestion of suggestions) {
        const bookmark = bookmarks.find((item) => item.id === suggestion.id);
        if (!bookmark) continue;

        const category = suggestion.category.trim() || "Unsorted";
        let folder = folderByName.get(category.toLowerCase());
        if (!folder) {
          folder = await api.createFolder({ name: category, parent_id: null });
          folderByName.set(category.toLowerCase(), folder);
        }

        await api.updateBookmark(bookmark.id, {
          title: bookmark.title,
          url: bookmark.url,
          description: bookmark.description,
          tags: suggestion.tags.slice(0, 6).join(", "),
          summary: suggestion.summary,
          folder_id: folder.id,
        });
        applied += 1;
      }

      await refreshAll();
      setNotice({ kind: "success", message: `Applied ${applied} local LLM suggestions` });
    } catch (error) {
      showError(error);
    } finally {
      setLlmBusy(false);
    }
  }

  function getLocalLlmWorker() {
    if (!llmWorkerRef.current) {
      llmWorkerRef.current = new Worker(new URL("./localLlmWorker.ts", import.meta.url), {
        type: "module",
      });
    }
    return llmWorkerRef.current;
  }

  function showError(error: unknown) {
    setNotice({
      kind: "error",
      message: error instanceof Error ? error.message : "Something went wrong",
    });
  }

  const displayedBookmarks = semanticResults.length > 0 ? semanticResults.map((result) => result.bookmark) : bookmarks;

  return (
    <main
      className={`min-h-screen ${
        darkMode
          ? "dark theme-dark bg-slate-950 text-slate-100"
          : "theme-light bg-slate-100 text-slate-900"
      }`}
    >
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-4 px-4 py-4 md:px-6 lg:grid lg:grid-cols-[310px_1fr]">
        <aside className="rounded border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-200 p-4 dark:border-slate-800">
            <div className="flex flex-col gap-3">
              <h1 className="text-xl font-semibold tracking-normal">Bookmarks</h1>
              <div className="grid grid-cols-5 gap-2">
                <IconButton label="Keyboard shortcuts" onClick={() => setNotice({ kind: "success", message: "/ search, N new, G view, D theme, Esc clear" })}>
                  <Keyboard size={18} />
                </IconButton>
                <IconButton label="Toggle theme" onClick={() => setDarkMode((mode) => !mode)}>
                  {darkMode ? <Sun size={18} /> : <Moon size={18} />}
                </IconButton>
                <label className="focus-ring inline-flex h-10 w-full cursor-pointer items-center justify-center rounded border border-slate-200 bg-white text-slate-700 hover:border-teal-500 hover:text-teal-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200" title="Import">
                  <Import size={18} />
                  <input
                    className="hidden"
                    type="file"
                    accept=".html,.htm,text/html"
                    onChange={(event) => handleImport(event.target.files?.[0])}
                  />
                </label>
                <IconButton label="Clear library" onClick={handleResetLibrary}>
                  <Trash2 size={18} />
                </IconButton>
                <a
                  className="focus-ring inline-flex h-10 w-full items-center justify-center rounded border border-slate-200 bg-white text-slate-700 hover:border-teal-500 hover:text-teal-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                  href={api.exportUrl}
                  title="Export"
                >
                  <Download size={18} />
                </a>
              </div>
            </div>
          </div>

          <div
            className="p-3"
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => draggedFolderId && handleMoveFolder(draggedFolderId, null)}
          >
            <button
              className={`focus-ring mb-2 flex h-10 w-full items-center justify-between rounded px-3 text-left text-sm font-medium ${
                selectedFolder === null
                  ? "bg-slate-900 text-white dark:bg-teal-500 dark:text-slate-950"
                  : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              }`}
              onClick={() => setSelectedFolder(null)}
            >
              <span>All bookmarks</span>
              <span>{bookmarks.length}</span>
            </button>
            <div className="space-y-1">
              {tree.map((folder) => (
                <FolderItem
                  draggedFolderId={draggedFolderId}
                  folder={folder}
                  key={folder.id}
                  selectedFolder={selectedFolder}
                  onDelete={handleDeleteFolder}
                  onDragStart={setDraggedFolderId}
                  onDrop={handleMoveFolder}
                  onSelect={setSelectedFolder}
                />
              ))}
            </div>
          </div>

          <form className="border-t border-slate-200 p-4 dark:border-slate-800" onSubmit={handleCreateFolder}>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <FolderPlus size={16} />
              <span>New folder</span>
            </div>
            <input
              className="input mb-2"
              placeholder="Folder name"
              value={folderName}
              onChange={(event) => setFolderName(event.target.value)}
            />
            <select
              className="input mb-3"
              value={folderParent}
              onChange={(event) => setFolderParent(event.target.value)}
            >
              <option value="">Top level</option>
              {flatFolderOptions.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.label}
                </option>
              ))}
            </select>
            <button className="focus-ring inline-flex h-10 w-full items-center justify-center gap-2 rounded bg-teal-600 px-3 text-sm font-semibold text-white hover:bg-teal-700">
              <Plus size={16} />
              Add folder
            </button>
          </form>
        </aside>

        <section className="flex min-w-0 flex-col gap-4">
          <div className="rounded border border-slate-200 bg-white p-4 shadow-soft dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <p className="text-sm font-medium text-teal-700 dark:text-teal-300">{selectedFolderName}</p>
                <h2 className="text-2xl font-semibold tracking-normal">Library</h2>
              </div>
              <div className="flex flex-col gap-2 md:flex-row md:items-center">
                <label className="focus-within:ring-2 focus-within:ring-teal-500 flex h-11 min-w-0 items-center gap-2 rounded border border-slate-200 bg-white px-3 dark:border-slate-700 dark:bg-slate-950 md:w-80">
                  <Search size={18} className="shrink-0 text-slate-500" />
                  <input
                    className="min-w-0 flex-1 bg-transparent outline-none"
                    placeholder="Search title, URL, tags"
                    ref={searchRef}
                    value={search}
                    onChange={(event) => {
                      setSemanticResults([]);
                      setSearch(event.target.value);
                    }}
                  />
                </label>
                <div className="flex h-11 rounded border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-950">
                  <button className={toggleClass(viewMode === "list")} onClick={() => setViewMode("list")} title="List view">
                    <List size={17} />
                  </button>
                  <button className={toggleClass(viewMode === "grid")} onClick={() => setViewMode("grid")} title="Grid view">
                    <Grid2X2 size={17} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {notice && (
            <div
              className={`rounded border px-4 py-3 text-sm ${
                notice.kind === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
                  : "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
              }`}
            >
              {notice.message}
            </div>
          )}

          <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
            <form className="rounded border border-slate-200 bg-white p-4 shadow-soft dark:border-slate-800 dark:bg-slate-900" onSubmit={handleCreateBookmark}>
              <div className="grid gap-3 md:grid-cols-[1fr_1fr_180px_auto]">
                <input
                  className="input"
                  placeholder="Title"
                  ref={titleRef}
                  value={bookmarkForm.title}
                  onChange={(event) => setBookmarkForm({ ...bookmarkForm, title: event.target.value })}
                />
                <input
                  className="input"
                  placeholder="https://example.com"
                  value={bookmarkForm.url}
                  onChange={(event) => setBookmarkForm({ ...bookmarkForm, url: event.target.value })}
                />
                <select
                  className="input"
                  value={bookmarkForm.folder_id}
                  onChange={(event) => setBookmarkForm({ ...bookmarkForm, folder_id: event.target.value })}
                >
                  <option value="">No folder</option>
                  {flatFolderOptions.map((folder) => (
                    <option key={folder.id} value={folder.id}>
                      {folder.label}
                    </option>
                  ))}
                </select>
                <button className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded bg-slate-900 px-4 font-semibold text-white hover:bg-slate-800 dark:bg-teal-500 dark:text-slate-950 dark:hover:bg-teal-400">
                  <Link2 size={17} />
                  {editingBookmarkId ? "Update" : "Save"}
                </button>
              </div>
              <textarea
                className="input mt-3 min-h-20 resize-y py-2"
                placeholder="Notes"
                value={bookmarkForm.description}
                onChange={(event) => setBookmarkForm({ ...bookmarkForm, description: event.target.value })}
              />
              {editingBookmarkId && (
                <button
                  className="focus-ring mt-3 inline-flex h-9 items-center gap-2 rounded border border-slate-200 px-3 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  onClick={resetBookmarkForm}
                  type="button"
                >
                  <X size={15} />
                  Cancel edit
                </button>
              )}
            </form>

            <div className="rounded border border-slate-200 bg-white p-4 shadow-soft dark:border-slate-800 dark:bg-slate-900">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold">
                  <Brain size={18} className="text-amber-500" />
                  <span>Local LLM</span>
                </div>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {llmBusy ? "Running..." : "Browser local"}
                </span>
              </div>
              <select
                className="input mb-3"
                value={llmModelId}
                onChange={(event) => {
                  setLlmModelId(event.target.value);
                  setLlmStatus("Not loaded");
                  setLlmOutput("");
                  setLlmSuggestions([]);
                  llmWorkerRef.current?.terminate();
                  llmWorkerRef.current = null;
                }}
              >
                {localModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.label}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <ActionButton disabled={llmBusy} onClick={runLocalLlm}>
                  <Sparkles size={16} />
                  Analyze
                </ActionButton>
                <ActionButton disabled={llmBusy || llmSuggestions.length === 0} onClick={applyLocalLlmSuggestions}>
                  <FolderPlus size={16} />
                  Apply
                </ActionButton>
                <ActionButton disabled={llmBusy} onClick={() => setLlmOutput("")}>
                  <X size={16} />
                  Clear
                </ActionButton>
                <ActionButton disabled={llmBusy} onClick={() => setNotice({ kind: "success", message: llmStatus })}>
                  <Brain size={16} />
                  Status
                </ActionButton>
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
                First run downloads the selected quantized model to browser cache. Analysis runs on your device.
              </p>
              <textarea
                className="input mt-3 min-h-28 resize-y py-2 text-xs"
                placeholder="Local LLM JSON output appears here"
                value={llmOutput || llmStatus}
                onChange={(event) => {
                  setLlmOutput(event.target.value);
                  setLlmSuggestions(parseLlmSuggestions(event.target.value));
                }}
              />
            </div>
          </div>

          {duplicates.length > 0 && (
            <div className="rounded border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
              <div className="mb-2 font-semibold">Duplicate groups</div>
              <div className="grid gap-2 md:grid-cols-2">
                {duplicates.slice(0, 4).map((group, index) => (
                  <div className="rounded border border-amber-200 bg-white p-3 dark:border-amber-800 dark:bg-slate-900" key={`${group.reason}-${index}`}>
                    <div className="font-medium">{group.reason}</div>
                    <div className="mt-1 text-xs opacity-80">
                      {group.bookmarks.map((bookmark) => bookmark.title).join(" / ")}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="min-h-[360px] rounded border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900">
            {loading ? (
              <div className="p-6 text-sm text-slate-500">Loading...</div>
            ) : displayedBookmarks.length === 0 ? (
              <div className="p-6 text-sm text-slate-500">No bookmarks found.</div>
            ) : (
              <>
                <div className={viewMode === "grid" ? "grid gap-4 p-4 md:grid-cols-2 2xl:grid-cols-3" : "divide-y divide-slate-200 dark:divide-slate-800"}>
                  {displayedBookmarks.map((bookmark) => (
                    <BookmarkCard
                      bookmark={bookmark}
                      key={bookmark.id}
                      mode={viewMode}
                      score={semanticResults.find((result) => result.bookmark.id === bookmark.id)?.score}
                      onDelete={handleDeleteBookmark}
                      onEdit={handleEditBookmark}
                    />
                  ))}
                </div>
                <div ref={loadMoreRef} />
                {hasMore && semanticResults.length === 0 && (
                  <div className="border-t border-slate-200 p-4 text-center dark:border-slate-800">
                    <button
                      className="focus-ring rounded border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                      onClick={() => loadBookmarks(false)}
                    >
                      {loadingMore ? "Loading..." : "Load more"}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function FolderItem({
  draggedFolderId,
  folder,
  selectedFolder,
  onSelect,
  onDelete,
  onDragStart,
  onDrop,
  depth = 0,
}: {
  draggedFolderId: number | null;
  folder: FolderTreeNode;
  selectedFolder: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  onDragStart: (id: number) => void;
  onDrop: (folderId: number, parentId: number | null) => void;
  depth?: number;
}) {
  const active = selectedFolder === folder.id;
  const dragging = draggedFolderId === folder.id;
  return (
    <div>
      <div
        className={`group flex items-center gap-1 rounded ${dragging ? "opacity-50" : ""}`}
        draggable
        onDragOver={(event) => event.preventDefault()}
        onDragStart={() => onDragStart(folder.id)}
        onDrop={(event) => {
          event.stopPropagation();
          if (draggedFolderId) onDrop(draggedFolderId, folder.id);
        }}
        style={{ paddingLeft: depth * 12 }}
      >
        <button
          className={`focus-ring flex h-9 min-w-0 flex-1 items-center rounded px-3 text-left text-sm font-medium ${
            active
              ? "bg-teal-600 text-white"
              : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          }`}
          onClick={() => onSelect(folder.id)}
        >
          <span className="truncate">{folder.name}</span>
        </button>
        <button
          className="focus-ring flex h-9 w-9 shrink-0 items-center justify-center rounded text-slate-400 opacity-100 hover:bg-rose-50 hover:text-rose-700 dark:hover:bg-rose-950 md:opacity-0 md:group-hover:opacity-100"
          onClick={() => onDelete(folder.id)}
          title="Delete folder"
        >
          <Trash2 size={15} />
        </button>
      </div>
      {folder.children.map((child) => (
        <FolderItem
          depth={depth + 1}
          draggedFolderId={draggedFolderId}
          folder={child}
          key={child.id}
          selectedFolder={selectedFolder}
          onDelete={onDelete}
          onDragStart={onDragStart}
          onDrop={onDrop}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

function BookmarkCard({
  bookmark,
  mode,
  score,
  onDelete,
  onEdit,
}: {
  bookmark: Bookmark;
  mode: ViewMode;
  score?: number;
  onDelete: (id: number) => void;
  onEdit: (bookmark: Bookmark) => void;
}) {
  const tags = splitTags(bookmark.tags);
  const image = (
    <div className="relative h-24 overflow-hidden rounded bg-slate-100 dark:bg-slate-800 md:h-28">
      {bookmark.thumbnail_url ? (
        <img className="h-full w-full object-cover" src={bookmark.thumbnail_url} alt="" loading="lazy" />
      ) : (
        <div className="flex h-full items-center justify-center text-sm font-semibold text-slate-400">
          {domainFromUrl(bookmark.url)}
        </div>
      )}
      {bookmark.favicon_url && (
        <img className="absolute left-2 top-2 h-8 w-8 rounded bg-white p-1 shadow" src={bookmark.favicon_url} alt="" loading="lazy" />
      )}
    </div>
  );

  return (
    <article className={mode === "grid" ? "rounded border border-slate-200 p-3 dark:border-slate-800" : "grid gap-3 p-4 md:grid-cols-[170px_1fr_auto]"}>
      {image}
      <div className="min-w-0">
        <div className="flex items-start gap-2">
          {bookmark.favicon_url && mode === "list" && (
            <img className="mt-0.5 h-5 w-5 shrink-0" src={bookmark.favicon_url} alt="" loading="lazy" />
          )}
          <div className="min-w-0">
            <a
              className="block truncate text-base font-semibold text-slate-900 hover:text-teal-700 dark:text-slate-50 dark:hover:text-teal-300"
              href={bookmark.url}
              rel="noreferrer"
              target="_blank"
            >
              {bookmark.title}
            </a>
            <p className="mt-1 truncate text-sm text-slate-500 dark:text-slate-400">{bookmark.url}</p>
          </div>
        </div>
        {score !== undefined && (
          <div className="mt-2 inline-flex rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900 dark:bg-amber-900 dark:text-amber-100">
            {(score * 100).toFixed(0)}% match
          </div>
        )}
        {bookmark.summary && <p className="mt-2 line-clamp-2 text-sm text-slate-700 dark:text-slate-300">{bookmark.summary}</p>}
        {tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span className="rounded bg-teal-50 px-2 py-1 text-xs font-medium text-teal-800 dark:bg-teal-950 dark:text-teal-200" key={tag}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded border border-slate-200 text-slate-600 hover:border-teal-300 hover:text-teal-700 dark:border-slate-700 dark:text-slate-300"
          onClick={() => onEdit(bookmark)}
          title="Edit bookmark"
        >
          <Pencil size={17} />
        </button>
        <button
          className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded border border-slate-200 text-slate-600 hover:border-rose-300 hover:text-rose-700 dark:border-slate-700 dark:text-slate-300"
          onClick={() => onDelete(bookmark.id)}
          title="Delete bookmark"
        >
          <Trash2 size={17} />
        </button>
      </div>
    </article>
  );
}

function IconButton({ children, label, onClick }: { children: ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      className="focus-ring inline-flex h-10 w-full items-center justify-center rounded border border-slate-200 bg-white text-slate-700 hover:border-teal-500 hover:text-teal-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
      onClick={onClick}
      title={label}
      type="button"
    >
      {children}
    </button>
  );
}

function ActionButton({
  children,
  disabled,
  onClick,
}: {
  children: ReactNode;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded border border-slate-200 px-3 text-sm font-semibold text-slate-700 hover:border-teal-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function flattenFolders(nodes: FolderTreeNode[], depth = 0): { id: number; label: string }[] {
  return nodes.flatMap((node) => [
    { id: node.id, label: `${"  ".repeat(depth)}${node.name}` },
    ...flattenFolders(node.children, depth + 1),
  ]);
}

function splitTags(tags: string | null): string[] {
  return (tags ?? "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function domainFromUrl(url: string): string {
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function toggleClass(active: boolean) {
  return `focus-ring flex h-9 w-9 items-center justify-center rounded ${
    active
      ? "bg-slate-900 text-white dark:bg-teal-500 dark:text-slate-950"
      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
  }`;
}

function getInitialDarkMode() {
  const stored = localStorage.getItem("darkMode");
  if (stored === "true") return true;
  if (stored === "false") return false;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

function applyTheme(darkMode: boolean) {
  const root = document.documentElement;
  root.classList.toggle("dark", darkMode);
  document.body.classList.toggle("dark", darkMode);
  root.dataset.theme = darkMode ? "dark" : "light";
  root.style.colorScheme = darkMode ? "dark" : "light";
}

function parseLlmSuggestions(text: string): LlmSuggestion[] {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) return [];

  try {
    const parsed = JSON.parse(text.slice(start, end + 1)) as { items?: LlmSuggestion[] };
    if (!Array.isArray(parsed.items)) return [];
    return parsed.items
      .filter((item) => Number.isFinite(item.id) && item.category && item.summary)
      .map((item) => ({
        id: item.id,
        category: String(item.category).slice(0, 80),
        tags: Array.isArray(item.tags) ? item.tags.map(String).slice(0, 6) : [],
        summary: String(item.summary).slice(0, 240),
      }));
  } catch {
    return [];
  }
}
