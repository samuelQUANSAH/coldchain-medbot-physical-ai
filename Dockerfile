FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=7860

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY infrastructure/ ./infrastructure/
COPY docs/ ./docs/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . uvicorn

EXPOSE 7860

CMD ["uvicorn", "coldchain_medbot.api.server:app", "--host", "0.0.0.0", "--port", "7860"]
