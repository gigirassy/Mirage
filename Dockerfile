FROM python:3.11-slim

WORKDIR /app

# system deps for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000
CMD ["gunicorn", "-b", "0.0.0.0:3000", "app:app", "--workers", "2"]
