FROM python:3.11-slim

WORKDIR /app

COPY services/notification_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/__init__.py ./services/__init__.py
COPY services/notification_service ./services/notification_service

ENV PYTHONPATH=/app

EXPOSE 8005

CMD ["uvicorn", "services.notification_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
