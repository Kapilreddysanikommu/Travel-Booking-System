FROM python:3.11-slim

WORKDIR /app

COPY services/billing_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY services/__init__.py ./services/__init__.py
COPY services/billing_service ./services/billing_service

ENV PYTHONPATH=/app

EXPOSE 8004

CMD ["uvicorn", "services.billing_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
