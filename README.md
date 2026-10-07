<div align="center">

# Bookmark Organizer
### Bring browser bookmarks into one searchable workspace

**Import & export · folders · local AI assistance**

</div>

A bookmark manager for importing browser exports, organizing links into folders, and finding saved pages quickly. Optional in-browser language models can help suggest categories without sending bookmark content to a hosted AI API.

## Features

- Import and export bookmarks in the browser’s HTML format
- Create folders, add or edit bookmarks, and search your collection
- Avoid duplicate entries during import
- Browse bookmarks in a focused workspace
- Optional local model support through Transformers.js; the first use may download model files

## Stack

| Frontend | Backend | Storage |
|---|---|---|
| React, Vite, Tailwind CSS | FastAPI | SQLite |

## Run on Windows

The repository includes a launcher that starts both app parts and opens the frontend:

```powershell
./run-app.bat
```

The frontend is available at `http://localhost:5173`; the backend API runs at `http://localhost:8000`. For manual setup, see the backend and frontend directories for their respective requirements and scripts.

## Project structure

- `frontend/` — React bookmark workspace and client-side features
- `backend/` — FastAPI routes, SQLite models, and bookmark import/export parsing
- `run-app.bat` / `run-app.ps1` — Windows development launchers

---

<p align="center"><sub>Keep the useful links. Find them when you need them.</sub></p>
