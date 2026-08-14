#!/bin/bash
# سكربت مخصص للتشغيل الدوري (cron) لتجديد شهادة SSL تلقائيًا.
# Certbot يجدد فقط الشهادات القريبة من الانتهاء (أقل من 30 يوم)، لذا يمكن
# تشغيل هذا السكربت يوميًا بأمان دون أي تأثير إن لم يحن وقت التجديد بعد.
#
# مثال لإضافته لـ crontab (تشغيل يوميًا الساعة 3 صباحًا):
#   0 3 * * * cd /home/ubuntu/wolfhost && bash scripts/renew-ssl.sh >> /home/ubuntu/wolfhost/logs/renew-ssl.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose run --rm certbot renew --webroot -w /var/www/certbot --quiet

docker compose exec nginx nginx -s reload

echo "[$(date '+%Y-%m-%d %H:%M:%S')] فحص/تجديد شهادة SSL تم بنجاح."
