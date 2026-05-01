import re

# TORA System Prompt: Defines the CA personality and strict formatting rules
TORA_SYSTEM_PROMPT = """You are TORA, an intelligent financial advisor inside the Spendsy platform.
Your goal is to help users understand their finances, budget, and plan for the future.

### CORE RULES
1. NEVER use the $ symbol; always use ₹ (Rupees) for currency.
2. ONLY quote numbers that appear VERBATIM in the "MY FINANCIAL PROFILE", "ADDITIONAL CONTEXT", "SIMULATIONS", or "MARKET & CATEGORY CONTEXT" blocks. If a number is not in those blocks, DO NOT write it — rewrite the sentence to describe the direction (e.g. "tight", "comfortable", "stretched") instead of inventing a figure.
3. Keep answers concise, direct, and conversational. Match reply length to question length.
4. You MUST output your response exactly as a JSON object matching the requested schema.
5. Provide a brief internal "reasoning" string where you verify your numbers before formulating the final "answer".
6. If the user asks a follow-up ("why?", "tell me more", "explain"), use the conversation history. Never say it's off-topic.
7. Never start with filler ("Certainly!", "Of course!", "Great question!"). Dive straight in.

### HANDLING QUESTION VARIATIONS (critical — users phrase the same intent many ways)
- Read the USER'S INTENT, not the exact wording. "Can I afford X?", "Is X within my budget?", "Should I buy X now?", "Kya mujhe X lena chahiye?" are all the same intent: a decision request about affording/buying X.
- Hinglish and Indian-English phrasing is normal and expected. Treat "shaadi", "gaadi", "sona", "paisa", "gehne", "kharcha" exactly like their English equivalents.
- Typos and casual spellings ("aford", "swuft", "iphne", "insurnce") are the same as the correct words. Do not ask the user to clarify spelling — answer the intent.
- Short queries ("SIP vs FD", "best AC", "PPF or ELSS") are full questions, not fragments. Give a decisive answer using the MARKET block.
- If the MARKET & CATEGORY CONTEXT block is present, it already contains the grounded facts + rules for this topic. Use them. Do not say "it depends on your situation" when the context already contains both the facts and the rules to apply.
- If the MARKET block is absent (no category matched), you are in profile-only mode: answer ONLY from the user's own vault/transactions. Never fabricate category knowledge (car prices, interest rates, gold rates) when no MARKET block exists.
- If you need more data (like specific transactions beyond the recent list), USE YOUR TOOLS.
- If you need real-time market data (car prices, bank interest rates, stock prices), USE `search_internet`.

### TOOLS
You can call these tools when needed. **IMPORTANT: DO NOT include `user_id` in the parameters; the system injects it automatically.**
- `get_transactions(limit=50)`: Fetch more recent transactions.
- `query_spending_data(query_type)`: Run specific analysis. Types: 'monthly_category_totals', 'merchant_statistics', 'income_expense_ratio'.
- `search_internet(query)`: Search the web for real-time market data (e.g., "Axis bank personal loan rates", "Honda City on-road price in Mumbai").
- `compare_tax_regimes()`: Compare old vs new tax regimes.
- `create_plan(title, target_amount, deadline, monthly_saving)`: Create a savings plan.
- `adjust_plan(plan_id, updates)`: Update an existing plan.
- `update_tax_profile(updates)`: Update tax-related fields (rent, 80C, etc.).

### FINANCIAL REASONING (for Planning & Affordability)
When creating a plan or answering "can I afford", use this logic:
1. **Interest Arbitrage**: If the user has high-interest debt (e.g., Credit Card @ 36%-42%), prioritize paying it off using a low-interest Personal Loan (e.g., 10.5%-14%) or Surplus.
2. **Savings Calculation**: Always calculate the EXACT interest saved. Formula: `(High_Rate - Low_Rate) * Principal / 12` = monthly interest saved.
3. **EMI Capacity**: Ensure total EMIs do not exceed 40% of Monthly Income.
4. **Surplus Mapping**: Explicitly suggest moving saved interest into new EMIs (e.g. "Saving ₹40k on CC interest covers your car EMI").

### OUTPUT FORMAT
Your output must be a single valid JSON object with these keys:
- "reasoning": A brief internal scratchpad (1-2 sentences). Verify your interest math here.
- "answer": The response object (see modes below).
- "tool_calls": An array of tool calls, or empty [].

**Simple Mode (DEFAULT — use for most questions)**
{"reasoning": "...", "answer": {"mode": "simple", "content": "A concise Markdown response."}, "tool_calls": []}

**Structured Mode (ONLY for "summarize", "analyze", "plan", or "review" requests)**
{"reasoning": "...", "answer": {"Financial Overview": "...", "Current Position": "...", "Recommended Strategy": "...", "Expected Outcome": "..."}, "tool_calls": []}

Default to Simple Mode. Never pad a short answer into four cards.
"""

# Greeting Keywords
GREETING_KEYWORDS = [
    r'\bhi\b', r'\bhello\b', r'\bhey\b', r'\byo\b', r'\bhola\b',
    r'\bgood\s+morning\b', r'\bgood\s+afternoon\b', r'\bgood\s+evening\b',
    r'\bhow\s+are\s+you\b', r'\bhowdy\b', r'\bsup\b', r"\bwhat'?s\s+up\b"
]

# Small-talk / acknowledgements — short social messages that should NEVER
# trigger a financial-data LLM call (they must stay purely conversational).
SMALL_TALK_KEYWORDS = [
    r'^\s*(?:thanks?|thank\s+you|ty|thx)\b',
    r'^\s*(?:ok(?:ay)?|cool|nice|great|awesome|got\s+it|sure|alright|sounds\s+good)\b',
    r'^\s*(?:bye|goodbye|see\s+you|cya|later|good\s+night|gn)\b',
    r'^\s*(?:no\s+problem|np|you\s+too|same|lol|haha|hehe)\b',
]

# Finance Keywords
FINANCE_KEYWORDS = [
    r'\bloan[s]?\b', r'\bemi[s]?\b', r'\btax(?:es)?\b', r'\bbudget(?:ing)?\b',
    r'\bspend(?:ing|s|ings)?\b', r'\binvest(?:ment|ing|ments)?\b', r'\bsav(?:e|ing|ings)\b',
    r'\bdebt[s]?\b', r'\bincome\b', r'\bexpense[s]?\b', r'\bcredit\b',
    r'\bpurchase[s]?\b', r'\bfinance[s]?\b', r'\bmoney\b', r'\ba?fford(?:able)?\b',
    r'\bbank(?:ing)?\b', r'\bcash\b', r'\bfund[s]?\b', r'\bwealth\b', r'\bpay(?:ment)?\b',
    r'\bsalary\b', r'\bmortgage[s]?\b', r'\binterest\b', r'\bretir(?:e|ement)\b',
    r'\bstock[s]?\b', r'\bshare[s]?\b', r'\bportfolio\b',
    r'\bbalance[s]?\b', r'\btransaction[s]?\b', r'\bnet\s+worth\b',
    r'\bsurplus\b', r'\bdeficit\b', r'\bgoal[s]?\b', r'\bplan(?:ner|s|ning)?\b',
    r'\bbill[s]?\b', r'\bcategor(?:y|ies|ize|ise)\b', r'\bmonthly\b', r'\bannual(?:ly)?\b',
    r'\bemergency\s+fund\b', r'\bsip\b', r'\bmutual\s+fund[s]?\b', r'\bfd\b',
]

# Conversational keywords: questions about TORA itself, general queries, or follow-ups
CONVERSATIONAL_KEYWORDS = [
    r'\bwhat\s+can\s+you\s+do\b', r'\bwhat\s+do\s+you\s+do\b',
    r'\bwho\s+are\s+you\b', r'\bwhat\s+are\s+you\b',
    r'\bhelp\s+me\b', r'\bhelp\b', r'\bcan\s+you\b',
    r'\btell\s+me\b', r'\bexplain\b', r'\bhow\s+does\b', r'\bhow\s+do\b',
    r'\bwhat\s+is\b', r'\bwhat\'?s\b', r'\bwhy\b', r'\bwhen\b',
    r'\bshould\s+i\b', r'\badvice\b', r'\bsuggest\b', r'\brecommend\b',
    r'\bthank(?:s|\s+you)\b', r'\byes\b', r'\bno\b', r'\bok(?:ay)?\b',
    r'\bplease\b', r'\bshow\s+me\b', r'\blist\b', r'\bsummar\w+\b',
    r'\bmore\b', r'\bdetail\b', r'\bplan\b', r'\bgoal\b',
    r'\bhow\s+much\b', r'\bhow\s+many\b', r'\bcompare\b', r'\bbetter\b',
    r'\bbest\b', r'\bworst\b', r'\btip[s]?\b', r'\bstrateg\w+\b',
    r'\bstart\b', r'\bbegin\b', r'\bget\s+started\b',
    r'\byour\s+feature\b', r'\byour\s+capabilit\b', r'\bwhat\s+else\b',
]

def detect_intent(message: str) -> str:
    """
    Categorizes the user's message as one of:
        - 'greeting'        — pure hi/hello with no finance content
        - 'small_talk'      — thanks / ok / bye / cool
        - 'finance_query'   — explicit finance keywords
        - 'conversational'  — capability questions / follow-ups → LLM
        - 'non_finance_query' — off-topic
    """
    message_lc = message.lower().strip()

    finance_pattern = re.compile('|'.join(FINANCE_KEYWORDS), re.IGNORECASE)
    has_finance = bool(finance_pattern.search(message_lc))

    # Small talk gets checked first and only counts if the message is SHORT
    # and has no finance content. "thanks, but what about my loans?" → finance.
    if not has_finance and len(message_lc.split()) <= 5:
        small_talk_pattern = re.compile('|'.join(SMALL_TALK_KEYWORDS), re.IGNORECASE)
        if small_talk_pattern.match(message_lc):
            return "small_talk"

    # Pure greeting — must be short AND have no finance words
    greeting_pattern = re.compile('|'.join(GREETING_KEYWORDS), re.IGNORECASE)
    if greeting_pattern.search(message_lc) and not has_finance and len(message_lc.split()) <= 6:
        return "greeting"

    if has_finance:
        return "finance_query"

    conversational_pattern = re.compile('|'.join(CONVERSATIONAL_KEYWORDS), re.IGNORECASE)
    if conversational_pattern.search(message_lc):
        return "conversational"

    return "non_finance_query"

def is_finance_related(question: str) -> bool:
    """
    Checks if the user's question relates to personal finance topics.
    Deprecated: Use detect_intent instead.
    """
    return detect_intent(question) == "finance_query"

_GREETING_REPLIES_FIRST = [
    "Hey! I'm TORA, your financial copilot. What would you like to look at today — spending, a savings goal, or something else?",
    "Hi there! I can help you make sense of your money. Want to review this month's spending, or plan toward something specific?",
    "Hello! Happy to help. Shall we check your budget, plan a goal, or dig into a specific category?",
]

_GREETING_REPLIES_RETURNING = [
    "Hey, welcome back. What would you like to work on — a quick check on spending, or planning something new?",
    "Hi again! Anything specific on your mind today? I can summarize your finances or help plan a goal.",
    "Hey! Picking up where we left off — want a spending recap, or should we start something new?",
    "Hi! What can I help with — budgets, a savings plan, or something else?",
]

_SMALL_TALK_REPLIES = {
    "thanks": [
        "Anytime! Let me know if there's anything else to look at.",
        "Happy to help. Want to keep going, or is that all for now?",
        "You're welcome! Anything else you'd like to plan or review?",
    ],
    "ok": [
        "Got it. Anything else you'd like to explore?",
        "Cool. Just say the word when you want to dig into something.",
        "Sounds good. Want to look at spending, a goal, or something else?",
    ],
    "bye": [
        "Take care! I'll be here whenever you need a hand with your finances.",
        "See you later — your plans are safe with me.",
        "Goodbye! Come back anytime for a check-in.",
    ],
    "generic": [
        "Got it. What would you like to do next?",
        "Cool. Anything else on your mind?",
    ],
}


def get_greeting_response(is_returning: bool = False) -> str:
    """Returns a conversational greeting as a simple-mode reply.

    is_returning: True if the user already has conversation history."""
    import json, random
    pool = _GREETING_REPLIES_RETURNING if is_returning else _GREETING_REPLIES_FIRST
    return json.dumps({"mode": "simple", "content": random.choice(pool)})


def get_small_talk_response(message: str) -> str:
    """Deterministic reply to greetings/acknowledgements — never calls the LLM."""
    import json, random
    msg = message.lower().strip()
    if re.match(r'^\s*(?:thanks?|thank\s+you|ty|thx)', msg):
        bucket = "thanks"
    elif re.match(r'^\s*(?:bye|goodbye|see\s+you|cya|later|good\s+night|gn)', msg):
        bucket = "bye"
    elif re.match(r'^\s*(?:ok(?:ay)?|cool|nice|great|awesome|got\s+it|sure|alright|sounds\s+good)', msg):
        bucket = "ok"
    else:
        bucket = "generic"
    return json.dumps({"mode": "simple", "content": random.choice(_SMALL_TALK_REPLIES[bucket])})


def get_capability_response() -> str:
    """Returns TORA's capability summary as a simple-mode markdown reply."""
    import json
    return json.dumps({
        "mode": "simple",
        "content": (
            "I'm TORA, your personal financial advisor. Here's what I can help with:\n\n"
            "- **Spending Analysis** — track and understand your spending patterns\n"
            "- **Budget Planning** — build and maintain realistic budgets\n"
            "- **Savings Goals** — plan for purchases, emergencies, or milestones\n"
            "- **Loan Management** — analyze EMIs and build repayment strategies\n"
            "- **Tax Planning** — compare regimes and find savings\n"
            "- **Investment Insights** — tax-efficient allocation suggestions\n\n"
            "Try: *\"Help me save ₹50,000 for a laptop by August\"* or *\"Analyze my spending this month\"*."
        )
    })


# ---------------------------------------------------------------------------
# Ambiguity pre-filter — catch common "I want to save more" style asks that
# shouldn't hit the LLM at all. Cheaper than a round-trip, more reliable
# than prompt-only steering, and keeps the clarifying-question shape
# consistent even when the local model is having an off day.
# ---------------------------------------------------------------------------

# Goal verbs that indicate the user wants to plan, save, or buy something.
_GOAL_VERBS = (
    r"save\s+(?:for|up|more)|plan(?:ning)?\s+for|buy|purchase|afford|"
    r"set\s+aside|build\s+up|get\s+(?:a|an)|pay\s+off|invest\s+in|start\s+"
)

# Phrases that are aspirational but never specify an amount or date.
_VAGUE_ASPIRATION_RE = re.compile(
    r"^\s*(?:i\s+(?:want|need|should|wanna|wish|hope)|can\s+you\s+help\s+me)\s+"
    r"(?:to\s+)?(?:save\s+more|spend\s+less|be\s+better|budget\s+better|"
    r"get\s+rich|retire\s+rich|plan\s+better|manage\s+(?:my\s+)?money|"
    r"be\s+(?:financially\s+)?(?:smarter|responsible)|"
    r"improve\s+(?:my\s+)?finances?|sort\s+out\s+(?:my\s+)?finances?|"
    r"fix\s+(?:my\s+)?spending|figure\s+(?:this|it|things)\s+out)",
    re.IGNORECASE,
)

# Amount / money token — ₹5k, ₹50,000, 5 lakhs, 2 crore, 5000 rs, etc.
_AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr|rupees?)\s?[\d,]+|"
    r"\b\d[\d,]*\s?(?:k|lakh|lac|cr|crore|l)\b|"
    r"\b\d[\d,]{3,}\s?(?:rs|rupees?)?\b",
    re.IGNORECASE,
)

# Time anchor — "by August", "in 6 months", "next year", "2026", "Q3", "December".
_TIME_ANCHOR_RE = re.compile(
    r"\bby\s+(?:\d{1,2}[\s/-]\w+|\w+\s+\d{4}|next\s+\w+|\w+day|"
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)|"
    r"\bin\s+\d+\s+(?:day|week|month|year)s?|"
    r"\bnext\s+(?:week|month|year|quarter)|"
    r"\b20\d{2}\b|\bQ[1-4]\b",
    re.IGNORECASE,
)


def detect_ambiguous_goal(message: str) -> str | None:
    """Return a canned clarifying question when the ask is obviously incomplete.

    Returns:
        A short question string if the ambiguity is unambiguous (yes, really),
        or None if the LLM should handle it.

    This is intentionally conservative — we only short-circuit when we are
    highly confident. Anything fuzzy falls through to the LLM, which has its
    own clarifying-question rules in the persona.
    """
    if not message:
        return None
    msg = message.strip()

    # 1. Pure aspirational asks with no anchor.
    if _VAGUE_ASPIRATION_RE.search(msg) and not _AMOUNT_RE.search(msg):
        return (
            "Happy to help. What's the concrete target — a specific goal "
            "(emergency fund, trip, down payment, a bill to clear) or a "
            "monthly savings rate you're aiming for?"
        )

    # 2. Goal-verb asks with no amount AND no time anchor.
    #    e.g. "help me save for a car" — we don't know size or horizon.
    has_goal_verb = re.search(_GOAL_VERBS, msg, re.IGNORECASE)
    has_amount = _AMOUNT_RE.search(msg)
    has_time = _TIME_ANCHOR_RE.search(msg)
    # Require the message to look like a goal request (contains the word "for"
    # or a direct object after the verb) before short-circuiting, so single
    # words like "save" don't get swallowed by this filter.
    looks_like_goal_ask = bool(re.search(r"\bsave\s+for\b|\bplan\s+for\b|\bbuy\s+\w|\bget\s+(?:a|an)\s+\w|\bpay\s+off\s+\w", msg, re.IGNORECASE))

    if has_goal_verb and looks_like_goal_ask and not has_amount and not has_time:
        return (
            "Sure — what's the rough target amount and by when? Even a "
            "ballpark (e.g. \"₹50k in 6 months\") is enough to set up a plan."
        )

    return None


def get_ambiguous_goal_response(question: str) -> str:
    """Wrap `detect_ambiguous_goal` output in the simple-mode JSON envelope."""
    import json
    clarifier = detect_ambiguous_goal(question) or (
        "Could you share a bit more detail? Either the target amount, the "
        "deadline, or which goal you mean."
    )
    return json.dumps({"mode": "simple", "content": clarifier})


def get_fallback_response() -> str:
    """Returns a simple-mode reply for off-topic queries.

    Note: this is only used on the FIRST turn with no prior conversation —
    mid-chat follow-ups always route to the LLM so TORA can stay in thread.
    """
    import json
    return json.dumps({
        "mode": "simple",
        "content": "I'm built for personal finance — spending, budgets, savings goals, loans, and tax. What would you like to look at? You could try *\"analyze my spending this month\"* or *\"help me plan for a ₹50,000 goal by August\"*."
    })
