# Guide de déploiement (VPS + Docker)

Ce guide suppose un déploiement sur un VPS (OVH, Hetzner, DigitalOcean...) avec Docker. Tout ce qui peut être automatisé l'est déjà dans ce dépôt (`docker-compose.yml`, nginx, certbot, sauvegardes). Les étapes marquées **[VOUS]** sont des actions que vous seul pouvez faire (paiement, compte externe, DNS).

## 1. Prérequis — actions de votre côté

- [ ] **[VOUS]** Louer un VPS (2 Go de RAM minimum) avec Docker installé (ou installable via `apt`).
- [ ] **[VOUS]** Acheter un nom de domaine (Gandi, OVH, Namecheap...).
- [ ] **[VOUS]** Pointer le DNS du domaine (enregistrement `A`) vers l'IP publique du VPS.
- [ ] **[VOUS]** (Optionnel mais recommandé) Créer un compte chez un fournisseur SMTP transactionnel (ex: Brevo, Mailgun, ou un simple compte Gmail avec mot de passe d'application) pour l'envoi d'emails (mot de passe oublié, notifications).

## 2. Préparer le serveur

```bash
# Sur le VPS
sudo apt update && sudo apt install -y docker.io docker-compose git
git clone <url-de-votre-depot> kotiza
cd kotiza
```

## 3. Configurer l'environnement

```bash
cp .env.example .env
```

Éditez `.env` et renseignez au minimum :

- `DJANGO_SECRET_KEY` — générez une vraie valeur :
  ```bash
  python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DJANGO_ALLOWED_HOSTS=votredomaine.com`
- `CSRF_TRUSTED_ORIGINS=https://votredomaine.com`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` — identifiants Postgres forts (jamais ceux de `.env.example`)
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` — si vous voulez que les emails partent réellement (sinon ils restent seulement dans les logs)

## 4. Configurer nginx pour votre domaine

Dans `docker/nginx/app.conf`, remplacez les 2 occurrences de `VOTRE-DOMAINE.com` par votre vrai domaine.

## 5. Démarrer les services de base (sans nginx pour l'instant)

```bash
docker-compose up -d db redis web
docker-compose logs -f web   # verifier que les migrations passent et que gunicorn demarre
```

## 6. Obtenir le certificat HTTPS (une seule fois)

```bash
./docker/nginx/init-letsencrypt.sh votredomaine.com votre@email.com
```

Ce script crée un certificat temporaire pour permettre à nginx de démarrer, démarre nginx, puis demande le vrai certificat à Let's Encrypt et recharge nginx. Le renouvellement automatique est ensuite géré par le service `certbot` du `docker-compose.yml` (vérifie toutes les 12h).

## 7. Vérifier

- `https://votredomaine.com/health/` doit répondre `{"status": "ok", ...}`
- `https://votredomaine.com/` doit afficher la page d'accueil

## 8. Créer le superutilisateur de production

```bash
docker-compose exec web python manage.py bootstrap_project --with-superuser \
  --username admin --email vous@votredomaine.com --password 'UnMotDePasseFortEtUnique!'
```

Changez ce mot de passe dès la première connexion si vous l'avez tapé en clair dans le terminal.

## 9. Sauvegardes automatiques

Ajoutez au crontab du serveur (`crontab -e`) :

```
0 3 * * * cd /chemin/vers/kotiza && ./docker/backup.sh >> logs/backup.log 2>&1
```

Cela sauvegarde la base chaque nuit à 3h dans `./backups/`, avec suppression automatique des sauvegardes de plus de 14 jours. **Pensez aussi à copier régulièrement `./backups/` hors du serveur** (S3, un autre serveur...) — une sauvegarde qui reste sur la même machine que l'original ne protège pas contre une panne disque.

Pour restaurer un dump :

```bash
gunzip -c backups/votre_dump.sql.gz | docker-compose exec -T db psql -U <DB_USER> <DB_NAME>
```

## 10. Rappels automatiques de cotisation

`send_contribution_reminders` relance par email (et notification in-app si le
membre a un compte lié) les membres sans cotisation mensuelle enregistrée pour
le mois en cours, groupe par groupe — seuls les groupes ayant déjà utilisé des
cotisations mensuelles sont concernés. Testez d'abord avec `--dry-run` :

```bash
docker-compose exec web python manage.py send_contribution_reminders --dry-run
```

Puis ajoutez au crontab du serveur (`crontab -e`) — une exécution mensuelle,
pas quotidienne, pour ne pas spammer les membres déjà relancés :

```
0 8 5 * * cd /chemin/vers/kotiza && docker-compose exec -T web python manage.py send_contribution_reminders >> logs/reminders.log 2>&1
```

Nécessite `EMAIL_HOST` configuré (section 3) pour un envoi réel — sans lui,
les emails partent dans les logs console du conteneur `web`, rien n'est
envoyé.

## 11. Renouvellement / mises à jour de l'application

```bash
git pull
docker-compose up -d --build web
docker-compose exec web python manage.py migrate
```

## Ce qui reste entièrement à votre charge

- Le contenu réel des pages `/mentions-legales/` et `/confidentialite/` (informations d'entreprise, politique de conservation des données) — voir la note dans ces templates.
- La supervision de la place disque du VPS (sauvegardes, logs, médias qui s'accumulent).
- Les mises à jour de sécurité du système d'exploitation du VPS (`apt upgrade`), Docker n'en fait pas partie.
