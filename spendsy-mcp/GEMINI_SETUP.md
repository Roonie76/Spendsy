# Gemini: Spendsy Financial Assistant Setup

To use the Spendsy Financial Assistant with Gemini, follow these steps.

### Prerequisites
1.  **Google Gemini API Key**: Get one from [Google AI Studio](https://aistudio.google.com/).
2.  **User ID**: Know your Spendsy `USER_ID` (default is `1` for development).

### Steps
1.  **Set Environment Variables**:
    ```bash
    export GOOGLE_API_KEY='your-gemini-api-key'
    export SPENDSY_USER_ID=1
    ```

2.  **Run the Gemini Client**:
    Open a terminal, activate the root virtual environment, and run the client:
    ```bash
    cd /home/rohinvengatesh04/Spendsy/Spendsy
    source .venv/bin/activate
    python3 spendsy-mcp/gemini_client.py
    ```

3.  **Interact with Gemini**:
    You can now ask questions like:
    - "Show me my latest transactions."
    - "Can I afford to buy a house for 80 lakhs?"
    - "Analyze my spending trends for the last 3 months."

### Important Notes
-   The client uses the `gemini-2.0-flash` model for fast, accurate financial analysis.
-   It automatically calls the relevant tools built into the Spendsy MCP server.
