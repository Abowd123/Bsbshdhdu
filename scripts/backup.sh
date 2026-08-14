#!/bin/bash
# نسخ احتياطي لقاعدة البيانات وملفات البوتات، مع رفع اختياري إلى
# Lightsail Object Storage (S3-compatible) إن كانت متغيرات .env مضبوطة.
set -euo pipefail
cd "$(dirname "$0")/.."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

set -a
source .env
set +a

DB_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"
BOTS_FILE="$BACKUP_DIR/bots_storage_${TIMESTAMP}.tar.gz"

echo "نسخ احتياطي لقاعدة بيانات PostgreSQL..."
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$DB_FILE"

echo "نسخ احتياطي لملفات البوتات (volume: bots_storage)..."
docker compose run --rm backup_util \
  tar czf "/backup/$(basename "$BOTS_FILE")" -C /data .

echo "النسخ المحلية جاهزة:"
echo "  - $DB_FILE"
echo "  - $BOTS_FILE"

# ===== رفع اختياري إلى Lightsail Object Storage (S3-compatible) =====
if [ -n "${LIGHTSAIL_BUCKET_NAME:-}" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "تحذير: أداة aws CLI غير مثبتة — سيتم الاحتفاظ بنسخة محلية فقط."
    echo "لتثبيتها: sudo apt-get install -y awscli"
  else
    export AWS_ACCESS_KEY_ID="${LIGHTSAIL_ACCESS_KEY_ID:-}"
    export AWS_SECRET_ACCESS_KEY="${LIGHTSAIL_SECRET_ACCESS_KEY:-}"
    ENDPOINT="https://s3.${LIGHTSAIL_BUCKET_REGION}.amazonaws.com"

    echo "رفع النسخ إلى Lightsail Bucket: ${LIGHTSAIL_BUCKET_NAME} (region: ${LIGHTSAIL_BUCKET_REGION})..."
    aws s3 cp "$DB_FILE"   "s3://${LIGHTSAIL_BUCKET_NAME}/backups/$(basename "$DB_FILE")"   --endpoint-url "$ENDPOINT"
    aws s3 cp "$BOTS_FILE" "s3://${LIGHTSAIL_BUCKET_NAME}/backups/$(basename "$BOTS_FILE")" --endpoint-url "$ENDPOINT"
    echo "تم رفع النسخ الاحتياطية إلى الـ Bucket بنجاح."
  fi
else
  echo "ملاحظة: LIGHTSAIL_BUCKET_NAME غير مضبوط في .env — تم الاحتفاظ بنسخة محلية فقط."
fi

# الاحتفاظ بآخر 14 يوم محليًا فقط (يمكن ضبط دورة حياة أطول/أقصر للنسخ في الـ Bucket من AWS)
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "bots_storage_*.tar.gz" -mtime +14 -delete

echo "اكتمل النسخ الاحتياطي."
