FROM python:3.11-slim

WORKDIR /app

# Copy only the requirements file first so Docker caches the pip install
# layer - code changes won't force a slow reinstall of unchanged dependencies.
COPY services/user_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code and this service's code. common/ is duplicated into
# every service's image because each container is independent - there is
# no shared filesystem between services in production.
COPY common ./common
COPY services/__init__.py ./services/__init__.py
COPY services/user_service ./services/user_service

# Lets "from common.auth import ..." and "from services.user_service.x
# import ..." resolve no matter what directory uvicorn is invoked from.
ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "services.user_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
