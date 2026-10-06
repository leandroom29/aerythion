FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api ./api
COPY config ./config
COPY data/raw ./data/raw
COPY data/processed ./data/processed
COPY data/output ./data/output
RUN useradd --create-home --shell /usr/sbin/nologin airquality \
    && chown -R airquality:airquality /app
USER airquality

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
