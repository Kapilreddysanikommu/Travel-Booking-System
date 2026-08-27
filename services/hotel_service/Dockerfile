FROM python:3.11-slim

WORKDIR /app

COPY services/hotel_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY services/__init__.py ./services/__init__.py
COPY services/hotel_service ./services/hotel_service

ENV PYTHONPATH=/app

EXPOSE 8003

CMD ["uvicorn", "services.hotel_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
