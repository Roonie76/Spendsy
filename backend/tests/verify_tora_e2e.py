import requests
import json
import time

def trigger_tora_workflow():
    url = "http://localhost:8005/ask-tora"
    payload = {
        "user_id": 1,
        "question": "Can you create a savings plan for a new high-end laptop? I'll need about ₹1,50,000 by next year. Assume I have ₹10,000 monthly surplus.",
        "tier": "pro" # Use pro to ensure tool execution is allowed
    }
    
    print(f"--- Sending request to TORA at {url} ---")
    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        print("\nTORA Response received:")
        print(json.dumps(data, indent=2))
        return data
    except Exception as e:
        print(f"Error calling TORA: {e}")
        return None

def verify_plan_in_finance_service():
    # Correct endpoint for listing plans
    url = "http://localhost:8002/internal/plans/list/1" 
    headers = {"X-Internal-API-Key": "spendsy-internal-api-key-32chars-long"}
    
    print(f"\n--- Verifying plan in Finance Service at {url} ---")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Internal API might be wrapped in a success_response { "status": "success", "data": [...] }
        resp_json = response.json()
        plans = resp_json.get("data", []) if isinstance(resp_json, dict) else resp_json
        
        if not isinstance(plans, list):
            print(f"Unexpected response format: {resp_json}")
            return False
            
        # Check if any plan was recently created by AI
        ai_plans = [p for p in plans if p.get("source") == "ai"]
        if ai_plans:
            print(f"SUCCESS: Found {len(ai_plans)} AI-created plan(s).")
            for p in ai_plans:
                print(f" - Plan: {p.get('title')}, Target: {p.get('target_amount')}, Status: {p.get('status')}")
            return True
        else:
            print("FAILURE: No AI-created plans found in the database.")
            return False
    except Exception as e:
        print(f"Error calling Finance Service: {e}")
        return False

if __name__ == "__main__":
    # Wait a bit for services to be fully ready if just started
    print("Waiting 10 seconds for services to settle...")
    time.sleep(10)
    
    tora_data = trigger_tora_workflow()
    if tora_data:
        verify_plan_in_finance_service()
