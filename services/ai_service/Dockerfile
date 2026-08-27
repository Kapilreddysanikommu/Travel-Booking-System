FROM python:3.11-slim

WORKDIR /app

COPY services/ai_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY services/__init__.py ./services/__init__.py
COPY services/ai_service ./services/ai_service

ENV PYTHONPATH=/app

EXPOSE 8006

CMD ["uvicorn", "services.ai_service.main:app", "--host", "0.0.0.0", "--port", "8006"]
