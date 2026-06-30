FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium ca-certificates curl \
    fonts-liberation fonts-noto-cjk fonts-noto-color-emoji fontconfig \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY image_full.py start.sh ./
RUN chmod +x start.sh && mkdir -p temp_gateway_uploads

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s \
    CMD curl -fsS http://localhost:7860/health || exit 1
CMD ["/app/start.sh"]
