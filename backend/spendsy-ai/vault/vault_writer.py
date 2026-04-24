"""
vault_writer.py — Core file operations for per-user Obsidian vaults.

Each user gets a folder of plain .md files that TORA generates and updates.
The vault does three things the DB-backed memory can't:
  1. Every note links to every other related note using [[wikilinks]].
  2. The vault is the single source of truth TORA injects into the prompt
     instead of raw JSON — structured prose beats JSON for 2B models.
  3. Users can download, open, and read their entire financial history
     in any markdown editor. Zero lock-in.

This module ONLY writes. TORA reads from the existing MCP/DB pipeline;
the vault writer mirrors those results as markdown.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config import settings

logger = logging.getLogger(__name__)

# ─── Vault root ───────────────────────────────────────────────────────────────

def _vault_root(user_id: int) -> Path:
    """Return the root directory for a user's vault."""
    base = getattr(settings, "vault_base_path", "/data/vaults")
    return Path(base) / f"user_{user_id}"


# ─── Skeleton ─────────────────────────────────────────────────────────────────

# Folder skeleton — mirrors the note taxonomy.
_FOLDERS = [
    "00_profile",
    "01_accounts",
    "01_accounts/loans",
    "01_accounts/credit_cards",
    "02_transactions",
    "03_goals",
    "04_plans",
    "05_conversations",
    "06_insights",
    "07_simulations",
    "08_templates",
]


def ensure_vault(user_id: int) -> Path:
    """Create the folder skeleton if it doesn't exist. Idempotent."""
    root = _vault_root(user_id)
    for folder in _FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    logger.info(f"Vault ensured for user {user_id} at {root}")
    return root


# ─── Atomic write ─────────────────────────────────────────────────────────────

def _write_note(vault: Path, relative_path: str, content: str) -> Path:
    """Write *content* to *vault / relative_path*, creating parents."""
    target = vault / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    logger.debug(f"Wrote vault note: {target}")
    return target


def _read_note(path: Path, default: str = "") -> str:
    """Read a vault note. Returns *default* if the file doesn't exist."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def _append_to_note(vault: Path, relative_path: str, content: str) -> Path:
    """Append *content* to an existing note (or create it)."""
    target = vault / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(content)
    return target


# ─── Formatting helpers ──────────────────────────────────────────────────────

def _fmt_currency(amount: float | int) -> str:
    """Format a number as ₹X,XX,XXX.XX (Indian numbering)."""
    if amount is None:
        return "₹0.00"
    return f"₹{float(amount):,.2f}"


def _frontmatter(fields: Dict[str, Any]) -> str:
    """Render a YAML frontmatter block."""
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(i) for i in v)}]")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _wikilink(path: str) -> str:
    """Return an Obsidian wikilink: [[path]]."""
    return f"[[{path}]]"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _period() -> str:
    return datetime.now().strftime("%Y-%m")


def _safe_filename(name: str) -> str:
    """Convert a title to a safe filename (lowercase, underscores)."""
    safe = name.lower().strip()
    safe = "".join(c if c.isalnum() or c in " _-" else "" for c in safe)
    safe = safe.replace(" ", "_")
    return safe[:60] or "untitled"
