from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import delete, or_, select, text
from sqlalchemy.orm import Session, selectinload

from .ai_tools import (
    duplicate_groups,
    enrich_bookmark,
    find_best_folder,
    favicon_url,
    normalize_url,
    semantic_score,
    suggest_category,
    thumbnail_url,
)
from .bookmark_parser import ParsedFolder, parse_bookmarks_html, render_bookmarks_html
from .database import Base, engine, get_db
from .models import Bookmark, Folder
from .schemas import (
    AIEnrichSummary,
    AIModelStatus,
    BookmarkCreate,
    BookmarkRead,
    BookmarkUpdate,
    DuplicateGroup,
    FolderCreate,
    FolderRead,
    FolderTree,
    FolderUpdate,
    ImportSummary,
    ResetSummary,
    SemanticSearchResult,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Browser Categorize Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/folders", response_model=list[FolderRead])
def list_folders(db: Session = Depends(get_db)) -> list[Folder]:
    return list(db.scalars(select(Folder).order_by(Folder.sort_order, Folder.name)).all())


@app.get("/api/folders/tree", response_model=list[FolderTree])
def folder_tree(db: Session = Depends(get_db)) -> list[dict]:
    folders = db.scalars(select(Folder).order_by(Folder.sort_order, Folder.name)).all()
    nodes = {
        folder.id: {
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
            "sort_order": folder.sort_order,
            "created_at": folder.created_at,
            "children": [],
        }
        for folder in folders
    }
    roots = []
    for folder in folders:
        node = nodes[folder.id]
        if folder.parent_id and folder.parent_id in nodes:
            nodes[folder.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


@app.post("/api/folders", response_model=FolderRead, status_code=201)
def create_folder(payload: FolderCreate, db: Session = Depends(get_db)) -> Folder:
    if payload.parent_id:
        ensure_folder_exists(payload.parent_id, db)
    folder = Folder(
        name=payload.name,
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@app.patch("/api/folders/{folder_id}", response_model=FolderRead)
def update_folder(folder_id: int, payload: FolderUpdate, db: Session = Depends(get_db)) -> Folder:
    folder = ensure_folder_exists(folder_id, db)
    if payload.parent_id == folder_id:
        raise HTTPException(status_code=400, detail="A folder cannot be its own parent")
    if payload.parent_id:
        ensure_folder_exists(payload.parent_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(folder, field, value)
    db.commit()
    db.refresh(folder)
    return folder


@app.delete("/api/folders/{folder_id}", status_code=204)
def delete_folder(folder_id: int, db: Session = Depends(get_db)) -> Response:
    folder = ensure_folder_exists(folder_id, db)
    db.delete(folder)
    db.commit()
    return Response(status_code=204)


@app.get("/api/bookmarks", response_model=list[BookmarkRead])
def list_bookmarks(
    search: str | None = Query(default=None),
    folder_id: int | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Bookmark]:
    query = select(Bookmark).order_by(Bookmark.created_at.desc())
    if folder_id is not None:
        query = query.where(Bookmark.folder_id == folder_id)
    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Bookmark.title.ilike(term),
                Bookmark.url.ilike(term),
                Bookmark.description.ilike(term),
                Bookmark.tags.ilike(term),
                Bookmark.summary.ilike(term),
            )
        )
    return list(db.scalars(query.offset(offset).limit(limit)).all())


@app.post("/api/bookmarks", response_model=BookmarkRead, status_code=201)
def create_bookmark(payload: BookmarkCreate, db: Session = Depends(get_db)) -> Bookmark:
    if payload.folder_id:
        ensure_folder_exists(payload.folder_id, db)
    if find_bookmark_by_normalized_url(payload.url, db):
        raise HTTPException(status_code=409, detail="This bookmark already exists")
    bookmark = Bookmark(**payload.model_dump())
    enrich_bookmark(bookmark)
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@app.patch("/api/bookmarks/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(
    bookmark_id: int,
    payload: BookmarkUpdate,
    db: Session = Depends(get_db),
) -> Bookmark:
    bookmark = ensure_bookmark_exists(bookmark_id, db)
    if payload.folder_id:
        ensure_folder_exists(payload.folder_id, db)
    if payload.url:
        duplicate = find_bookmark_by_normalized_url(payload.url, db, exclude_id=bookmark_id)
        if duplicate:
            raise HTTPException(status_code=409, detail="This bookmark already exists")
    fields = payload.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(bookmark, field, value)
    if "tags" not in fields and "summary" not in fields:
        enrich_bookmark(bookmark)
    else:
        bookmark.favicon_url = bookmark.favicon_url or favicon_url(bookmark.url)
        bookmark.thumbnail_url = bookmark.thumbnail_url or thumbnail_url(bookmark.url)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@app.delete("/api/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)) -> Response:
    bookmark = ensure_bookmark_exists(bookmark_id, db)
    db.delete(bookmark)
    db.commit()
    return Response(status_code=204)


@app.delete("/api/library", response_model=ResetSummary)
def reset_library(db: Session = Depends(get_db)) -> ResetSummary:
    bookmarks_deleted = len(db.scalars(select(Bookmark.id)).all())
    folders_deleted = len(db.scalars(select(Folder.id)).all())
    db.execute(delete(Bookmark))
    db.execute(delete(Folder))
    db.commit()
    return ResetSummary(
        folders_deleted=folders_deleted,
        bookmarks_deleted=bookmarks_deleted,
    )


@app.post("/api/ai/enrich", response_model=AIEnrichSummary)
def enrich_all_bookmarks(db: Session = Depends(get_db)) -> AIEnrichSummary:
    bookmarks = list(db.scalars(select(Bookmark)).all())
    for bookmark in bookmarks:
        enrich_bookmark(bookmark)
    db.commit()
    return AIEnrichSummary(bookmarks_updated=len(bookmarks))


@app.get("/api/ai/status", response_model=AIModelStatus)
def ai_status() -> AIModelStatus:
    return AIModelStatus(
        name="Bundled Tiny Bookmark Model",
        mode="local-offline",
        external_api_required=False,
    )


@app.post("/api/ai/bookmarks/{bookmark_id}/enrich", response_model=BookmarkRead)
def enrich_one_bookmark(bookmark_id: int, db: Session = Depends(get_db)) -> Bookmark:
    bookmark = ensure_bookmark_exists(bookmark_id, db)
    enrich_bookmark(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@app.post("/api/ai/auto-categorize", response_model=AIEnrichSummary)
def auto_categorize_bookmarks(db: Session = Depends(get_db)) -> AIEnrichSummary:
    folders = list(db.scalars(select(Folder)).all())
    bookmarks = list(db.scalars(select(Bookmark)).all())
    moved = 0

    for bookmark in bookmarks:
        enrich_bookmark(bookmark)
        category = suggest_category(bookmark)
        folder = find_best_folder(category, folders)
        if folder is None:
            folder = Folder(name=category, sort_order=len(folders))
            db.add(folder)
            db.flush()
            folders.append(folder)
        if bookmark.folder_id != folder.id:
            bookmark.folder_id = folder.id
            moved += 1

    db.commit()
    return AIEnrichSummary(bookmarks_updated=moved)


@app.get("/api/ai/semantic-search", response_model=list[SemanticSearchResult])
def semantic_search(
    query: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict]:
    bookmarks = list(db.scalars(select(Bookmark)).all())
    scored = [
        {"bookmark": bookmark, "score": semantic_score(query, bookmark)}
        for bookmark in bookmarks
    ]
    return [
        item
        for item in sorted(scored, key=lambda result: result["score"], reverse=True)
        if item["score"] > 0
    ][:limit]


@app.get("/api/ai/duplicates", response_model=list[DuplicateGroup])
def find_duplicates(db: Session = Depends(get_db)) -> list[dict]:
    bookmarks = list(db.scalars(select(Bookmark).order_by(Bookmark.created_at.desc())).all())
    return [
        {"reason": reason, "bookmarks": items}
        for reason, items in duplicate_groups(bookmarks)
    ]


@app.post("/api/import", response_model=ImportSummary)
async def import_bookmarks(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ImportSummary:
    raw = await file.read()
    parsed = parse_bookmarks_html(raw.decode("utf-8", errors="ignore"))
    existing_urls = {
        normalize_url(bookmark.url)
        for bookmark in db.scalars(select(Bookmark)).all()
    }
    summary = {"folders_created": 0, "bookmarks_created": 0, "skipped_duplicates": 0}
    import_folder_children(parsed, None, db, summary, existing_urls)
    db.commit()
    return ImportSummary(**summary)


@app.get("/api/export")
def export_bookmarks(db: Session = Depends(get_db)) -> Response:
    folders = db.scalars(
        select(Folder)
        .options(selectinload(Folder.children), selectinload(Folder.bookmarks))
        .order_by(Folder.name)
    ).all()
    bookmarks = db.scalars(
        select(Bookmark).where(Bookmark.folder_id.is_(None)).order_by(Bookmark.title)
    ).all()

    folder_payload = build_export_tree(list(folders))
    bookmark_payload = [{"title": item.title, "url": item.url} for item in bookmarks]
    html = render_bookmarks_html(folder_payload, bookmark_payload)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="bookmarks.html"'},
    )


def ensure_folder_exists(folder_id: int, db: Session) -> Folder:
    folder = db.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


def ensure_bookmark_exists(bookmark_id: int, db: Session) -> Bookmark:
    bookmark = db.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return bookmark


def find_bookmark_by_normalized_url(
    url: str,
    db: Session,
    exclude_id: int | None = None,
) -> Bookmark | None:
    normalized = normalize_url(url)
    bookmarks = db.scalars(select(Bookmark)).all()
    for bookmark in bookmarks:
        if exclude_id is not None and bookmark.id == exclude_id:
            continue
        if normalize_url(bookmark.url) == normalized:
            return bookmark
    return None


def find_or_create_folder(
    name: str,
    parent_id: int | None,
    db: Session,
    summary: dict[str, int],
) -> Folder:
    existing = db.scalar(
        select(Folder).where(Folder.name == name, Folder.parent_id == parent_id)
    )
    if existing:
        return existing
    folder = Folder(name=name, parent_id=parent_id)
    db.add(folder)
    db.flush()
    summary["folders_created"] += 1
    return folder


def import_folder_children(
    parsed_folder: ParsedFolder,
    parent_id: int | None,
    db: Session,
    summary: dict[str, int],
    existing_urls: set[str],
) -> None:
    for child in parsed_folder.folders:
        folder = find_or_create_folder(child.name, parent_id, db, summary)
        import_folder_children(child, folder.id, db, summary, existing_urls)

    for item in parsed_folder.bookmarks:
        normalized = normalize_url(item.url)
        if normalized in existing_urls:
            summary["skipped_duplicates"] += 1
            continue
        bookmark = Bookmark(title=item.title, url=item.url, folder_id=parent_id)
        enrich_bookmark(bookmark)
        db.add(bookmark)
        existing_urls.add(normalized)
        summary["bookmarks_created"] += 1


def build_export_tree(folders: list[Folder]) -> list[dict]:
    nodes = {
        folder.id: {
            "id": folder.id,
            "name": folder.name,
            "children": [],
            "bookmarks": [
                {"title": bookmark.title, "url": bookmark.url}
                for bookmark in sorted(folder.bookmarks, key=lambda item: item.title.lower())
            ],
        }
        for folder in folders
    }
    roots = []
    for folder in folders:
        node = nodes[folder.id]
        if folder.parent_id and folder.parent_id in nodes:
            nodes[folder.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def ensure_sqlite_schema() -> None:
    with engine.begin() as connection:
        folder_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(folders)")).fetchall()
        }
        bookmark_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(bookmarks)")).fetchall()
        }

        if "sort_order" not in folder_columns:
            connection.execute(text("ALTER TABLE folders ADD COLUMN sort_order INTEGER DEFAULT 0"))

        for column in ["tags", "summary", "favicon_url", "thumbnail_url"]:
            if column not in bookmark_columns:
                connection.execute(text(f"ALTER TABLE bookmarks ADD COLUMN {column} TEXT"))


ensure_sqlite_schema()
