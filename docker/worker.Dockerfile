FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir fastapi uvicorn pydantic sqlalchemy psycopg aiosqlite httpx python-dotenv boto3

CMD ["python", "scripts/seed_demo.py"]
