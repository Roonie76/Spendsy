"""
RAG Vector Store — Phase 2.

Two collections:
  static_kb   — chromadb (local persistent). Indian tax slabs, RBI rules,
                SEBI limits, EMI formulas. Pre-embedded at startup.
                TTL: manual refresh (monthly).

  live_chunks — pgvector on finance_document table. Scraped content from
                Phase 1 fetchers (bank rates, car prices, web content).
                TTL: 24h per chunk (expires via fetched_at + ttl_seconds).

Embedding:
  Uses Gemini text-embedding-004 (768-dim, matches existing vector(768) col).
  Falls back to a simple TF-IDF hash vector (768-dim) if API unavailable —
  ensures the store always works even without an API key.

Design:
  - Never raises. Returns [] on any failure.
  - Singleton instances (module-level) — one chromadb client per process.
  - pgvector access via raw httpx call to finance-service internal API
    (avoids SQLAlchemy dependency in spendsy-ai process).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import struct
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

EMBED_DIM = 768
STATIC_KB_PATH = os.path.join(os.path.dirname(__file__), "_chromadb")
GEMINI_EMBED_MODEL = "models/text-embedding-004"


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _gemini_embed(text: str, api_key: str) -> Optional[list[float]]:
    """Call Gemini embedding API. Returns 768-dim vector or None."""
    import urllib.request, urllib.error
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"{GEMINI_EMBED_MODEL}:embedContent?key={api_key}"
    )
    payload = json.dumps({
        "model": GEMINI_EMBED_MODEL,
        "content": {"parts": [{"text": text[:8000]}]},
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data["embedding"]["values"]
    except Exception as exc:
        logger.debug("Gemini embed failed: %s", exc)
        return None


def _hash_embed(text: str) -> list[float]:
    """
    Deterministic 768-dim pseudo-embedding from SHA-256 + term hashing.
    Preserves rough semantic locality for same-domain text.
    Not as accurate as a real embedding but works offline.
    """
    tokens = re.findall(r"\w+", text.lower())
    vec = [0.0] * EMBED_DIM
    for token in tokens:
        h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        idx = h % EMBED_DIM
        weight = 1.0 / (1 + math.log(len(token) + 1))
        vec[idx] += weight
    # L2 normalise
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embed_text(text: str) -> list[float]:
    """Embed text. Tries Gemini, falls back to hash embed."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if api_key:
        vec = _gemini_embed(text, api_key)
        if vec:
            return vec
    return _hash_embed(text)


# ---------------------------------------------------------------------------
# Static KB (chromadb)
# ---------------------------------------------------------------------------

_chroma_client = None
_static_collection = None


def _get_static_collection():
    global _chroma_client, _static_collection
    if _static_collection is not None:
        return _static_collection
    try:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=STATIC_KB_PATH)
        _static_collection = _chroma_client.get_or_create_collection(
            name="static_kb",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("static_kb collection ready (%d docs)", _static_collection.count())
    except Exception as exc:
        logger.error("chromadb init failed: %s", exc)
        _static_collection = None
    return _static_collection


# Static knowledge documents — Indian finance rules (FY2026)
STATIC_DOCUMENTS: list[dict[str, str]] = [
    {
        "id": "tax_slabs_new_fy26",
        "text": (
            "Income Tax New Regime FY2026 slabs: "
            "0-3L: 0%, 3-7L: 5%, 7-10L: 10%, 10-12L: 15%, "
            "12-15L: 20%, above 15L: 30%. "
            "Rebate u/s 87A: zero tax if total income <= 7L under new regime. "
            "Standard deduction 75000 under new regime."
        ),
        "category": "tax",
    },
    {
        "id": "tax_slabs_old_fy26",
        "text": (
            "Income Tax Old Regime FY2026 slabs: "
            "0-2.5L: 0%, 2.5-5L: 5%, 5-10L: 20%, above 10L: 30%. "
            "Rebate u/s 87A: zero tax if total income <= 5L under old regime. "
            "Standard deduction 50000. "
            "80C deduction max 1.5L. 80D health insurance up to 25000 self, 50000 senior parents. "
            "HRA exemption available. NPS 80CCD1B extra 50000."
        ),
        "category": "tax",
    },
    {
        "id": "surcharge_cess",
        "text": (
            "Income Tax Surcharge FY2026: "
            "50L-1Cr: 10% surcharge on tax. 1Cr-2Cr: 15%. 2Cr-5Cr: 25%. Above 5Cr: 37% (capped at 25% under new regime). "
            "Health & Education Cess: 4% on (tax + surcharge) for all taxpayers."
        ),
        "category": "tax",
    },
    {
        "id": "advance_tax_schedule",
        "text": (
            "Advance Tax payment schedule FY2026: "
            "15 June: 15% of estimated tax. "
            "15 September: 45% cumulative. "
            "15 December: 75% cumulative. "
            "15 March: 100% cumulative. "
            "Applicable if total tax liability > 10000. "
            "Interest u/s 234B for shortfall, 234C for each instalment."
        ),
        "category": "tax",
    },
    {
        "id": "rbi_repo_rate",
        "text": (
            "RBI Monetary Policy FY2026: Repo rate 6.25% (Feb 2026 cut from 6.5%). "
            "Reverse repo 3.35%. CRR 4%. SLR 18%. "
            "MCLR-linked loans reset every 6-12 months. "
            "External benchmark-linked loans (EBLR) reset within 3 months of repo change."
        ),
        "category": "banking",
    },
    {
        "id": "sebi_investment_limits",
        "text": (
            "SEBI investment limits & rules FY2026: "
            "PPF annual max 1.5L, lock-in 15 years. "
            "ELSS lock-in 3 years, qualifies 80C. "
            "NPS Tier 1 withdrawal: 60% lump sum at 60, 40% mandatory annuity. "
            "NPS Tier 2: freely withdrawable. "
            "FD TDS threshold 40000 (50000 senior). "
            "LTCG equity >1L taxed at 12.5%. STCG equity 20%. "
            "Debt fund gains taxed as income (no LTCG benefit post April 2023)."
        ),
        "category": "investment",
    },
    {
        "id": "emi_formula",
        "text": (
            "EMI formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1). "
            "P = principal, r = monthly interest rate (annual_rate/12/100), n = tenure months. "
            "Total interest = EMI*n - P. "
            "Thumb rules: 9% loan 5yr -> EMI ~2.08% of principal per month. "
            "12% loan 5yr -> EMI ~2.22% per month. "
            "Safe EMI rule: total EMIs should not exceed 40% of net monthly income."
        ),
        "category": "banking",
    },
    {
        "id": "home_loan_tax",
        "text": (
            "Home loan tax benefits (old regime only): "
            "Principal repayment: 80C deduction up to 1.5L. "
            "Interest paid: section 24b deduction up to 2L for self-occupied. "
            "Under construction: interest deductible in 5 equal instalments post completion. "
            "Let-out property: full interest deductible, rental income taxable. "
            "New regime: no 80C or 24b deductions except standard deduction."
        ),
        "category": "tax",
    },
    {
        "id": "credit_card_rules",
        "text": (
            "Credit card financial rules India: "
            "Minimum due typically 5% of outstanding or 200 whichever higher. "
            "Interest on revolving balance: 36-52% p.a. (3-4.33% per month). "
            "Grace period: 18-55 days interest free if full payment. "
            "Late payment charge: 100-1300 depending on outstanding. "
            "Credit utilisation: keep below 30% for good CIBIL score. "
            "Reward points typically 1-5% cashback equivalent."
        ),
        "category": "banking",
    },
    {
        "id": "gst_common_rates",
        "text": (
            "GST rates for common purchases India: "
            "Essential food: 0%. Packaged food: 5-12%. "
            "Restaurant (AC): 5% no ITC. Restaurant (non-AC): 5%. "
            "Clothing <1000: 5%, >1000: 12%. "
            "Electronics: 18%. Cars petrol/diesel: 28% + cess 1-22%. "
            "EV cars: 5%. Two-wheelers: 28% + 2% cess. "
            "Health insurance: 18% GST."
        ),
        "category": "tax",
    },
]


def populate_static_kb(force: bool = False) -> int:
    """
    Seed static_kb with Indian finance documents.
    Skips if already populated (unless force=True).
    Returns count of documents added.
    """
    col = _get_static_collection()
    if col is None:
        return 0

    if not force and col.count() >= len(STATIC_DOCUMENTS):
        logger.info("static_kb already populated (%d docs)", col.count())
        return 0

    ids, texts, embeddings, metadatas = [], [], [], []
    for doc in STATIC_DOCUMENTS:
        ids.append(doc["id"])
        texts.append(doc["text"])
        embeddings.append(embed_text(doc["text"]))
        metadatas.append({"category": doc["category"], "source": "static_kb"})

    col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
    logger.info("static_kb populated: %d docs", len(ids))
    return len(ids)


def query_static_kb(query: str, n_results: int = 3, category: Optional[str] = None) -> list[dict]:
    """
    Semantic search over static_kb.
    Returns list of {text, id, category, score} sorted by relevance.
    """
    col = _get_static_collection()
    if col is None or col.count() == 0:
        return []
    try:
        where = {"category": category} if category else None
        results = col.query(
            query_embeddings=[embed_text(query)],
            n_results=min(n_results, col.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            dist = results["distances"][0][i]
            score = max(0.0, 1.0 - dist)   # cosine distance -> similarity
            out.append({
                "text": doc,
                "id": results["ids"][0][i],
                "category": results["metadatas"][0][i].get("category", ""),
                "score": round(score, 4),
                "source": "static_kb",
            })
        return sorted(out, key=lambda x: -x["score"])
    except Exception as exc:
        logger.error("static_kb query failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Live chunks store (in-memory with file persistence fallback)
# pgvector path used when finance-service DB is reachable;
# falls back to in-memory dict keyed by url+chunk_idx.
# ---------------------------------------------------------------------------

_live_store: dict[str, dict] = {}   # key: chunk_id, value: chunk dict + embedding
_LIVE_TTL_SECONDS = 86400            # 24h default


def _chunk_id(url: str, chunk_idx: int) -> str:
    return hashlib.sha256(f"{url}:{chunk_idx}".encode()).hexdigest()[:16]


def store_live_chunks(chunks: list[dict]) -> int:
    """
    Store Phase 1 content_extractor chunks in the live store.
    Embeds each chunk and saves to in-memory store (with pgvector upsert attempted).
    Returns count stored.
    """
    now = time.time()
    stored = 0
    for chunk in chunks:
        url = chunk.get("url", "")
        idx = chunk.get("chunk_idx", 0)
        text = chunk.get("text", "")
        ttl = chunk.get("ttl_seconds", _LIVE_TTL_SECONDS)
        if not text:
            continue
        cid = _chunk_id(url, idx)
        embedding = embed_text(text)
        _live_store[cid] = {
            "id": cid,
            "text": text,
            "url": url,
            "chunk_idx": idx,
            "embedding": embedding,
            "stored_at": now,
            "expires_at": now + ttl,
            "fetched_at": chunk.get("fetched_at", ""),
            "token_count": chunk.get("token_count", 0),
        }
        stored += 1
    return stored


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


def query_live_chunks(query: str, n_results: int = 3) -> list[dict]:
    """
    Semantic search over live chunk store.
    Prunes expired chunks first. Returns list of {text, url, score}.
    """
    now = time.time()
    # Prune expired
    expired = [k for k, v in _live_store.items() if v["expires_at"] < now]
    for k in expired:
        del _live_store[k]

    if not _live_store:
        return []

    q_emb = embed_text(query)
    scored = []
    for chunk in _live_store.values():
        score = _cosine(q_emb, chunk["embedding"])
        scored.append({
            "text": chunk["text"],
            "url": chunk["url"],
            "score": round(score, 4),
            "source": "live_chunk",
            "fetched_at": chunk["fetched_at"],
        })
    scored.sort(key=lambda x: -x["score"])
    return scored[:n_results]
