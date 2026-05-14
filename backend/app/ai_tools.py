import math
import re
from collections import Counter, defaultdict
from urllib.parse import quote, urlparse

from .models import Bookmark, Folder


CATEGORY_KEYWORDS = {
    "Development": {
        "api",
        "code",
        "css",
        "developer",
        "docs",
        "fastapi",
        "framework",
        "github",
        "javascript",
        "python",
        "react",
        "typescript",
    },
    "Design": {"color", "design", "figma", "font", "icons", "inspiration", "ui", "ux"},
    "AI": {"ai", "chatgpt", "embedding", "llm", "machine", "model", "openai", "prompt"},
    "Learning": {"course", "guide", "learn", "lesson", "reference", "tutorial"},
    "News": {"article", "blog", "daily", "news", "newsletter"},
    "Tools": {"app", "converter", "generator", "productivity", "tool", "utility"},
    "Shopping": {"buy", "cart", "deal", "price", "product", "shop", "store"},
    "Reading": {"book", "essay", "paper", "read", "research", "story"},
}

STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "for",
    "from",
    "how",
    "into",
    "more",
    "not",
    "the",
    "this",
    "to",
    "with",
    "www",
    "you",
    "your",
}


def enrich_bookmark(bookmark: Bookmark) -> None:
    domain = get_domain(bookmark.url)
    text = bookmark_text(bookmark)
    tags = generate_tags(text, domain)
    bookmark.tags = ", ".join(tags)
    bookmark.summary = generate_summary(bookmark, domain, tags)
    bookmark.favicon_url = favicon_url(bookmark.url)
    bookmark.thumbnail_url = thumbnail_url(bookmark.url)


def suggest_category(bookmark: Bookmark) -> str:
    text_tokens = set(tokenize(bookmark_text(bookmark)))
    scores = {
        category: len(text_tokens.intersection(keywords))
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_category
    domain = get_domain(bookmark.url).split(".")[0].title()
    return domain or "Unsorted"


def find_best_folder(category: str, folders: list[Folder]) -> Folder | None:
    category_key = category.lower()
    for folder in folders:
        if folder.name.lower() == category_key:
            return folder
    return None


def semantic_score(query: str, bookmark: Bookmark) -> float:
    query_vector = vectorize(query)
    bookmark_vector = vectorize(bookmark_text(bookmark))
    return cosine_similarity(query_vector, bookmark_vector)


def duplicate_groups(bookmarks: list[Bookmark]) -> list[tuple[str, list[Bookmark]]]:
    by_url: dict[str, list[Bookmark]] = defaultdict(list)
    by_title_domain: dict[str, list[Bookmark]] = defaultdict(list)

    for bookmark in bookmarks:
        normalized = normalize_url(bookmark.url)
        by_url[normalized].append(bookmark)
        by_title_domain[f"{slugify(bookmark.title)}::{get_domain(bookmark.url)}"].append(bookmark)

    groups: list[tuple[str, list[Bookmark]]] = []
    seen: set[int] = set()
    for items in by_url.values():
        if len(items) > 1:
            groups.append(("Same URL", items))
            seen.update(item.id for item in items)

    for items in by_title_domain.values():
        ids = {item.id for item in items}
        if len(items) > 1 and not ids.issubset(seen):
            groups.append(("Similar title and domain", items))
            seen.update(ids)

    return groups


def bookmark_text(bookmark: Bookmark) -> str:
    return " ".join(
        part
        for part in [
            bookmark.title,
            bookmark.url,
            bookmark.description or "",
            bookmark.tags or "",
            bookmark.summary or "",
        ]
        if part
    )


def generate_tags(text: str, domain: str) -> list[str]:
    tokens = [token for token in tokenize(text) if token not in STOP_WORDS and len(token) > 2]
    counts = Counter(tokens)
    tags = [token for token, _ in counts.most_common(5)]
    if domain:
        domain_tag = domain.split(".")[0]
        if domain_tag and domain_tag not in tags:
            tags.insert(0, domain_tag)
    return tags[:6]


def generate_summary(bookmark: Bookmark, domain: str, tags: list[str]) -> str:
    base = bookmark.description.strip() if bookmark.description else ""
    if base:
        summary = base[:180].rstrip()
        return summary if len(base) <= 180 else f"{summary}..."
    tag_text = ", ".join(tags[:3]) if tags else "general reference"
    return f"{bookmark.title} from {domain or 'this site'} looks useful for {tag_text}."


def favicon_url(url: str) -> str:
    domain = get_domain(url)
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={quote(domain)}&sz=64"


def thumbnail_url(url: str) -> str:
    return f"https://image.thum.io/get/width/640/crop/360/noanimate/{quote(url, safe=':/?&=%')}"


def get_domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc.lower().removeprefix("www.")


def normalize_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    path = parsed.path.rstrip("/")
    return f"{parsed.netloc.lower().removeprefix('www.')}{path}".lower()


def slugify(value: str) -> str:
    return "-".join(tokenize(value))


def tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def vectorize(value: str) -> Counter[str]:
    return Counter(token for token in tokenize(value) if token not in STOP_WORDS and len(token) > 2)


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left).intersection(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return round(numerator / (left_norm * right_norm), 4)

