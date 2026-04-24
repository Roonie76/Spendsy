"""
4-stage entity resolver.

Stage 1 — token-normalized exact match against each plugin's entity_keys.
  Multi-word keys match as consecutive tokens; prevents "ev" matching "every"
  and "tv" matching "tvs".

Stage 2 — synonym lookup (Hindi/Hinglish-aware) maps user tokens to canonical
  entities, which are then mapped back to a plugin.

Stage 3 — fuzzy fallback. Only fires when stages 1-2 produced nothing and the
  user has 4+ letter tokens. Uses difflib to catch common typos (swuft→swift,
  iphne→iphone, modlar→modular). Stdlib only, no new dependency.

Stage 4 — if nothing resolves, return []. We deliberately do NOT call an LLM
  to guess; that violates the no-lag constraint.

The resolver returns up to MAX_MATCHES PluginMatch entries, ranked by score.
Composition role (primary vs supporting) is assigned here, not downstream,
so the engine can fan out fetches with known roles.
"""

from __future__ import annotations

import difflib
import re
from typing import Iterable

from .entity_synonyms import REVERSE_SYNONYMS
from .fetch_registry import PLUGIN_REGISTRY, PluginMatch

MAX_MATCHES = 2

# A generous tokenizer: splits on whitespace and punctuation, keeps alphanumeric
# and hyphen (so "e-bike" survives as one token). Lowercases everything.
_TOKEN_RE = re.compile(r"[A-Za-z0-9+]+(?:['\-][A-Za-z0-9+]+)*")


def _tokenize(message: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(message or "")]


def _build_entity_to_plugin_map() -> dict[str, str]:
    """Flatten PLUGIN_REGISTRY to entity_key → plugin_id.

    Built lazily (not at import) because plugins register themselves via
    the package __init__, which imports this module first.
    """
    mapping: dict[str, str] = {}
    for plugin_id, plugin in PLUGIN_REGISTRY.items():
        for key in plugin.entity_keys:
            mapping[key.lower()] = plugin_id
    return mapping


def _find_consecutive_match(
    tokens: list[str], phrase: str
) -> tuple[int, int] | None:
    """Return (start, end) if phrase (multi-token) appears as consecutive
    tokens in `tokens`. Case-insensitive."""
    phrase_tokens = phrase.lower().split()
    if not phrase_tokens:
        return None
    n = len(phrase_tokens)
    for i in range(len(tokens) - n + 1):
        if tokens[i : i + n] == phrase_tokens:
            return i, i + n
    return None


def _score_match(phrase: str, message_token_count: int) -> float:
    """Longer phrases score higher (prefer "air conditioner" over "ac"),
    normalised against message length so short messages don't over-inflate."""
    phrase_len = len(phrase.split())
    base = min(1.0, phrase_len / 3.0)  # caps at 3-word phrases
    # Small bonus for multi-word matches — they're almost certainly intentional.
    if phrase_len > 1:
        base += 0.1
    # Penalise when the phrase is most of the message (likely a generic query
    # like "ev" in a 3-word question — keep but don't over-rank).
    density = phrase_len / max(1, message_token_count)
    if density > 0.8:
        base *= 0.9
    return round(min(1.0, base), 3)


def _collect_stage1(
    tokens: list[str], entity_to_plugin: dict[str, str]
) -> list[tuple[str, str, float]]:
    """Stage 1: direct entity_key matches.

    Returns list of (plugin_id, matched_phrase, score). Duplicates per plugin
    are collapsed in _rank().
    """
    hits: list[tuple[str, str, float]] = []
    # Try longer phrases first so "air conditioner" wins over "air" if both
    # were entity keys (though we don't have "air" as one — this is defence
    # in depth).
    keys_by_length = sorted(
        entity_to_plugin.keys(), key=lambda k: len(k.split()), reverse=True
    )
    n_tokens = len(tokens)
    for key in keys_by_length:
        if " " in key:
            if _find_consecutive_match(tokens, key) is not None:
                hits.append(
                    (entity_to_plugin[key], key, _score_match(key, n_tokens))
                )
        else:
            if key in tokens:
                hits.append(
                    (entity_to_plugin[key], key, _score_match(key, n_tokens))
                )
    return hits


def _collect_stage3_fuzzy(
    tokens: list[str], entity_to_plugin: dict[str, str]
) -> list[tuple[str, str, float]]:
    """Stage 3: fuzzy-match individual tokens against single-word entity keys
    and short synonyms when stages 1-2 produced nothing.

    Uses `difflib.get_close_matches` (stdlib, Ratcliff-Obershelp ratio) with
    a conservative cutoff of 0.8 — catches one-char typos and common
    transpositions ("swuft" vs "swift", "iphne" vs "iphone") but won't
    hallucinate matches on unrelated words.

    Only applied to user tokens of length >= 4 to avoid false matches on
    short noise like "an", "on", "to".
    """
    n_tokens = len(tokens)
    # Build candidate pool: single-word entity keys + single-word synonyms
    # + "distinctive" words pulled from multi-word keys ("insurance" from
    # "health insurance", "billion" from "big billion"). We skip generic
    # connectors AND generic-finance vocabulary — words like "monthly",
    # "budget", "income", "saving" appear in track-1 profile queries and
    # fuzzy-matching them creates massive false-positive leakage.
    _STOPWORD_TOKENS = {
        # Connectives
        "the", "a", "an", "of", "my", "me", "for", "to", "and", "or",
        "in", "on", "at", "with", "by", "is", "are", "was", "were",
        # Generic descriptors that shouldn't drive plugin routing
        "home", "new", "old", "best", "next", "last", "this", "that",
        "more", "less", "some", "many", "few", "much",
        # Generic finance vocabulary — these fire in track-1 queries and
        # must never fuzzy-match into a plugin.
        "monthly", "month", "yearly", "year", "budget", "budgets",
        "expense", "expenses", "income", "spending", "spend", "saved",
        "saving", "savings", "save", "balance", "paise", "paisa",
        "rupees", "rupee", "amount", "total", "cost", "costs", "costing",
        "price", "prices", "fee", "fees", "rate", "rates",
        # Common English nouns that live inside multi-word synonyms but
        # would be ambiguous as fuzzy-match targets on their own.
        "water", "heater", "paris", "rome", "bath", "toilet", "class",
        "house", "home", "cover", "plan", "charge", "charges",
        "care", "center", "centre", "club", "card", "credit", "debit",
        "party", "event", "study",
        # Generic spending-category words that are too broad to route —
        # they're either track-1 descriptions ("spent on food") or need
        # a more specific co-occurring term to be meaningful.
        "food", "shopping", "travel", "grocery", "groceries",
        "current", "account", "salary", "credit", "debit",
        # Hindi verbs / connectors that shouldn't fuzzy-match entity words
        "kiya", "kiye", "kya", "hai", "tha", "thi", "thi",
        "mera", "meri", "mere", "apna", "apne", "apni",
    }
    candidate_pool: dict[str, str] = {}

    def _add_token(word: str, plugin_id: str) -> None:
        # 4-char threshold: "loan", "rent", "bike", "gold" are real entity
        # words we want to catch typos of. Stopword set blocks the generics.
        if len(word) < 4 or word in _STOPWORD_TOKENS:
            return
        candidate_pool.setdefault(word, plugin_id)

    # Pool canonical entity keys first (high-quality, curated).
    for key, plugin_id in entity_to_plugin.items():
        if " " in key:
            for part in key.split():
                _add_token(part, plugin_id)
        elif len(key) >= 4:
            candidate_pool.setdefault(key, plugin_id)

    # Then pool distinctive synonym words so we can catch typos of user
    # phrasing ("swuft"→"swift", "iphne"→"iphone", "billon"→"billion",
    # "insurnce"→"insurance"). `_add_token` enforces 4+ chars + stopword
    # filter + first-letter guard below. We also pool parts of multi-word
    # synonyms for things like "big billion" → "billion".
    for syn, canonical in REVERSE_SYNONYMS.items():
        plugin_id = entity_to_plugin.get(canonical.lower())
        if not plugin_id:
            continue
        if " " in syn:
            for part in syn.split():
                _add_token(part, plugin_id)
        else:
            _add_token(syn, plugin_id)

    pool_keys = list(candidate_pool.keys())
    hits: list[tuple[str, str, float]] = []
    for tok in tokens:
        # Short tokens (3 chars) are allowed because "rnt"→"rent" is a real
        # user typo, but we compensate by requiring strict first-letter match
        # below so "the"/"any" don't match.
        if len(tok) < 3 or tok in _STOPWORD_TOKENS:
            continue
        close = difflib.get_close_matches(tok, pool_keys, n=1, cutoff=0.8)
        if not close:
            continue
        matched_key = close[0]
        # First-letter guardrail: fuzzy matches must share the first char.
        # Real typos almost always preserve it (swuft/swift, iphne/iphone,
        # modlar/modular, rnt/rent, billon/billion). Noise matches from
        # difflib often don't (any/any-of-many). Cheap and very effective.
        if tok[0] != matched_key[0]:
            continue
        plugin_id = candidate_pool[matched_key]
        # Score fuzzy hits slightly below exact matches so if any other
        # stage later finds an exact hit it wins.
        score = _score_match(matched_key, n_tokens) * 0.85
        hits.append((plugin_id, matched_key, round(score, 3)))
    return hits


def _collect_stage2(
    tokens: list[str], entity_to_plugin: dict[str, str]
) -> list[tuple[str, str, float]]:
    """Stage 2: synonym → canonical → plugin.

    Only considers synonyms whose canonical is actually registered as an
    entity_key somewhere. This keeps stale synonyms (for plugins we haven't
    built yet) from producing phantom matches.
    """
    hits: list[tuple[str, str, float]] = []
    n_tokens = len(tokens)

    # Try multi-word synonyms first.
    sorted_syns = sorted(
        REVERSE_SYNONYMS.keys(), key=lambda s: len(s.split()), reverse=True
    )
    for syn in sorted_syns:
        canonical = REVERSE_SYNONYMS[syn]
        plugin_id = entity_to_plugin.get(canonical.lower())
        if not plugin_id:
            continue
        if " " in syn:
            if _find_consecutive_match(tokens, syn) is not None:
                hits.append((plugin_id, canonical, _score_match(syn, n_tokens)))
        else:
            if syn in tokens:
                hits.append((plugin_id, canonical, _score_match(syn, n_tokens)))
    return hits


def _rank(
    candidates: Iterable[tuple[str, str, float]],
) -> list[PluginMatch]:
    """Collapse duplicates per plugin (keep best score + longest entity),
    sort by score desc, assign primary/supporting roles."""
    best_per_plugin: dict[str, tuple[str, float]] = {}
    for plugin_id, entity, score in candidates:
        cur = best_per_plugin.get(plugin_id)
        if cur is None or score > cur[1] or (
            score == cur[1] and len(entity) > len(cur[0])
        ):
            best_per_plugin[plugin_id] = (entity, score)

    ranked = sorted(
        best_per_plugin.items(), key=lambda item: item[1][1], reverse=True
    )
    matches: list[PluginMatch] = []
    for i, (plugin_id, (entity, score)) in enumerate(ranked[:MAX_MATCHES]):
        matches.append(
            PluginMatch(
                plugin_id=plugin_id,
                entity=entity,
                score=score,
                role="primary" if i == 0 else "supporting",
            )
        )
    return matches


def resolve_entities(message: str) -> list[PluginMatch]:
    """Resolve a user message to zero or more plugin matches.

    Returns [] when nothing matches — caller should skip enrichment entirely
    rather than guess. Never raises on malformed input.
    """
    if not message or not message.strip():
        return []
    tokens = _tokenize(message)
    if not tokens:
        return []

    entity_to_plugin = _build_entity_to_plugin_map()
    if not entity_to_plugin:
        # Registry hasn't been populated yet — safe no-op.
        return []

    hits = _collect_stage1(tokens, entity_to_plugin)
    hits.extend(_collect_stage2(tokens, entity_to_plugin))
    if not hits:
        # Stage 3: fuzzy only fires when exact + synonym both returned nothing.
        hits = _collect_stage3_fuzzy(tokens, entity_to_plugin)
    if not hits:
        return []
    return _rank(hits)
