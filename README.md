# Browser Categorize Tool

A lightweight bookmark manager MVP with browser bookmark import/export, folders, bookmark CRUD, and search.

## Stack

- Frontend: React, Vite, Tailwind CSS
- Backend: FastAPI
- Database: SQLite

## Project Layout

```text
backend/
  app/
    main.py              FastAPI routes
    models.py            SQLAlchemy models
    schemas.py           API schemas
    bookmark_parser.py   Netscape bookmark HTML import/export
frontend/
  src/
    App.tsx              Main bookmark workspace
    api.ts               API client
```

## Run Backend

Simplest option on Windows:

```powershell
.\run-app.bat
```

That starts the backend and frontend, then opens the app at `http://localhost:5173`.

To stop both servers:

```powershell
.\stop-app.bat
```

Manual backend command:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

## Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

## MVP Features

- Import browser bookmarks from HTML exports
- Skip duplicate bookmarks during import
- Clear the existing library before importing a new bookmark HTML file
- View nested folder hierarchy
- Create and delete folders
- Create and delete bookmarks
- Search bookmarks by title, URL, and notes
- Export bookmarks back to Netscape-compatible HTML

## Stage 2 UX Features

- Drag folders onto other folders to move them
- Switch between list and grid views
- Toggle dark mode
- Favicon and thumbnail previews for bookmarks
- Infinite scrolling with a fallback load-more button
- Keyboard shortcuts for search, new bookmark, view mode, theme, and clear

## Browser-Local LLM Features

These features run in the user's browser with Transformers.js. No backend API key is required.
The first run downloads the selected quantized model into the browser cache.

- Model choices include SmolLM2 135M, SmolLM2 360M, Qwen2.5 0.5B, TinyLlama 1.1B, and Llama 3.2 1B
- Local JSON suggestions for folder category, tags, and summary
- Apply local LLM suggestions to create folders and update bookmarks
- Duplicate detection by URL and similar title/domain
- Duplicate blocking when saving or importing the same bookmark again

## Next Stage Candidates

- Edit forms for existing bookmarks and folders
- Authentication and sync
- Real LLM/embedding integration with OpenAI or local embedding models
- Reader mode and saved article content
