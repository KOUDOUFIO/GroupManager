#!/usr/bin/env bash
# Gestion des installations clientes Kotiza sur un seul serveur.
#
# Chaque client a sa propre installation (base Postgres, cache, application,
# fichiers) : aucune donnee n'est partagee entre clients. Un nginx commun
# route chaque domaine vers la bonne installation et gere le HTTPS.
#
# Toutes les donnees clientes vivent dans ./clients/ (hors Git) :
#   clients/shared.env          reglages communs (SMTP, contact facturation...)
#   clients/<client>/.env       secrets et date de fin d'abonnement du client
#   clients/<client>/media/     fichiers envoyes par le client
#   clients/<client>/backups/   sauvegardes de la base du client
#   clients/nginx/              configuration nginx generee
#   clients/certbot/            certificats HTTPS
#
# Usage : docker/multi/kotiza-clients.sh <commande> [arguments]
#   init                                   Premiere installation du serveur
#   new <client> <domaine> <email> [jours] Creer un client (30 jours par defaut)
#   extend <client> <AAAA-MM-JJ>           Prolonger l'abonnement jusqu'a cette date
#   status                                 Lister les clients et leur abonnement
#   backup <client|all>                    Sauvegarder la base (garde 14 jours)
#   update                                 Reconstruire l'image et redemarrer tous les clients
#   task <client|all> <tache>              Lancer une tache : reminders (rappels de
#                                          cotisation) ou payments (paiements en attente)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLIENTS_ROOT="${KOTIZA_CLIENTS_ROOT:-$ROOT/clients}"
MULTI="$ROOT/docker/multi"
IMAGE="kotiza:latest"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
export CLIENTS_ROOT

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(docker-compose)
fi

die() { echo "Erreur : $*" >&2; exit 1; }
random_hex() { openssl rand -hex "$1"; }
env_value() { grep -E "^$2=" "$1" | tail -n 1 | cut -d= -f2-; }

proxy_compose() {
  "${COMPOSE[@]}" -p kotiza-proxy -f "$MULTI/proxy.yml" "$@"
}

client_compose() {
  local slug="$1"; shift
  local dir="$CLIENTS_ROOT/$slug"
  [ -f "$dir/.env" ] || die "client inconnu : $slug"
  CLIENT_SLUG="$slug" CLIENT_DIR="$dir" \
    "${COMPOSE[@]}" -p "kotiza-$slug" --env-file "$dir/.env" -f "$MULTI/client.yml" "$@"
}

list_clients() {
  local dir
  for dir in "$CLIENTS_ROOT"/*/; do
    [ -f "$dir/.env" ] && basename "$dir"
  done
  return 0
}

# Recree le conteneur web (nouveau .env ou nouvelle image). On supprime puis
# recree plutot que `up --force-recreate`, qui plante avec docker-compose 1.x
# sur les versions recentes de Docker (KeyError: 'ContainerConfig').
recreate_web() {
  client_compose "$1" rm -sf web
  client_compose "$1" up -d --no-deps web
}

reload_nginx() {
  proxy_compose exec -T nginx nginx -t
  proxy_compose exec -T nginx nginx -s reload
}

write_nginx_http_only() {
  local slug="$1" domain="$2"
  cat > "$CLIENTS_ROOT/nginx/$slug.conf" <<EOF
# Genere par kotiza-clients.sh (client : $slug) - phase d'obtention du certificat.
server {
    listen 80;
    server_name $domain;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 503;
    }
}
EOF
}

write_nginx_https() {
  local slug="$1" domain="$2"
  cat > "$CLIENTS_ROOT/nginx/$slug.conf" <<EOF
# Genere par kotiza-clients.sh (client : $slug).
server {
    listen 80;
    server_name $domain;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name $domain;

    ssl_certificate     /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 20M;

    location /media/ {
        alias /srv/clients/$slug/media/;
    }

    location / {
        # Resolution a la demande : nginx demarre meme si ce client est arrete.
        resolver 127.0.0.11 valid=30s;
        set \$upstream http://$slug-web:8000;
        proxy_pass \$upstream;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
}

cmd_init() {
  mkdir -p "$CLIENTS_ROOT/nginx" "$CLIENTS_ROOT/certbot/conf" "$CLIENTS_ROOT/certbot/www"
  if [ ! -f "$CLIENTS_ROOT/shared.env" ]; then
    cat > "$CLIENTS_ROOT/shared.env" <<'EOF'
# Reglages communs a tous les clients (un .env client peut les surcharger).
# Votre email : compte kotiza-support de chaque client et alertes Let's Encrypt.
KOTIZA_OPERATOR_EMAIL=

# Contact affiche quand un abonnement expire (telephone Mobile Money, email...).
KOTIZA_BILLING_CONTACT=

# Envoi des emails (mot de passe oublie, rappels de cotisation).
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=

# Suivi des erreurs (optionnel).
SENTRY_DSN=
EOF
    chmod 600 "$CLIENTS_ROOT/shared.env"
    echo "Cree : $CLIENTS_ROOT/shared.env (a completer)."
  fi
  # Refuse les domaines inconnus au lieu de servir le site d'un client au hasard.
  cat > "$CLIENTS_ROOT/nginx/00-default.conf" <<'EOF'
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    ssl_reject_handshake on;
    return 444;
}
EOF
  docker build -t "$IMAGE" "$ROOT"
  proxy_compose up -d
  echo "Serveur pret. Creez un client avec : $0 new <client> <domaine> <email>"
}

cmd_new() {
  [ $# -ge 3 ] || die "usage : new <client> <domaine> <email-admin> [jours]"
  local slug="$1" domain="$2" email="$3" days="${4:-30}"
  [[ "$slug" =~ ^[a-z0-9][a-z0-9-]{1,30}$ ]] || die "nom de client invalide (minuscules, chiffres, tirets) : $slug"
  [[ "$domain" =~ ^[A-Za-z0-9.-]+$ ]] || die "domaine invalide : $domain"
  [[ "$days" =~ ^[0-9]+$ ]] || die "nombre de jours invalide : $days"
  [ -f "$CLIENTS_ROOT/shared.env" ] || die "lancez d'abord : $0 init"
  local operator_email
  operator_email="$(env_value "$CLIENTS_ROOT/shared.env" KOTIZA_OPERATOR_EMAIL)"
  [ -n "$operator_email" ] || die "renseignez KOTIZA_OPERATOR_EMAIL dans $CLIENTS_ROOT/shared.env"
  local dir="$CLIENTS_ROOT/$slug"
  [ ! -e "$dir" ] || die "le client $slug existe deja"

  mkdir -p "$dir/media" "$dir/backups"
  local access_until
  access_until="$(date -d "+$days days" +%F)"
  cat > "$dir/.env" <<EOF
# Client : $slug - cree le $(date +%F)
DJANGO_SECRET_KEY=$(random_hex 32)
DJANGO_ALLOWED_HOSTS=$domain
CSRF_TRUSTED_ORIGINS=https://$domain
DB_NAME=kotiza
DB_USER=kotiza
DB_PASSWORD=$(random_hex 24)
KOTIZA_ACCESS_UNTIL=$access_until
SENTRY_ENVIRONMENT=$slug
EOF
  chmod 600 "$dir/.env"

  echo "Demarrage de l'installation $slug ..."
  client_compose "$slug" up -d
  local tries=0
  until client_compose "$slug" exec -T web python -c \
      "import socket; socket.create_connection(('127.0.0.1', 8000), 2)" >/dev/null 2>&1; do
    tries=$((tries + 1))
    [ "$tries" -lt 90 ] || die "l'application $slug ne demarre pas (voir : docker logs kotiza-$slug-web-1)"
    sleep 2
  done

  local operator_password client_password
  operator_password="$(random_hex 12)"
  client_password="$(random_hex 8)"
  client_compose "$slug" exec -T web python manage.py bootstrap_project --with-superuser \
    --username kotiza-support --email "$operator_email" --password "$operator_password" >/dev/null
  client_compose "$slug" exec -T web python manage.py create_client_admin \
    --username admin --email "$email" --password "$client_password" >/dev/null

  echo "Obtention du certificat HTTPS pour $domain ..."
  write_nginx_http_only "$slug" "$domain"
  reload_nginx
  local staging=()
  [ "${CERTBOT_STAGING:-0}" = "1" ] && staging=(--staging)
  proxy_compose run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot \
    -d "$domain" --email "$operator_email" --agree-tos --no-eff-email -n "${staging[@]}"
  write_nginx_https "$slug" "$domain"
  reload_nginx

  cat <<EOF

Client $slug pret : https://$domain
Abonnement valable jusqu'au $access_until.

  Compte du client  : admin / $client_password
      (a transmettre au client ; il perd l'acces si l'abonnement expire)
  Votre compte      : kotiza-support / $operator_password
      (superutilisateur, toujours actif ; a garder pour vous)

Ces mots de passe ne seront plus affiches : notez-les maintenant.
EOF
}

cmd_extend() {
  [ $# -eq 2 ] || die "usage : extend <client> <AAAA-MM-JJ>"
  local slug="$1" until_date="$2"
  local env_file="$CLIENTS_ROOT/$slug/.env"
  [ -f "$env_file" ] || die "client inconnu : $slug"
  [[ "$until_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && date -d "$until_date" >/dev/null 2>&1 \
    || die "date invalide (format AAAA-MM-JJ) : $until_date"
  if grep -q '^KOTIZA_ACCESS_UNTIL=' "$env_file"; then
    sed -i "s/^KOTIZA_ACCESS_UNTIL=.*/KOTIZA_ACCESS_UNTIL=$until_date/" "$env_file"
  else
    echo "KOTIZA_ACCESS_UNTIL=$until_date" >> "$env_file"
  fi
  recreate_web "$slug"
  echo "Abonnement de $slug prolonge jusqu'au $until_date."
}

cmd_status() {
  local today slug env_file domain access_until state days
  today="$(date +%F)"
  printf '%-20s %-32s %-12s %-10s %s\n' CLIENT DOMAINE "FIN ABO" JOURS ETAT
  for slug in $(list_clients); do
    env_file="$CLIENTS_ROOT/$slug/.env"
    domain="$(env_value "$env_file" DJANGO_ALLOWED_HOSTS)"
    access_until="$(env_value "$env_file" KOTIZA_ACCESS_UNTIL)"
    if [ -n "$access_until" ]; then
      days=$(( ($(date -d "$access_until" +%s) - $(date -d "$today" +%s)) / 86400 ))
      [ "$days" -lt 0 ] && days="EXPIRE"
    else
      access_until="-"; days="-"
    fi
    state="$(docker inspect -f '{{.State.Status}}' "$(client_compose "$slug" ps -q web 2>/dev/null)" 2>/dev/null || echo arrete)"
    printf '%-20s %-32s %-12s %-10s %s\n' "$slug" "$domain" "$access_until" "$days" "$state"
  done
}

backup_one() {
  local slug="$1"
  local dir="$CLIENTS_ROOT/$slug"
  local file="$dir/backups/${slug}_$(date +%Y%m%d_%H%M%S).sql.gz"
  local db_user db_name
  db_user="$(env_value "$dir/.env" DB_USER)"
  db_name="$(env_value "$dir/.env" DB_NAME)"
  mkdir -p "$dir/backups"
  client_compose "$slug" exec -T db pg_dump -U "$db_user" "$db_name" | gzip > "$file"
  find "$dir/backups" -name "${slug}_*.sql.gz" -mtime "+$BACKUP_RETENTION_DAYS" -delete
  echo "$slug : $(du -h "$file" | cut -f1) -> $file"
}

cmd_backup() {
  [ $# -eq 1 ] || die "usage : backup <client|all>"
  local slug
  if [ "$1" = "all" ]; then
    for slug in $(list_clients); do backup_one "$slug"; done
  else
    backup_one "$1"
  fi
}

task_one() {
  local slug="$1" command="$2"
  echo "[$slug] $command"
  client_compose "$slug" exec -T web python manage.py "$command" || echo "[$slug] echec de $command" >&2
}

cmd_task() {
  [ $# -eq 2 ] || die "usage : task <client|all> <reminders|payments>"
  local command slug
  case "$2" in
    reminders) command=send_contribution_reminders ;;
    payments)  command=check_pending_payments ;;
    *) die "tache inconnue : $2 (reminders ou payments)" ;;
  esac
  if [ "$1" = "all" ]; then
    for slug in $(list_clients); do task_one "$slug" "$command"; done
  else
    task_one "$1" "$command"
  fi
}

cmd_update() {
  docker build -t "$IMAGE" "$ROOT"
  local slug
  for slug in $(list_clients); do
    echo "Mise a jour de $slug ..."
    recreate_web "$slug"
  done
}

case "${1:-}" in
  init)   shift; cmd_init "$@" ;;
  new)    shift; cmd_new "$@" ;;
  extend) shift; cmd_extend "$@" ;;
  status) shift; cmd_status "$@" ;;
  backup) shift; cmd_backup "$@" ;;
  update) shift; cmd_update "$@" ;;
  task)   shift; cmd_task "$@" ;;
  *) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
