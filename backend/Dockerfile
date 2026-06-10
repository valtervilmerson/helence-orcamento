FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

# A Railway injeta a porta via $PORT (docs/09, seção 11.2).
# `python -m app.db.migrate` será adicionado ao start command quando
# as migrations forem implementadas (docs/07, Fase 1).
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
