#!/usr/bin/env bash
# Sauvegarde quotidienne de la base Postgres du projet.
#
# A executer depuis la racine du projet (la ou se trouve docker-compose.yml).
# Cree un dump compresse dans ./backups/ et supprime les dumps de plus de
# BACKUP_RETENTION_DAYS jours (14 par defaut).
#
# Installation recommandee sur le serveur (crontab -e) :
#   0 3 * * * cd /chemin/vers/le/projet && ./docker/backup.sh >> logs/backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."

RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_DIR="./backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ -z "${DB_NAME:-}" ] || [ -z "${DB_USER:-}" ]; then
  echo "DB_NAME et DB_USER doivent etre definis (via .env ou l'environnement)." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

DUMP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"
echo "Sauvegarde de la base '$DB_NAME' vers $DUMP_FILE ..."

docker-compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$DUMP_FILE"

echo "Sauvegarde terminee : $(du -h "$DUMP_FILE" | cut -f1)"

echo "Suppression des sauvegardes de plus de $RETENTION_DAYS jours ..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete

echo "OK."
