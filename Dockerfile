FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PREFIX=/ecosystem-map

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir flask gunicorn
RUN python -m app.demo
EXPOSE 5057
CMD ["gunicorn", "--bind", "0.0.0.0:5057", "app.main:app"]
