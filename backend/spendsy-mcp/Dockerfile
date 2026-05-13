FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV MCP_TRANSPORT=sse
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8006
ENV FASTMCP_SSE_PATH=/mcp/sse
ENV FASTMCP_MESSAGE_PATH=/mcp/messages
ENV PIP_DEFAULT_TIMEOUT=180
ENV PIP_RETRIES=10
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=180 --retries=10 -r requirements.txt

COPY backend/spendsy-mcp/ ./

EXPOSE 8006

CMD ["python", "server.py"]
