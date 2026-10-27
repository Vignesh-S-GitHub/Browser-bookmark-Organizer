<div align="center">

# 🔖 Bookmark Organizer

**One searchable workspace for your saved links.**

![React](https://img.shields.io/badge/React-149ECA?style=flat-square&logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)

[Quick start](#quick-start) · [Features](#features) · [Local AI](#local-ai-and-storage)

</div>

---

Import a browser HTML bookmark export, arrange links into nested folders, search your collection, and export it again. A React/TypeScript frontend connects to a local FastAPI + SQLite backend. Optional browser language models suggest categories, tags, and summaries.

<a id="features"></a>

## ✨ Features

| Organize | Find | Move your collection |
|---|---|---|
| Nested folders and folder drag-to-move | Search titles, URLs, descriptions, tags, and summaries | Netscape-compatible HTML import/export |
| Create/delete bookmarks and folders | List/grid views, themes, previews, and shortcuts | Duplicate URL checks when importing or saving |
| Apply category/tag/summary suggestions | Local matching and duplicate-group inspection | Reset the library before a fresh import when needed |

<a id="quick-start"></a>

## 🚀 Quick start

Requirements: Python **3.10+** for the source syntax, Node.js compatible with Vite 6, and npm. The repository does not pin a Node engine.

```bash
git clone https://github.com/Vignesh-S-GitHub/Browser-bookmark-Organizer.git
cd Browser-bookmark-Organizer
```

**Backend — first terminal:**

```bash
cd backend
python -m venv .venv
# macOS / Linux; Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

API: **http://localhost:8000** · Interactive API docs: **http://localhost:8000/docs**.

**Frontend — second terminal, from the repository root:**

```bash
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. On Windows, [run-app.bat](run-app.bat) starts both services and [stop-app.bat](stop-app.bat) stops them.

<a id="local-ai-and-storage"></a>

## 🤖 Local AI and storage

- SQLite stores the library in `bookmarks.db`, relative to the backend's working directory. Keep an HTML export and, if needed, a database backup before resetting.
- The backend's built-in categorization and matching use local rules. Optional Transformers.js text-generation models run in a browser worker, trying WebGPU and then WASM.
- The first model run downloads weights to the browser cache; it needs internet and sufficient device resources. No hosted generation API key is required.
- Favicon and thumbnail previews can request external services. Local inference does not make every network feature offline.
- This local MVP has no account authentication or cloud synchronization.

## 🧪 Development

```bash
cd frontend
npm run build
```

The build runs TypeScript checking and Vite. No automated test suite is currently included. Backend PATCH endpoints exist for editing bookmarks/folders; richer editing forms remain a UI development opportunity.

## 📁 Repository guide

| Path | Purpose |
|---|---|
| [backend/app/main.py](backend/app/main.py) | CRUD, import/export, search, and enrichment routes |
| [backend/app/bookmark_parser.py](backend/app/bookmark_parser.py) | Browser HTML parsing and rendering |
| [backend/app/ai_tools.py](backend/app/ai_tools.py) | Local matching and enrichment helpers |
| [frontend/src/App.tsx](frontend/src/App.tsx) | Bookmark workspace |
| [frontend/src/localLlmWorker.ts](frontend/src/localLlmWorker.ts) | Browser model loading and inference |

## 🤝 Contributing

Open an issue with a reproducible example or submit a focused pull request. Keep setup instructions and documentation aligned with any behavior changes.

## 📄 License

No repository-level `LICENSE` file is currently included.
