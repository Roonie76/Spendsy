"""
Content Extractor — Phase 1 of Obscura web intelligence layer.

Turns raw HTML (from ObscuraClient.scrape or any fetch) into clean,
chunked text suitable for context injection or RAG indexing.

Pipeline:
  raw_html → trafilatura extraction → strip boilerplate
           → split into token-bounded chunks
           → tag each chunk with {url, fetched_at, chunk_idx, token_count}

Design rules:
  - Never raises. Returns [] on any failure so callers stay clean.
  - Chunks are 400 tokens max (Gemini 1.5 Flash context budget friendly).
  - Overlap: 50 tokens between adjacent chunks to preserve sentence continuity.
  - Metadata attached per-chunk so RAG indexer can store without re-joining.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Target / overlap sizes in approximate tokens (1 token ≈ 4 chars for English)
CHUNK_TOKENS = 400
OVERLAP_TOKENS = 50
CHARS_PER_TOKEN = 4
CHUNK_CHARS = CHUNK_TOKENS * CHARS_PER_TOKEN       # 1600 chars
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN   # 200 chars

# Noise patterns to strip after extraction
_NOISE_RE = re.compile(
    r"(cookie\s+policy|accept\s+cookies|subscribe\s+to\s+newsletter"
    r"|follow\s+us\s+on|share\s+this\s+article|advertisement"
    r"|sponsored\s+content|terms\s+of\s+use|privacy\s+policy"
    r"|all\s+rights\s+reserved)",
    re.IGNORECASE,
)


def _extract_text(html: str) -> str:
    """
    Use trafilatura for main-content extraction.
    Falls back to a simple tag-strip regex if trafilatura unavailable.
    """
    try:
        import trafilatura  # type: ignore

        text = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            include_images=False,
            no_fallback=False,
        )
        if text:
            return text
    except Exception as exc:
        logger.debug("trafilatura failed: %s", exc)

    # Minimal fallback: strip all HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _clean(text: str) -> str:
    """Remove noise lines and normalise whitespace."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if _NOISE_RE.search(line):
            continue
        if len(line) < 20:          # skip stray nav/breadcrumb fragments
            continue
        lines.append(line)
    return "\n".join(lines)


def _split_chunks(text: str, url: str, fetched_at: str) -> list[dict[str, Any]]:
    """
    Slide a window of CHUNK_CHARS with OVERLAP_CHARS overlap over `text`.
    Each chunk dict: {text, url, fetched_at, chunk_idx, token_count}.
    """
    if not text:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + CHUNK_CHARS
        chunk_text = text[start:end]

        # Try to end on sentence boundary within last 200 chars
        if end < len(text):
            boundary = chunk_text.rfind(". ", len(chunk_text) - 200)
            if boundary != -1:
                end = start + boundary + 2  # include the period + space
                chunk_text = text[start:end]

        token_count = max(1, len(chunk_text) // CHARS_PER_TOKEN)
        chunks.append(
            {
                "text": chunk_text.strip(),
                "url": url,
                "fetched_at": fetched_at,
                "chunk_idx": idx,
                "token_count": token_count,
            }
        )

        idx += 1
        # Advance by chunk size minus overlap
        start = end - OVERLAP_CHARS
        if start <= 0:
            break

    return chunks


def extract_chunks(
    html: str,
    url: str = "",
    fetched_at: str | None = None,
) -> list[dict[str, Any]]:
    """
    Main entry point.

    Args:
        html:       Raw HTML string from Obscura or any HTTP fetch.
        url:        Source URL (for provenance tagging).
        fetched_at: ISO timestamp string. Defaults to now (UTC).

    Returns:
        List of chunk dicts, empty on failure.
    """
    if not html:
        return []

    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()

    try:
        raw_text = _extract_text(html)
        clean_text = _clean(raw_text)
        chunks = _split_chunks(clean_text, url, fetched_at)
        logger.info(
            "content_extractor: %d chunks from %s (%d chars)",
            len(chunks),
            url or "<inline>",
            len(clean_text),
        )
        return chunks
    except Exception as exc:
        logger.error("content_extractor failed for %s: %s", url, exc)
        return []


def extract_chunks_from_scrape_result(
    scrape_result: dict[str, Any],
    url: str = "",
    fetched_at: str | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience wrapper for ObscuraClient.scrape() output.

    ObscuraClient returns {selector_key: text_or_None, ...}.
    This joins all non-None values and passes through extract_chunks.
    Handles both raw-HTML and already-extracted-text responses.
    """
    if not scrape_result or "error" in scrape_result:
        return []

    combined = "\n\n".join(
        str(v) for v in scrape_result.values() if v is not None
    )
    # If it looks like plain text (no angle brackets), skip extraction step
    if "<" not in combined:
        fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
        clean_text = _clean(combined)
        return _split_chunks(clean_text, url, fetched_at)

    return extract_chunks(combined, url=url, fetched_at=fetched_at)
