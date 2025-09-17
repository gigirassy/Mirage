FROM python:3.11-alpine

WORKDIR /app

# system deps for lxml
RUN apk add --no-cache \
    build-base \
    libxml2-dev \
    libxslt-dev \
    zlib-dev && \
    rm -rf /var/cache/apk/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000
CMD ["gunicorn", "-b", "0.0.0.0:3000", "app:app", "--workers", "2"]
