# This is just a basic dockerfile you can play with this docker file as you please!

FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# PYTHONPATH'i ayarla
ENV PYTHONPATH=/app

# Uygulamayı çalıştır
CMD ["python", "src/api.py"]
