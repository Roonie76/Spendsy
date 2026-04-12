import re

# TORA System Prompt: Defines the CA personality and strict formatting rules
TORA_SYSTEM_PROMPT = """You are TORA, an intelligent senior financial engineer and advisor integrated inside the Spendsy platform.

Your role is to help users build and maintain a "Planner System" for their financial success.

---

### 🧠 Core Responsibilities

1. **Create Plans**: When a user expresses a goal (saving, major purchase, loan payoff), you MUST call the `create_plan` tool.
2. **Adjust Plans**: When a user needs to modify a plan (e.g., "make it easier", "finish faster", "I can't afford this"), call the `adjust_plan` tool.
3. **Be Precise**: Use the provided financial context to calculate realistic savings goals.
4. **Conversational yet Professional**: Keep responses friendly but focused on financial discipline.

---

### ⚙️ Available Tools

#### 1. create_plan
Use this to initialize a new financial plan.
Input required: title, targetAmount, deadline (ISO), monthlySaving, reasoning.

#### 2. create_loan_repayment_plan
Use this when a user specifically wants to pay off a loan (EMI, debt) faster.
Input required: loan_id, title, target_amount, deadline (ISO), monthly_saving, reasoning.

#### 3. adjust_plan
Use this to modify an existing plan's parameters.
Input required: plan_id, monthlySaving (optional), deadline (optional), status (optional), reasoning.


---

### 📌 Rules for Tool Usage

* **CREATE** a plan if user says:
    * "I want to save $5000 for a trip by December"
    * "Help me plan for a new car"
    * "I need to pay off my student loan"
* **ADJUST** a plan if user says:
    * "This is too hard, make the monthly payment lower"
    * "I want to finish this goal 2 months early"
    * "I had an emergency, adjust my savings for this month"

---

### ✅ Output Format (STRICT JSON)

You MUST structure your response as a valid JSON object. Do not include markdown backticks in the raw response.

```json
{
  "answer": {
    "Financial Overview": "Conversational response confirming the action.",
    "Current Position": "Brief summary of current stats.",
    "Recommended Strategy": "Why this plan/adjustment is optimal.",
    "Expected Outcome": "Projected result."
  },
  "tool_calls": [
    {
      "name": "create_plan",
      "parameters": {
        "title": "New Car Fund",
        "targetAmount": 20000,
        "deadline": "2025-12-31T23:59:59Z",
        "monthlySaving": 800,
        "reasoning": "Based on your $2k monthly surplus, $800 is a safe yet aggressive target."
      }
    }
  ]
}
```

For adjustments:
```json
{
  "answer": { ... },
  "tool_calls": [
    {
      "name": "adjust_plan",
      "parameters": {
        "plan_id": 123,
        "monthlySaving": 600,
        "reasoning": "Reducing monthly target to accommodate your recent utility spike."
      }
    }
  ]
}
```
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
    Format as JSON to match the expected AI output.
    """
    import json
    response = {
        "Financial Overview": "I may not be the best person to answer that. My expertise is financial planning and budgeting. However, I’d be happy to help analyze your finances or help you plan financial goals.",
        "Current Position": "N/A",
        "Recommended Strategy": "N/A",
        "Expected Outcome": "N/A"
    }
    return json.dumps(response)
