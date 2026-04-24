"""
note_templates.py — Typed note generators for every vault document.

Each function produces a complete markdown string with YAML frontmatter.
Frontmatter gives TORA a structured header it can parse in O(1).
Wikilinks mean Obsidian's graph view connects goals → plans → conversations
automatically — the user sees their financial story as a network, not a list.

Design rule: every number that appears in a note must originate from the
clean_summary dict. Never compute or estimate inside the template.
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from .vault_writer import (
    _fmt_currency,
    _frontmatter,
    _today,
    _period,
    _wikilink,
)


# ─── Profile note (00_profile/overview.md) ────────────────────────────────────

def render_profile_note(
    user_id: int,
    summary: Dict[str, Any],
    user_tier: str = "free",
) -> str:
    """Main profile dashboard — always updated every session."""
    income = summary.get("monthly_income", 0) or 0
    expenses = summary.get("monthly_expenses", 0) or 0
    balance = summary.get("account_balance", 0) or 0
    surplus = summary.get("monthly_surplus", 0) or 0
    budget = summary.get("monthly_budget", 0) or 0
    tx_count = len(summary.get("recent_transactions", []))

    goals = summary.get("goals", [])
    plans = summary.get("plans", [])
    loans = summary.get("loans", [])

    fm = _frontmatter({
        "type": "profile",
        "user_id": user_id,
        "tier": user_tier,
        "updated": _today(),
    })

    body = "# Financial Profile\n\n"
    body += f"- Monthly income: {_fmt_currency(income)}\n"
    body += f"- Monthly expenses: {_fmt_currency(expenses)}\n"
    body += f"- Monthly budget: {_fmt_currency(budget)}\n"
    body += f"- Account balance: {_fmt_currency(balance)}\n"
    body += f"- Monthly surplus: {_fmt_currency(surplus)}\n"
    body += f"- Transactions on file: {tx_count}\n\n"

    # Spending by category
    categories = _aggregate_categories(summary.get("recent_transactions", []))
    if categories:
        body += "## Spending by category\n\n"
        body += "| Category | Amount |\n|---|---|\n"
        for cat, amt in categories:
            body += f"| {cat} | {_fmt_currency(amt)} |\n"
        body += "\n"

    # Linked sections
    body += "## Linked accounts\n"
    body += f"{_wikilink('01_accounts/balances')}\n\n"

    if goals:
        body += "## Active goals\n"
        for g in goals:
            name = _safe_filename(g.get("title", "untitled"))
            body += f"- {_wikilink(f'03_goals/{name}')}\n"
        body += "\n"

    if plans:
        body += "## Active plans\n"
        for p in plans:
            name = _safe_filename(p.get("title", "untitled"))
            body += f"- {_wikilink(f'04_plans/{name}')}\n"
        body += "\n"

    if loans:
        body += "## Active loans\n"
        for l in loans:
            name = _safe_filename(l.get("title", l.get("bank", "untitled")))
            body += f"- {_wikilink(f'01_accounts/loans/{name}')}\n"
        body += "\n"

    # Dataview query — Obsidian renders this as a live table
    body += "## All active goals (Dataview)\n\n"
    body += "```dataview\n"
    body += 'TABLE target, deadline, saved FROM "03_goals"\n'
    body += 'WHERE status = "active"\n'
    body += "SORT deadline ASC\n"
    body += "```\n"

    return fm + "\n" + body


# ─── Balances note (01_accounts/balances.md) ──────────────────────────────────

def render_balances_note(
    user_id: int,
    summary: Dict[str, Any],
) -> str:
    balance = summary.get("account_balance", 0) or 0
    credit_cards = summary.get("credit_cards", [])
    loans = summary.get("loans", [])

    fm = _frontmatter({
        "type": "balances",
        "user_id": user_id,
        "updated": _today(),
    })

    body = "# Account Balances\n\n"
    body += f"- Primary account: {_fmt_currency(balance)}\n\n"

    if credit_cards:
        body += "## Credit cards\n\n"
        for cc in credit_cards:
            name = cc.get("card_name", cc.get("bank", "Card"))
            body += f"- **{name}**: outstanding {_fmt_currency(cc.get('current_outstanding', 0))}, "
            body += f"limit {_fmt_currency(cc.get('credit_limit', 0))}\n"
        body += "\n"

    if loans:
        body += "## Loans\n\n"
        for loan in loans:
            title = loan.get("title", loan.get("bank", "Loan"))
            body += f"- **{title}**: {_fmt_currency(loan.get('outstanding_principal', 0))} remaining "
            body += f"({_wikilink(f'01_accounts/loans/{_safe_filename(title)}')})\n"
        body += "\n"

    return fm + "\n" + body


# ─── Goal note (03_goals/{name}.md) ───────────────────────────────────────────

def render_goal_note(goal: Dict[str, Any]) -> str:
    title = goal.get("title", "Untitled Goal")
    target = goal.get("target_amount", 0) or 0
    saved = goal.get("current_saved", 0) or 0
    deadline = goal.get("deadline", "not set")
    status = goal.get("status", "active")
    pct = round((saved / target * 100) if target else 0, 1)

    fm = _frontmatter({
        "type": "goal",
        "status": status,
        "target": target,
        "deadline": deadline,
        "saved": saved,
        "updated": _today(),
    })

    body = f"# {title}\n\n"
    body += f"Target: {_fmt_currency(target)} by {deadline}\n"
    body += f"Saved: {_fmt_currency(saved)} ({pct}%)\n\n"

    # Link to associated plan if name matches
    plan_name = _safe_filename(title)
    body += "## Linked plan\n"
    body += f"{_wikilink(f'04_plans/{plan_name}')}\n\n"

    body += "## Relevant conversations\n"
    body += f"Search: {_wikilink(f'05_conversations/{_today()}')}\n"

    return fm + "\n" + body


# ─── Plan note (04_plans/{name}.md) ───────────────────────────────────────────

def render_plan_note(plan: Dict[str, Any]) -> str:
    title = plan.get("title", "Untitled Plan")
    target = plan.get("target_amount", 0) or 0
    saved = plan.get("current_saved", 0) or 0
    deadline = plan.get("deadline", "not set")
    status = plan.get("status", "active")
    monthly = plan.get("monthly_saving", 0) or 0

    fm = _frontmatter({
        "type": "plan",
        "status": status,
        "target": target,
        "monthly_saving": monthly,
        "deadline": deadline,
        "updated": _today(),
    })

    body = f"# {title}\n\n"
    body += f"- Target: {_fmt_currency(target)}\n"
    body += f"- Monthly saving: {_fmt_currency(monthly)}\n"
    body += f"- Saved so far: {_fmt_currency(saved)}\n"
    body += f"- Deadline: {deadline}\n"
    body += f"- Status: {status}\n\n"

    # Link back to goal
    goal_name = _safe_filename(title)
    body += "## Linked goal\n"
    body += f"{_wikilink(f'03_goals/{goal_name}')}\n"

    return fm + "\n" + body


# ─── Loan note (01_accounts/loans/{name}.md) ─────────────────────────────────

def render_loan_note(loan: Dict[str, Any]) -> str:
    title = loan.get("title", loan.get("bank", "Loan"))
    principal = loan.get("outstanding_principal", 0) or 0
    rate = loan.get("interest_rate", 0) or 0
    emi = loan.get("emi_amount", 0) or 0
    tenure = loan.get("remaining_tenure_months", 0) or 0

    fm = _frontmatter({
        "type": "loan",
        "outstanding": principal,
        "rate": rate,
        "emi": emi,
        "tenure_months": tenure,
        "updated": _today(),
    })

    body = f"# {title}\n\n"
    body += f"- Outstanding: {_fmt_currency(principal)}\n"
    body += f"- Interest rate: {rate}%\n"
    body += f"- EMI: {_fmt_currency(emi)}\n"
    body += f"- Remaining tenure: {tenure} months\n\n"

    body += "## Linked\n"
    body += f"{_wikilink('01_accounts/balances')}\n"

    return fm + "\n" + body


# ─── Conversation note (05_conversations/YYYY-MM-DD.md) ──────────────────────

def render_conversation_entry(
    question: str,
    answer: Dict[str, Any],
    summary: Dict[str, Any],
    intent: str = "finance_query",
) -> str:
    """Render a single Q&A turn to be appended to the daily conversation note."""
    now = datetime.now().strftime("%H:%M")

    income = summary.get("monthly_income", 0) or 0
    expenses = summary.get("monthly_expenses", 0) or 0
    balance = summary.get("account_balance", 0) or 0
    surplus = summary.get("monthly_surplus", 0) or 0

    # Extract the answer text
    if answer.get("mode") == "simple":
        answer_text = answer.get("content", "")
    elif answer.get("Financial Overview"):
        sections = []
        for key in ("Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome"):
            val = answer.get(key)
            if val and val != "N/A":
                sections.append(f"**{key}**: {val}")
        answer_text = "\n\n".join(sections)
    else:
        answer_text = answer.get("content", str(answer))

    entry = f"\n---\n\n### {now} — {intent}\n\n"
    entry += f"**User**: {question}\n\n"
    entry += f"**TORA**: {answer_text}\n\n"
    entry += "**Numbers referenced**:\n"
    entry += f"- Balance: {_fmt_currency(balance)}\n"
    entry += f"- Income: {_fmt_currency(income)}\n"
    entry += f"- Expenses: {_fmt_currency(expenses)}\n"
    entry += f"- Surplus: {_fmt_currency(surplus)}\n"

    return entry


def render_conversation_header(date: str, intent: str = "finance_query") -> str:
    """Render the frontmatter header for a new daily conversation note."""
    fm = _frontmatter({
        "type": "conversation",
        "date": date,
        "intent": intent,
        "topics": "[]",
    })
    return fm + f"\n# Session {date}\n"


# ─── Monthly transactions (02_transactions/YYYY-MM.md) ───────────────────────

def render_monthly_transactions_note(
    period: str,
    summary: Dict[str, Any],
) -> str:
    """Render a monthly summary of transactions."""
    income = summary.get("monthly_income", 0) or 0
    expenses = summary.get("monthly_expenses", 0) or 0
    transactions = summary.get("recent_transactions", [])

    fm = _frontmatter({
        "type": "monthly_transactions",
        "period": period,
        "income": income,
        "expenses": expenses,
        "tx_count": len(transactions),
        "updated": _today(),
    })

    body = f"# Transactions — {period}\n\n"
    body += f"- Total income: {_fmt_currency(income)}\n"
    body += f"- Total expenses: {_fmt_currency(expenses)}\n"
    body += f"- Transaction count: {len(transactions)}\n\n"

    categories = _aggregate_categories(transactions)
    if categories:
        body += "## By category\n\n"
        body += "| Category | Amount |\n|---|---|\n"
        for cat, amt in categories:
            body += f"| {cat} | {_fmt_currency(amt)} |\n"
        body += "\n"

    # Transaction List
    if transactions:
        body += "## Transaction Detail\n\n"
        body += "| Date | Description | Type | Amount |\n"
        body += "|---|---|---|---|\n"
        for tx in transactions[:100]:  # Cap at 100 to avoid massive files
            date = tx.get("date", "---")
            title = tx.get("title", tx.get("description", "Untitled"))
            txtype = tx.get("type", "expense")
            amt = tx.get("amount", 0)
            sign = "+" if txtype == "income" else "-"
            body += f"| {date} | {title} | {txtype} | {sign}{_fmt_currency(amt)} |\n"
        body += "\n"

    body += "## Links\n"
    body += f"{_wikilink('00_profile/overview')}\n"

    return fm + "\n" + body


# ─── Obsidian Canvas (financial_map.canvas) ──────────────────────────────────

def render_canvas(summary: Dict[str, Any]) -> str:
    """Generate an Obsidian Canvas JSON file linking key vault notes."""
    nodes = [
        {"id": "profile", "type": "file", "file": "00_profile/overview.md",
         "x": 0, "y": 0, "width": 400, "height": 300},
        {"id": "balances", "type": "file", "file": "01_accounts/balances.md",
         "x": -500, "y": 0, "width": 400, "height": 300},
        {"id": "transactions", "type": "file", "file": f"02_transactions/{_period()}.md",
         "x": 0, "y": 400, "width": 400, "height": 300},
    ]
    edges = [
        {"id": "e1", "fromNode": "profile", "toNode": "balances"},
        {"id": "e2", "fromNode": "profile", "toNode": "transactions"},
    ]

    # Add goal nodes
    goals = summary.get("goals", [])
    for i, g in enumerate(goals):
        name = _safe_filename(g.get("title", f"goal_{i}"))
        node_id = f"goal_{i}"
        nodes.append({
            "id": node_id, "type": "file",
            "file": f"03_goals/{name}.md",
            "x": 500, "y": i * 350, "width": 400, "height": 250,
        })
        edges.append({"id": f"eg{i}", "fromNode": "profile", "toNode": node_id})

    # Add plan nodes
    plans = summary.get("plans", [])
    for i, p in enumerate(plans):
        name = _safe_filename(p.get("title", f"plan_{i}"))
        node_id = f"plan_{i}"
        nodes.append({
            "id": node_id, "type": "file",
            "file": f"04_plans/{name}.md",
            "x": 1000, "y": i * 350, "width": 400, "height": 250,
        })
        edges.append({"id": f"ep{i}", "fromNode": f"goal_{i}" if i < len(goals) else "profile", "toNode": node_id})

    return json.dumps({"nodes": nodes, "edges": edges}, indent=2)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Convert a title to a safe filename (lowercase, underscores)."""
    safe = name.lower().strip()
    safe = "".join(c if c.isalnum() or c in " _-" else "" for c in safe)
    safe = safe.replace(" ", "_")
    return safe[:60] or "untitled"


def _aggregate_categories(transactions: list) -> list:
    """Group transactions by category and return sorted (cat, total) pairs."""
    cats: Dict[str, float] = {}
    for tx in transactions:
        if tx.get("type") == "expense":
            cat = tx.get("category", "other") or "other"
            cats[cat] = cats.get(cat, 0) + float(tx.get("amount", 0))
    return sorted(cats.items(), key=lambda x: x[1], reverse=True)
