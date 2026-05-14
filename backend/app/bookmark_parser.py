from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser


@dataclass
class ParsedBookmark:
    title: str
    url: str


@dataclass
class ParsedFolder:
    name: str
    folders: list["ParsedFolder"] = field(default_factory=list)
    bookmarks: list[ParsedBookmark] = field(default_factory=list)


class NetscapeBookmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = ParsedFolder(name="Imported")
        self._stack = [self.root]
        self._pending_folder: ParsedFolder | None = None
        self._capture: str | None = None
        self._text: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "h3":
            self._capture = "folder"
            self._text = []
        elif tag == "a":
            self._capture = "bookmark"
            self._text = []
            self._href = dict(attrs).get("href")
        elif tag == "dl" and self._pending_folder is not None:
            self._stack.append(self._pending_folder)
            self._pending_folder = None

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h3" and self._capture == "folder":
            name = self._clean_text()
            if name:
                folder = ParsedFolder(name=name)
                self._stack[-1].folders.append(folder)
                self._pending_folder = folder
            self._reset_capture()
        elif tag == "a" and self._capture == "bookmark":
            title = self._clean_text() or self._href or "Untitled"
            if self._href:
                self._stack[-1].bookmarks.append(ParsedBookmark(title=title, url=self._href))
            self._reset_capture()
        elif tag == "dl" and len(self._stack) > 1:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)

    def _clean_text(self) -> str:
        return " ".join("".join(self._text).split())

    def _reset_capture(self) -> None:
        self._capture = None
        self._text = []
        self._href = None


def parse_bookmarks_html(content: str) -> ParsedFolder:
    parser = NetscapeBookmarkParser()
    parser.feed(content)
    return parser.root


def render_bookmarks_html(folders: list[dict], bookmarks: list[dict]) -> str:
    def render_folder(folder: dict) -> str:
        children = "\n".join(render_folder(child) for child in folder["children"])
        links = "\n".join(render_link(bookmark) for bookmark in folder["bookmarks"])
        return (
            f'<DT><H3>{escape(folder["name"])}</H3>\n'
            "<DL><p>\n"
            f"{children}\n{links}\n"
            "</DL><p>"
        )

    def render_link(bookmark: dict) -> str:
        return f'<DT><A HREF="{escape(bookmark["url"], quote=True)}">{escape(bookmark["title"])}</A>'

    top_folders = "\n".join(render_folder(folder) for folder in folders)
    top_links = "\n".join(render_link(bookmark) for bookmark in bookmarks)
    return (
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n'
        "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n"
        "<TITLE>Bookmarks</TITLE>\n"
        "<H1>Bookmarks</H1>\n"
        "<DL><p>\n"
        f"{top_folders}\n{top_links}\n"
        "</DL><p>\n"
    )

