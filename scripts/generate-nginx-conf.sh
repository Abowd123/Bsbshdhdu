#!/bin/bash
# يولّد nginx/nginx.conf من nginx/nginx.conf.template باستبدال ${DOMAIN_NAME} فقط
# (لا يلمس متغيرات nginx الداخلية مثل $host أو $remote_addr)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "ملف .env غير موجود." >&2
  exit 1
fi

set -a
source .env
set +a

: "${DOMAIN_NAME:?يجب تحديد DOMAIN_NAME في .env (اسم الدومين الذي سيشير إلى Lightsail Static IP)}"

if ! command -v envsubst >/dev/null 2>&1; then
  echo "الأداة envsubst غير مثبتة. ثبّتها بالأمر: sudo apt-get install -y gettext-base" >&2
  exit 1
fi

envsubst '${DOMAIN_NAME}' < nginx/nginx.conf.template > nginx/nginx.conf

echo "تم توليد nginx/nginx.conf للدومين: $DOMAIN_NAME"
