FROM python:3.11-slim

WORKDIR /app

COPY services/flight_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY services/__init__.py ./services/__init__.py
COPY services/flight_service ./services/flight_service

ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "services.flight_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
