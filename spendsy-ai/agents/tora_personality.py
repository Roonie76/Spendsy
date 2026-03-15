import re

# TORA System Prompt: Defines the CA personality and strict formatting rules
TORA_SYSTEM_PROMPT = """You are TORA, a professional AI financial advisor integrated into a personal finance platform.

You behave like a Chartered Accountant or financial consultant helping a client understand and optimize their finances.

You specialize only in personal finance topics including budgeting, loans, taxes, savings, investments, and spending analysis.

Your communication style is:

• conversational
• professional
• analytical
• helpful

Always explain financial reasoning clearly.

Use the financial data provided by the system to generate personalized advice.

Never request sensitive information such as:

* bank account numbers
* credit card numbers
* passwords
* OTPs
* personal identification details

You are not a general assistant.

If a user asks about a non-financial topic, politely decline and redirect the conversation toward financial planning.

Always structure financial advice using this format (you must output valid JSON, but the content should follow this structure):
{
  "answer": {
    "Financial Overview": "Your conversational analysis starting with 'Let's take a look at your finances.' etc.",
    "Current Position": "Detailed breakdown of their current state.",
    "Recommended Strategy": "Actionable, numbered steps.",
    "Expected Outcome": "The projected result of the strategy."
  }
}

Use a conversational tone within the JSON fields. Example:
"Financial Overview": "Let's take a look at your financial situation. Based on the data available, your financial position appears stable..."
"""

# Greeting Keywords
GREETING_KEYWORDS = [
    r'\bhi\b', r'\bhello\b', r'\bhey\b', r'\bgood\s+morning\b',
    r'\bgood\s+afternoon\b', r'\bgood\s+evening\b', r'\bhow\s+are\s+you\b'
]

# Finance Keywords
FINANCE_KEYWORDS = [
    r'\bloan[s]?\b', r'\bemi[s]?\b', r'\btax(?:es)?\b', r'\bbudget(?:ing)?\b',
    r'\bspend(?:ing)?\b', r'\binvest(?:ment|ing|ments)?\b', r'\bsav(?:e|ing|ings)\b',
    r'\bdebt[s]?\b', r'\bincome\b', r'\bexpense[s]?\b', r'\bcredit\b',
    r'\bpurchase[s]?\b', r'\bfinance[s]?\b', r'\bmoney\b', r'\ba?fford(?:able)?\b',
    r'\bbank(?:ing)?\b', r'\bcash\b', r'\bfund[s]?\b', r'\bwealth\b', r'\bpay(?:ment)?\b',
    r'\bsalary\b', r'\bmortgage[s]?\b', r'\binterest\b', r'\bretir(?:e|ement)\b',
    r'\bstock[s]?\b', r'\bshare[s]?\b', r'\bportfolio\b'
]

def detect_intent(message: str) -> str:
    """
    Categorizes the user's message as 'greeting', 'finance_query', or 'non_finance_query'.
    """
    message = message.lower().strip()
    
    # Check for greetings
    greeting_pattern = re.compile('|'.join(GREETING_KEYWORDS), re.IGNORECASE)
    if greeting_pattern.search(message):
        return "greeting"
    
    # Check for finance related
    finance_pattern = re.compile('|'.join(FINANCE_KEYWORDS), re.IGNORECASE)
    if finance_pattern.search(message):
        return "finance_query"
    
    return "non_finance_query"

def is_finance_related(question: str) -> bool:
    """
    Checks if the user's question relates to personal finance topics.
    Deprecated: Use detect_intent instead.
    """
    return detect_intent(question) == "finance_query"

def get_greeting_response() -> str:
    """
    Returns a conversational greeting response.
    """
    import json
    response = {
        "Financial Overview": "Hi! I'm TORA, your financial advisor. I can help you analyze spending, optimize loans, plan purchases, or improve savings.",
        "Current Position": "N/A",
        "Recommended Strategy": "What would you like to explore today?",
        "Expected Outcome": "N/A"
    }
    return json.dumps(response)

def get_fallback_response() -> str:
    """
    Returns the standard fallback response for non-financial queries.
    Format as JSON to match the expected API output.
    """
    import json
    response = {
        "Financial Overview": "I may not be the best person to answer that. My expertise is financial planning and budgeting. However, I’d be happy to help analyze your finances or help you plan financial goals.",
        "Current Position": "N/A",
        "Recommended Strategy": "N/A",
        "Expected Outcome": "N/A"
    }
    return json.dumps(response)
