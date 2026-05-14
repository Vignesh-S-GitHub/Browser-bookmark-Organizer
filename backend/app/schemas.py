from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FolderBase(BaseModel):
    name: str
    parent_id: int | None = None
    sort_order: int = 0


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class FolderRead(FolderBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FolderTree(FolderRead):
    children: list["FolderTree"] = []


class BookmarkBase(BaseModel):
    title: str
    url: str
    description: str | None = None
    tags: str | None = None
    summary: str | None = None
    favicon_url: str | None = None
    thumbnail_url: str | None = None
    folder_id: int | None = None


class BookmarkCreate(BookmarkBase):
    pass


class BookmarkUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    description: str | None = None
    tags: str | None = None
    summary: str | None = None
    favicon_url: str | None = None
    thumbnail_url: str | None = None
    folder_id: int | None = None


class BookmarkRead(BookmarkBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportSummary(BaseModel):
    folders_created: int
    bookmarks_created: int
    skipped_duplicates: int = 0


class ResetSummary(BaseModel):
    folders_deleted: int
    bookmarks_deleted: int


class AIEnrichSummary(BaseModel):
    bookmarks_updated: int


class AIModelStatus(BaseModel):
    name: str
    mode: str
    external_api_required: bool


class DuplicateGroup(BaseModel):
    reason: str
    bookmarks: list[BookmarkRead]


class SemanticSearchResult(BaseModel):
    bookmark: BookmarkRead
    score: float
