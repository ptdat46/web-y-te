"""Safe local document discovery and deterministic lexical retrieval."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {".txt", ".md", ".html", ".htm", ".csv", ".json", ".pdf"}


@dataclass(frozen=True)
class DocumentChunk:
    source: str
    title: str
    text: str
    chunk_id: str
    page: str = ""


def _extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup
        return BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser").get_text("\n")
    if suffix == ".csv":
        with path.open(encoding="utf-8", errors="replace", newline="") as handle:
            return "\n".join(" | ".join(row) for row in csv.reader(handle))
    if suffix == ".json":
        return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return ""


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def discover_chunks(rag_dir: Path, chunk_size: int = 1200, overlap: int = 150) -> list[DocumentChunk]:
    """Load bounded, deterministic chunks. Missing or unreadable files are skipped."""
    chunks: list[DocumentChunk] = []
    if not rag_dir.is_dir():
        return chunks
    step = max(1, chunk_size - min(overlap, chunk_size - 1))
    root = rag_dir.resolve()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED):
        try:
            text = _normalize(_extract(path))
        except (OSError, ValueError, UnicodeError):
            continue
        if not text:
            continue
        relative = path.relative_to(root).as_posix()
        for index, start in enumerate(range(0, len(text), step)):
            piece = text[start:start + chunk_size].strip()
            if not piece:
                continue
            digest = hashlib.sha256(f"{relative}:{index}:{piece}".encode()).hexdigest()[:16]
            chunks.append(DocumentChunk(relative, path.stem, piece, digest))
    return chunks


def keyword_retrieve(chunks: list[DocumentChunk], query: str, top_k: int = 5) -> list[DocumentChunk]:
    """Return relevant chunks with deterministic tie-breaking and no-match support."""
    terms = {term for term in re.findall(r"[\wÀ-ỹ]+", query.casefold()) if len(term) > 2}
    scored: list[tuple[int, str, DocumentChunk]] = []
    for chunk in chunks:
        haystack = chunk.text.casefold()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, chunk.source, chunk))
    scored.sort(key=lambda item: (-item[0], item[1], item[2].chunk_id))
    return [chunk for _, _, chunk in scored[:max(1, top_k)]]


def format_context(chunks: list[DocumentChunk], limit: int = 12000) -> str:
    """Format retrieved text as explicitly untrusted reference material."""
    sections: list[str] = []
    size = 0
    for chunk in chunks:
        section = f"[{chunk.source}#{chunk.chunk_id}]\n{chunk.text}"
        if size + len(section) + 2 > limit:
            break
        sections.append(section)
        size += len(section) + 2
    return "\n\n".join(sections)
