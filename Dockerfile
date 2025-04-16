FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libmagic1 \
    && apt-get clean


RUN pip install poetry


COPY . .


RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

EXPOSE 80


CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
