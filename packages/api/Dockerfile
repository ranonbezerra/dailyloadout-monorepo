FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root --no-interaction

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/

RUN poetry install --without dev --no-interaction

EXPOSE 8100
CMD ["uvicorn", "src.dailyloadout.main:app", "--host", "0.0.0.0", "--port", "8100"]
