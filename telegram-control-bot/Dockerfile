FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY telegram-control-bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram-control-bot/bot ./bot

# لا نحتاج أي منفذ مكشوف — البوت يعمل بـ Long Polling فقط (لا يستقبل اتصالات واردة)
CMD ["python", "-m", "bot.main"]
