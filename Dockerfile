FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Chromium + ChromeDriver + LibreOffice
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    wget \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/temp /app/descargas

EXPOSE 10000

CMD ["python", "bot.py"]
