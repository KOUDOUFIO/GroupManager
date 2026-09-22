#!/usr/bin/env bash
# Obtient le premier certificat HTTPS Let's Encrypt pour ce projet.
#
# A executer UNE SEULE FOIS sur le serveur, apres avoir :
#   1. Remplace VOTRE-DOMAINE.com par votre vrai domaine dans docker/nginx/app.conf
#   2. Pointe le DNS de ce domaine vers l'IP publique du serveur
#   3. Rempli .env (voir .env.example)
#
# Usage : ./docker/nginx/init-letsencrypt.sh votredomaine.com votre@email.com
set -e

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <domaine> <email>"
  echo "Exemple: $0 kotiza.example.com admin@example.com"
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"
COMPOSE="docker compose"
DATA_PATH="./certbot"

if [ -d "$DATA_PATH/conf/live/$DOMAIN" ]; then
  echo "Un certificat existe deja pour $DOMAIN. Rien a faire (utilisez certbot renew pour le renouveler)."
  exit 0
fi

echo "### Creation d'un certificat factice pour permettre a nginx de demarrer ..."
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
$COMPOSE run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '/etc/letsencrypt/live/$DOMAIN/privkey.pem' \
    -out '/etc/letsencrypt/live/$DOMAIN/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### Demarrage de nginx ..."
$COMPOSE up --force-recreate -d nginx

echo "### Suppression du certificat factice ..."
$COMPOSE run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$DOMAIN && \
  rm -Rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -Rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "### Demande du vrai certificat Let's Encrypt pour $DOMAIN ..."
$COMPOSE run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    --email $EMAIL -d $DOMAIN \
    --rsa-key-size 2048 --agree-tos --no-eff-email --force-renewal" certbot

echo "### Rechargement de nginx avec le vrai certificat ..."
$COMPOSE exec nginx nginx -s reload

echo "Termine. https://$DOMAIN devrait maintenant fonctionner."
