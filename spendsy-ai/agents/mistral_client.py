import json
import logging
import os
import urllib.request
import urllib.error
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

def call_mistral(prompt: str, context: Dict[str, Any]) -> str:
    """
    Execute the HTTP call to the Mistral AI API using mistral-small-latest.
    """
    api_key = settings.mistral_api_key or os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        # Defaulting to a simulated response if no API key is present for development
        logger.warning("MISTRAL_API_KEY not set, returning simulated response")
        return json.dumps({
            "answer": {
                "Financial Overview": "Mistral (Simulated): I've analyzed your financial state. You are maintaining a healthy balance.",
                "Current Position": "Based on your recent transactions, your liquidity is stable.",
                "Recommended Strategy": "Consider diversifying your savings into a high-yield account.",
                "Expected Outcome": "Increased passive income from interest over the next quarter."
            },
            "tool_calls": []
        })
        
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Mistral expects a messages format
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": "You are TORA, a helpful financial assistant for the Spendsy app. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers, 
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30.0) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Mistral API Error ({e.code}): {error_body}")
        raise RuntimeError(f"Mistral API Error ({e.code}): {error_body}")
    except Exception as e:
        logger.error(f"Mistral request failed: {str(e)}")
        raise RuntimeError(f"Mistral request failed: {str(e)}")
