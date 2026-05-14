FROM glm-ocr:latest

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY backend/document-parser/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 -r requirements.txt

COPY backend/document-parser/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
