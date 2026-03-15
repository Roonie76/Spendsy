import ollama
from config import settings
from tools import (
    get_summary, get_transactions, spending_insights, 
    subscription_detection, budget_recommendation
)



def ask_tora(question: str, user_id: int):
    """
    Retrieve financial data and ask the local DeepSeek model for insights.
    """
    # 1. Retrieve user financial data (Context retrieval)
    summary = get_summary(user_id)
    transactions = get_transactions(user_id, limit=50) # Cap at 50 for context
    insights = spending_insights(user_id)
    subs = subscription_detection(user_id)
    budget = budget_recommendation(user_id)

    # 2. Build the system command/prompt
    prompt = f"""
You are Tora, a specialized financial assistant for the Spendsy platform. 
Your goal is to provide clear, actionable financial advice based ONLY on the user's data.

### USER FINANCIAL CONTEXT (User ID: {user_id})
- **Summary**: {summary}
- **Insights**: {insights}
- **Top Transactions (Recent 50)**: {transactions}
- **Recurring Subscriptions**: {subs}
- **Budget Advice**: {budget}

### INSTRUCTIONS
- Use the data above to answer the user's question.
- Be precise with numbers.
- If the data is missing or erroring, inform the user politely.
- Use a helpful, professional, and encouraging tone.

### USER QUESTION
"{question}"

Provide your reasoning and then the final answer.
"""

    try:
        # 3. Call local Ollama instance
        response = ollama.chat(
            model=settings.tora_model,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Tora error: I'm having trouble connecting to my local brain (Ollama). details: {str(e)}"
