# Link the Vercel Chatbot to Your Local LLM

The hosted Vercel app cannot call `localhost` on your laptop. From the browser, `localhost` means the visitor's device, not your machine. To connect `https://spendsy-fintech.vercel.app` to your local Ollama-backed TORA service, expose TORA through an HTTPS tunnel and point Vercel to that URL.

## 1. Run Ollama

```powershell
ollama serve
ollama pull gemma:2b
```

Use whatever model you configured in `MODEL_GEMMA` / `MODEL_LLAMA`.

## 2. Run Spendsy locally

```powershell
.\run-local.ps1
```

With the Docker dev setup, TORA is exposed on:

```text
http://localhost:8004
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8004/health
```

If you run `backend/spendsy-ai/main.py` directly with uvicorn, use `http://localhost:8005` instead.

## 3. Create an HTTPS tunnel to TORA

Open a second PowerShell window for the tunnel. `run-local.ps1` keeps running so it can stream logs and keep Vite alive.

Cloudflare Tunnel example:

```powershell
cloudflared tunnel --url http://localhost:8004
```

Or ngrok:

```powershell
ngrok http 8004
```

Copy the generated `https://...` URL.

## 4. Configure Vercel

In Vercel project settings, add:

```text
VITE_TORA_URL=https://your-tunnel-url
```

Redeploy the frontend after changing this variable.

## 5. Configure local CORS

In your local `.env`, make sure the hosted app is allowed:

```text
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000,http://127.0.0.1:8080,https://spendsy-fintech.vercel.app
```

Restart TORA after changing `.env`.

## Request Flow

```text
Vercel frontend -> HTTPS tunnel -> local TORA FastAPI -> local Ollama
```

Keep your laptop, Ollama, Spendsy services, and the tunnel running while testing the hosted chatbot.
