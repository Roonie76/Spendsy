"""
vault_sync.py — Post-session vault synchronization.

Called at the end of every handle_user_question call. Takes the already-fetched
clean_summary and the session's Q&A and writes/updates the relevant vault notes.

Design:
  - Profile and balances: ALWAYS updated (they change every session).
  - Goals, plans, loans: only written if data is present.
  - Conversation: APPENDED to the daily note (multiple Q&A per day).
  - Monthly transactions: written only if the file doesn't exist yet.
  - Canvas: regenerated when structural data (goals/plans) changes.

This function is intentionally fire-and-forget — vault sync failures must
NEVER block the user from getting their AI response. Errors are logged
but swallowed.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from .vault_writer import (
    _read_note,
    _write_note,
    _append_to_note,
    _today,
    _period,
    _safe_filename,
    ensure_vault,
)
from .note_templates import (
    render_balances_note,
    render_canvas,
    render_conversation_entry,
    render_conversation_header,
    render_goal_note,
    render_loan_note,
    render_monthly_transactions_note,
    render_plan_note,
    render_profile_note,
)

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    """Convert a title to a safe filename."""
    safe = name.lower().strip()
    safe = "".join(c if c.isalnum() or c in " _-" else "" for c in safe)
    safe = safe.replace(" ", "_")
    return safe[:60] or "untitled"


async def sync_vault_after_session(
    user_id: int,
    clean_summary: Dict[str, Any],
    question: str,
    answer: Dict[str, Any],
    intent: str,
    user_tier: str = "free",
) -> None:
    """
    Mirror the current financial state into the user's Obsidian vault.

    Called at the end of every TORA session. Non-blocking — failures are
    logged but never propagated to the user.
    """
    try:
        vault = ensure_vault(user_id)
        today = _today()
        period = _period()

        # ── Always update (these change every session) ────────────────────
        _write_note(
            vault, "00_profile/overview.md",
            render_profile_note(user_id, clean_summary, user_tier),
        )
        _write_note(
            vault, "01_accounts/balances.md",
            render_balances_note(user_id, clean_summary),
        )

        # ── Append conversation entry to today's note ─────────────────────
        conv_path = f"05_conversations/{today}.md"
        existing = _read_note(vault / conv_path)
        if not existing:
            # First conversation of the day — write header
            _write_note(vault, conv_path, render_conversation_header(today, intent))

        _append_to_note(
            vault, conv_path,
            render_conversation_entry(question, answer, clean_summary, intent),
        )

        # ── Conditional: goals ────────────────────────────────────────────
        for goal in clean_summary.get("goals", []):
            name = _safe_filename(goal.get("title", "untitled"))
            _write_note(vault, f"03_goals/{name}.md", render_goal_note(goal))

        # ── Conditional: plans ────────────────────────────────────────────
        for plan in clean_summary.get("plans", []):
            name = _safe_filename(plan.get("title", "untitled"))
            _write_note(vault, f"04_plans/{name}.md", render_plan_note(plan))

        # ── Conditional: loans ────────────────────────────────────────────
        for loan in clean_summary.get("loans", []):
            title = loan.get("title", loan.get("bank", "loan"))
            name = _safe_filename(title)
            _write_note(vault, f"01_accounts/loans/{name}.md", render_loan_note(loan))

        # ── Monthly transactions (only if file doesn't exist yet) ─────────
        monthly_path = f"02_transactions/{period}.md"
        if not (vault / monthly_path).exists():
            _write_note(
                vault, monthly_path,
                render_monthly_transactions_note(period, clean_summary),
            )

        # ── Canvas (regenerate when structural data changes) ──────────────
        _write_note(vault, "financial_map.canvas", render_canvas(clean_summary))

        logger.info(f"Vault synced for user {user_id} ({today})")

    except Exception as e:
        # Fire-and-forget — vault sync must never break the user experience
        logger.error(f"Vault sync failed for user {user_id}: {e}", exc_info=True)


def read_vault_context(user_id: int) -> str:
    """
    Read the user's vault profile as prose context for the LLM prompt.

    Returns the profile note content if the vault exists, empty string otherwise.
    This is the key optimization: structured prose with ₹ amounts already
    formatted beats raw JSON for gemma4:e2b accuracy.
    """
    from .vault_writer import _vault_root

    vault = _vault_root(user_id)
    profile_path = vault / "00_profile" / "overview.md"
    today_conv_path = vault / "05_conversations" / f"{_today()}.md"

    context = ""

    # Profile note — the primary financial context
    profile_md = _read_note(profile_path)
    if profile_md:
        # Strip frontmatter for the LLM (it only needs the prose)
        lines = profile_md.split("\n")
        in_frontmatter = False
        body_lines = []
        for line in lines:
            if line.strip() == "---":
                in_frontmatter = not in_frontmatter
                continue
            if not in_frontmatter:
                body_lines.append(line)
        context += "\n".join(body_lines).strip()

    # Today's conversation — for follow-up resolution
    conv_md = _read_note(today_conv_path)
    if conv_md:
        # Only include the last 2000 chars to keep tokens reasonable
        stripped = _strip_frontmatter(conv_md)
        if len(stripped) > 2000:
            stripped = "..." + stripped[-2000:]
        if stripped.strip():
            context += "\n\n=== TODAY'S EARLIER CONVERSATIONS ===\n"
            context += stripped

    return context


def _strip_frontmatter(md: str) -> str:
    """Remove YAML frontmatter from a markdown string."""
    lines = md.split("\n")
    in_fm = False
    result = []
    for line in lines:
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if not in_fm:
            result.append(line)
    return "\n".join(result)
