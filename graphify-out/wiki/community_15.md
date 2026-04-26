# Community 15

**23 nodes**

## Nodes
- **RuntimeError** (`` ) → gemini_client_call_gemini, llm_router_call_llm, mistral_client_call_mistral
- **gemini_client.py** (`backend/spendsy-ai/agents/gemini_client.py` L1) → gemini_client_call_gemini, backend_spendsy_ai_agents_llm_router_py
- **call_gemini()** (`backend/spendsy-ai/agents/gemini_client.py` L11) → gemini_client_rationale_12, d_projects_spendsy_backend_spendsy_ai_agents_gemini_client_py
- **Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest.** (`backend/spendsy-ai/agents/gemini_client.py` L12)
- **llm_router.py** (`backend/spendsy-ai/agents/llm_router.py` L1) → backend_spendsy_ai_agents_ollama_client_py, backend_spendsy_ai_agents_mistral_client_py, llm_router_call_llm
- **call_llm()** (`backend/spendsy-ai/agents/llm_router.py` L11) → llm_router_rationale_18, ollama_client_call_ollama, mistral_client_call_mistral
- **Route the prompt to specialized local models via Ollama with reasoning fallback.** (`backend/spendsy-ai/agents/llm_router.py` L18)
- **mistral_client.py** (`backend/spendsy-ai/agents/mistral_client.py` L1) → mistral_client_call_mistral
- **call_mistral()** (`backend/spendsy-ai/agents/mistral_client.py` L11) → mistral_client_rationale_12, d_projects_spendsy_backend_spendsy_ai_agents_mistral_client_py
- **Execute the HTTP call to the Mistral AI API using mistral-small-latest.** (`backend/spendsy-ai/agents/mistral_client.py` L12)
- **ollama_client.py** (`backend/spendsy-ai/agents/ollama_client.py` L1) → ollama_client_strip_code_fences, ollama_client_call_ollama
- **_strip_code_fences()** (`backend/spendsy-ai/agents/ollama_client.py` L14) → ollama_client_call_ollama, ollama_client_rationale_15, d_projects_spendsy_backend_spendsy_ai_agents_ollama_client_py
- **call_ollama()** (`backend/spendsy-ai/agents/ollama_client.py` L22) → ollama_client_rationale_30, d_projects_spendsy_backend_spendsy_ai_agents_ollama_client_py
- **Ollama models often wrap JSON in ```json ... ``` fences despite format=json.** (`backend/spendsy-ai/agents/ollama_client.py` L15)
- **Execute a chat completion request to the local Ollama API.      Args:         mo** (`backend/spendsy-ai/agents/ollama_client.py` L30)
- **test_ollama_integration.py** (`backend/tests/test_ollama_integration.py` L1) → test_ollama_integration_test_phi_math, test_ollama_integration_test_qwen_tools
- **test_phi_math()** (`backend/tests/test_ollama_integration.py` L15) → d_projects_spendsy_backend_tests_test_ollama_integration_py
- **test_qwen_tools()** (`backend/tests/test_ollama_integration.py` L28) → d_projects_spendsy_backend_tests_test_ollama_integration_py
- **gemini_client.py** (`backend/spendsy-ai/agents/gemini_client.py` L1) → d_projects_spendsy_backend_spendsy_ai_agents_llm_router_py
- **llm_router.py** (`backend/spendsy-ai/agents/llm_router.py` L1) → d_projects_spendsy_backend_spendsy_ai_agents_ollama_client_py, d_projects_spendsy_backend_spendsy_ai_agents_mistral_client_py, d_projects_spendsy_backend_spendsy_ai_agents_tora_agent_py
- **mistral_client.py** (`backend/spendsy-ai/agents/mistral_client.py` L1)
- **ollama_client.py** (`backend/spendsy-ai/agents/ollama_client.py` L1)
- **test_ollama_integration.py** (`backend/tests/test_ollama_integration.py` L1)
