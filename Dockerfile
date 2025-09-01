FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user 'meltah' for security
RUN groupadd -r meltah && useradd -r -g meltah -m -s /bin/bash meltah

RUN mkdir -p /app \
    && chown -R meltah:meltah /app

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl git && \
    rm -rf /var/lib/apt/lists/* && \
    chown -R meltah:meltah /app

USER meltah

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY . .



EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
