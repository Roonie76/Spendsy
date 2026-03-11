import os
import asyncio
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
USER_ID = int(os.getenv("SPENDSY_USER_ID", "1")) # Default to user 1 for dev

if not GOOGLE_API_KEY:
    print("❌ Error: GOOGLE_API_KEY not found in environment.")
    print("Please set it: export GOOGLE_API_KEY='your-key-here'")
    exit(1)

client = genai.Client(api_key=GOOGLE_API_KEY)

# Tool Definitions (Mapping from MCP tools)
# Note: For a production app, these would be dynamically pulled from the MCP server.
# For this client, we define the primary tools Gemini can use.

def get_summary(user_id: int) -> str:
    # This will be replaced by actual MCP call logic if we were using a full MCP client.
    # For now, we'll implement a simple bridge or instructions.
    pass

# Direct bridge to Spendsy MCP tools
# Since we are running the MCP server locally, we can call its functions if imported, 
# or better, use the requests-based logic we already have in server.py as a temporary bridge 
# if we don't want to run a full MCP client-server loop in this simple script.

from server import (
    get_summary, get_transactions, monthly_spend, 
    spending_by_category, top_merchants, spending_insights,
    detect_duplicate_transactions, budget_recommendation,
    spending_trend_analysis, get_full_financial_context,
    simulate_loan_closure, simulate_house_purchase
)

tools = [
    get_summary, get_transactions, monthly_spend,
    spending_by_category, top_merchants, spending_insights,
    detect_duplicate_transactions, budget_recommendation,
    spending_trend_analysis, get_full_financial_context,
    simulate_loan_closure, simulate_house_purchase
]

def chat():
    print("🚀 Spendsy Gemini Assistant Started!")
    print("Ask me anything about your finances (e.g., 'What was my spend last month?')")
    print("Type 'exit' to quit.\n")
    
    # Initialize chat with tools
    chat_session = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            tools=tools,
            system_instruction=f"You are Spendsy AI, a helpful financial assistant. You have access to the user's financial data for user_id={USER_ID}. Always use the provided tools to answer financial questions accurately. If a user asks about complex planning like buying a house or closing a loan, use the simulation tools."
        )
    )
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        try:
            response = chat_session.send_message(user_input)
            print(f"\nGemini: {response.text}\n")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    chat()
