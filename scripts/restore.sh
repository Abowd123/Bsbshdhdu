#!/bin/bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <db_backup.sql.gz> <bots_storage_backup.tar.gz>"
  exit 1
fi

DB_BACKUP="$1"
STORAGE_BACKUP="$2"

cd "$(dirname "$0")/.."
source .env

echo "Restoring PostgreSQL database from $DB_BACKUP..."
gunzip -c "$DB_BACKUP" | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"

echo "Restoring bots storage volume from $STORAGE_BACKUP..."
cp "$STORAGE_BACKUP" "./backups/_restore_tmp.tar.gz"
docker compose run --rm backup_util \
  sh -c "rm -rf /data/* && tar xzf /backup/_restore_tmp.tar.gz -C /data"
rm -f "./backups/_restore_tmp.tar.gz"

echo "Restore completed. Restart services with: docker compose restart"
