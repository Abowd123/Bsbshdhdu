#!/bin/bash
# يحصل على أول شهادة SSL حقيقية من Let's Encrypt لدومين المشروع.
# آمن للتشغيل أكثر من مرة: إذا كانت الشهادة الحقيقية موجودة بالفعل لا يفعل شيئًا.
#
# آلية العمل:
#  1. لو مفيش شهادة أصلاً: يُنشئ شهادة وهمية (self-signed) مؤقتة حتى يقدر nginx
#     يبدأ أصلاً (بما إن ملف nginx.conf يشير لمسار الشهادة دايمًا).
#  2. يشغّل nginx بهذه الشهادة المؤقتة.
#  3. يحذف الشهادة الوهمية ويطلب شهادة حقيقية من Let's Encrypt عبر HTTP-01
#     (webroot) على المنفذ 80.
#  4. يعمل reload لـ nginx ليستخدم الشهادة الحقيقية.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "ملف .env غير موجود." >&2
  exit 1
fi

set -a
source .env
set +a

: "${DOMAIN_NAME:?يجب تحديد DOMAIN_NAME في .env}"
: "${CERTBOT_EMAIL:?يجب تحديد CERTBOT_EMAIL في .env (بريد لتنبيهات انتهاء الشهادة)}"

CERT_LIVE_PATH="/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem"

# الشهادة الوهمية المؤقتة صالحة ليوم واحد فقط، بينما شهادة Let's Encrypt الحقيقية
# صالحة 90 يومًا. لذلك نتحقق أن الشهادة الحالية (إن وجدت) ستظل صالحة بعد يومين
# على الأقل، للتمييز بين الوهمية والحقيقية دون الاعتماد على قراءة نص المُصدر.
echo "التحقق من وجود شهادة SSL حقيقية سابقة لـ ${DOMAIN_NAME}..."
if docker compose run --rm --entrypoint sh certbot -c "test -f '${CERT_LIVE_PATH}' && openssl x509 -in '${CERT_LIVE_PATH}' -noout -checkend 172800" >/dev/null 2>&1; then
  echo "توجد شهادة حقيقية بالفعل لـ ${DOMAIN_NAME}. لن يتم طلب شهادة جديدة (لتجنب حدود Let's Encrypt)."
  echo "لتجديد الشهادة استخدم: bash scripts/renew-ssl.sh"
  exit 0
fi

echo "لا توجد شهادة حقيقية بعد. بدء إجراء الحصول على شهادة SSL جديدة لـ ${DOMAIN_NAME}..."

echo "1) إنشاء شهادة وهمية مؤقتة حتى يقدر nginx يبدأ..."
docker compose run --rm --entrypoint sh certbot -c "
  set -e
  mkdir -p '/etc/letsencrypt/live/${DOMAIN_NAME}'
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '/etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem' \
    -out '/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem' \
    -subj '/CN=localhost'
"

echo "2) توليد nginx.conf وتشغيل nginx بالشهادة الوهمية..."
bash scripts/generate-nginx-conf.sh
docker compose up -d nginx

echo "3) حذف الشهادة الوهمية وطلب شهادة حقيقية عبر HTTP-01 (webroot)..."
docker compose run --rm --entrypoint sh certbot -c "
  rm -rf '/etc/letsencrypt/live/${DOMAIN_NAME}' \
         '/etc/letsencrypt/archive/${DOMAIN_NAME}' \
         '/etc/letsencrypt/renewal/${DOMAIN_NAME}.conf'
"

docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "${DOMAIN_NAME}" \
  --email "${CERTBOT_EMAIL}" \
  --agree-tos \
  --no-eff-email \
  --non-interactive

echo "4) إعادة تحميل nginx ليستخدم الشهادة الحقيقية..."
docker compose exec nginx nginx -s reload

echo "تم! أصبح الموقع متاحًا عبر HTTPS على: https://${DOMAIN_NAME}"
