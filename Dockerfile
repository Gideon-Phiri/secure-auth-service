FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN groupadd -r vscode && useradd -r -g vscode -m -s /bin/bash vscode

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/* && \
    chown -R vscode:vscode /app

USER vscode

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
