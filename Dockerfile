FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ⚠️ SIN --no-install-recommends, y con TODAS las libs que Chromium necesita
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    wget curl unzip ca-certificates \
    libnss3 libatk-bridge2.0-0 libatk1.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    libcups2 libdbus-1-3 libglib2.0-0 libx11-6 libxcb1 \
    libxext6 libxi6 libxtst6 libexpat1 \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1
# ⚠️ Evita el crash por /dev/shm pequeño (clásico en contenedores)
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/temp /app/descargas

EXPOSE 10000

CMD ["python", "bot.py"]
