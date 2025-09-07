FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml poetry.lock* requirements.txt* README.md srsbot ./

RUN set -eux; \
    if [ -f "pyproject.toml" ]; then \
      pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi; \
    elif [ -f "requirements.txt" ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

CMD ["python", "-m", "srsbot.main"]

