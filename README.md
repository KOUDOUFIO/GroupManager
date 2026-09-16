# GroupManager

Plateforme web pour gerer des groupes, membres, rencontres, cotisations, documents et evenements.

## Base de données

Le projet est un backend Django et fonctionne avec **deux bases de données possibles**, choisies automatiquement (`groupmanager/settings.py::_build_database_config`) :

| Contexte | Moteur | Déclenché quand |
|---|---|---|
| Production / Docker (recommandé) | **PostgreSQL 14** | `DATABASE_URL` (postgres://...) est définie, ou `DB_NAME` + `DB_USER` + `DB_PASSWORD` sont toutes définies |
| Développement local par défaut | **SQLite** (`db.sqlite3`) | Aucune variable Postgres définie |
| Tests (`manage.py test`) | **SQLite** | Toujours, même si les variables Postgres sont définies |

Avec `docker-compose up`, le service `db` lance un conteneur `postgres:14` et le service `web` s'y connecte via `DB_HOST=db`. En local sans Docker, si vous ne renseignez pas `DB_NAME`/`DB_USER`/`DB_PASSWORD` dans `.env`, l'application bascule automatiquement sur SQLite.

Le cache applicatif (throttling API, cache de données) utilise **Redis** (`REDIS_HOST`/`REDIS_PORT`, cf. `CACHES` dans `settings.py`), indépendamment du moteur de base de données.

## Demarrage rapide

1. Creer un environnement virtuel (optionnel).
2. Installer les dependances :

```bash
python3 -m pip install -r requirements.txt
```

3. Configurer les variables d'environnement dans un fichier `.env` a la racine du projet. Le projet charge automatiquement ce fichier et active PostgreSQL si `DB_NAME`, `DB_USER` et `DB_PASSWORD` sont presentes.

```env
DB_NAME=groupmanager_db
DB_USER=groupmanager_user
DB_PASSWORD=ChangeMe_2025!
DB_HOST=localhost
DB_PORT=5432
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

4. Lancer les migrations :

```bash
python3 manage.py migrate
```

4. Creer un superutilisateur :

```bash
python3 manage.py createsuperuser
```

5. Initialiser les roles et permissions :

```bash
python3 manage.py seed_roles
```

6. Configurer Postgres (si besoin) :

```bash
sudo -u postgres psql
```

```sql
CREATE USER groupmanager_user WITH PASSWORD 'GroupManager_2025!';
CREATE DATABASE groupmanager_db OWNER groupmanager_user;
```

7. Demarrer le serveur :

```bash
python3 manage.py runserver
```

## Initialisation professionnelle (1 commande)

```bash
python3 manage.py bootstrap_project --with-superuser --username admin --email admin@example.com --password Admin1234!
```

## Commandes standard (Makefile)

```bash
make install
make bootstrap
make run
make ci
```

- `make ci` execute `check`, `check-migrations` et `test`.
- Le pipeline CI GitHub Actions est disponible dans `.github/workflows/ci.yml`.
- Le pipeline CD Docker (build/push GHCR + deploiement webhook optionnel) est dans `.github/workflows/docker-cd.yml`.

## CD Docker (GitHub Actions)

- Build + push automatique de l'image Docker sur `ghcr.io/<owner>/<repo>`:
  - sur `push` de `main`
  - sur `tag` `v*`
- Deploiement webhook optionnel:
  - automatique sur `tag v*`
  - manuel via `workflow_dispatch` avec `deploy=true`
- Secret optionnel a configurer dans le repo:
  - `DEPLOY_WEBHOOK_URL` (URL de ton systeme de deploiement)

## Docker (recommande)

1. Copier le fichier d'exemple :

```bash
cp .env.example .env
```

2. Modifier `.env` si besoin.

3. Lancer les services :

```bash
docker-compose up --build
```

4. Ouvrir l'application :

- http://127.0.0.1:8000/

## Acces

- Interface principale : http://127.0.0.1:8000/
- Interface Administrateur : http://127.0.0.1:8000/admin-workspace/
- Interface Manager : http://127.0.0.1:8000/manager-workspace/
- Recherche Globale : http://127.0.0.1:8000/recherche/
- Administration : http://127.0.0.1:8000/admin/
- API REST : http://127.0.0.1:8000/api/
- Schema API (JSON) : http://127.0.0.1:8000/api/schema/
- API Dashboard : http://127.0.0.1:8000/api/dashboard-summary/
- API Audit : http://127.0.0.1:8000/api/audit-logs/
- Ecran Audit : http://127.0.0.1:8000/audit-logs/
- Connexion : http://127.0.0.1:8000/accounts/login/
- Healthcheck : http://127.0.0.1:8000/health/

## Structure du projet

```
groupmanager/        Configuration Django (settings, urls, wsgi/asgi)
core/                 Application principale
  models/             Modeles de donnees, un fichier par domaine
    group.py            Group
    organ.py             Organ
    member.py            Member
    position.py          Position
    meeting.py            Meeting, MeetingEntry
    contribution.py       Contribution
    document.py           Document
    event.py              Event
    audit_log.py          AuditLog
    notification.py       Notification, NotificationPreference
    dashboard.py          DashboardPreference
    two_factor.py         TOTPDevice, TwoFactorPreference
  web_views/          Vues web (Django classic), un fichier par domaine
    marketing.py          Pages vitrine (accueil, entreprise, plateforme, devis)
    workspaces.py          Workspaces admin/gestionnaire, recherche, dashboard groupe
    mixins.py               Briques communes aux vues CRUD (permissions, recherche)
    group.py / organ.py / member.py / position.py / meeting.py /
    contribution.py / document.py / event.py / audit.py   CRUD par domaine
    exports.py              Exports CSV / Excel / PDF
  views.py            Vues API REST (DRF ViewSets)
  serializers.py       Serializers DRF
  services/           Logique metier (un service par domaine)
  forms.py            Formulaires Django avec validations croisees
  admin.py             Configuration Django Admin
  signals.py           Journal d'audit automatique (post_save/post_delete)
  middleware.py         Contexte de l'acteur pour l'audit
  migrations/           Migrations de base de donnees
  templates/, static/   Gabarits HTML et assets
```

## Notes

- Les fichiers telecharges sont stockes dans le dossier `media/`.
- Variables d'environnement possibles : `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_LOG_LEVEL`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_SECURE_HSTS_PRELOAD`, `DRF_PAGE_SIZE`, `DRF_THROTTLE_ANON`, `DRF_THROTTLE_USER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
- Exports disponibles (cotisations/presences) en CSV, Excel et PDF.
- Les exports `cotisations` et `presences` acceptent des filtres URL: `group`, `start_date` et `end_date`.
- Un module d'audit trace automatiquement les creations, modifications et suppressions sur les entites principales.
- Un dashboard `Groupe 360` est disponible via la liste des groupes (action `Dashboard`).
- Les menus de navigation s'adaptent au profil connecte (`Administrateur`, `Gestionnaire`, `Utilisateur`).
- Les erreurs HTTP 400/403/404/500 ont des pages dediees.
- Les logs applicatifs sont ecrits dans `logs/groupmanager.log`.
