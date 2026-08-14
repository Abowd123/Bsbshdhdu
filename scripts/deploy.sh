#!/bin/bash
# سكربت نشر Wolf Host (+ telegram-control-bot) على AWS Lightsail
# (Ubuntu 22.04 أو 24.04, بدون Kubernetes — Docker Compose فقط).
#
# الاستخدام:
#   1. انسخ .env.example إلى .env واملأ القيم (خصوصًا DOMAIN_NAME وCERTBOT_EMAIL
#      وTELEGRAM_BOT_TOKEN وكل كلمات المرور).
#   2. تأكد إن الدومين يشير إلى Static IP الخاص بـ Lightsail (DNS A record).
#   3. تأكد إن منافذ 22/80/443 فقط مفتوحة في تبويب Networking بلوحة Lightsail.
#   4. شغّل: bash scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

install_docker_if_missing() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "Docker + Docker Compose plugin موجودان بالفعل."
    return
  fi

  echo "تثبيت Docker Engine و Docker Compose plugin..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg gettext-base

  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  sudo usermod -aG docker "$USER" || true
  echo "تم تثبيت Docker. إن ظهرت مشاكل صلاحيات لاحقًا، سجّل خروج/دخول من جديد حتى تُفعّل عضوية مجموعة docker."
}

install_docker_if_missing

if [ ! -f .env ]; then
  echo "ملف .env غير موجود. انسخ .env.example إلى .env واملأ القيم أولاً:"
  echo "  cp .env.example .env && nano .env"
  exit 1
fi

set -a
source .env
set +a

: "${DOMAIN_NAME:?يجب تحديد DOMAIN_NAME في .env (الدومين الذي يشير إلى Lightsail Static IP)}"
: "${CERTBOT_EMAIL:?يجب تحديد CERTBOT_EMAIL في .env}"
: "${POSTGRES_USER:?يجب تحديد POSTGRES_USER في .env}"

echo "توليد إعدادات nginx للدومين: ${DOMAIN_NAME}..."
bash scripts/generate-nginx-conf.sh

echo "بناء جميع صور الخدمات (backend, frontend, celery, telegram_control_bot)..."
docker compose build

echo "تشغيل PostgreSQL و Redis أولاً..."
docker compose up -d postgres redis

echo "انتظار جاهزية قاعدة البيانات..."
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER}" >/dev/null 2>&1; do
  printf '.'
  sleep 2
done
echo " جاهزة."

echo "تنفيذ الترحيلات (alembic) وبيانات البذر..."
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed

echo "تشغيل الخدمات الأساسية (backend, celery_worker, celery_beat, frontend, telegram_control_bot)..."
docker compose up -d backend celery_worker celery_beat frontend telegram_control_bot

echo "التأكد من صحة backend قبل تشغيل nginx..."
for i in $(seq 1 30); do
  if docker compose exec -T backend curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "إعداد شهادة SSL (Let's Encrypt) عبر Certbot إن لم تكن موجودة بعد..."
bash scripts/init-ssl.sh

echo ""
echo "تم النشر بنجاح."
echo "  - تحقق من حالة الخدمات: docker compose ps"
echo "  - الموقع يجب أن يكون متاحًا الآن على: https://${DOMAIN_NAME}"
echo "  - لا تنسَ جدولة تجديد SSL التلقائي والنسخ الاحتياطي عبر crontab"
echo "    (راجع خطوات النشر اليدوية في الرد لتفاصيل الأوامر بالضبط)."
