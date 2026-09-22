.PHONY: help install bootstrap run check check-migrations test ci docker-build docker-run

PYTHON ?= ./.venv/bin/python
PIP ?= ./.venv/bin/pip
RUN_SQLITE = env -u DB_NAME -u DB_USER -u DB_PASSWORD -u DB_HOST -u DB_PORT
IMAGE ?= kotiza:local

help:
	@echo "Targets disponibles:"
	@echo "  make install            - Installer les dependances"
	@echo "  make bootstrap          - Initialiser DB + roles + superuser"
	@echo "  make run                - Lancer le serveur local"
	@echo "  make check              - Verifications Django"
	@echo "  make check-migrations   - Verifier migrations manquantes"
	@echo "  make test               - Executer les tests"
	@echo "  make ci                 - Pipeline locale (check + migrations + tests)"
	@echo "  make docker-build       - Construire l'image Docker locale"
	@echo "  make docker-run         - Lancer le conteneur local sur :8000"

install:
	$(PIP) install -r requirements.txt

bootstrap:
	$(RUN_SQLITE) $(PYTHON) manage.py bootstrap_project --with-superuser --username admin --email admin@example.com --password Admin1234!

run:
	$(RUN_SQLITE) $(PYTHON) manage.py runserver 127.0.0.1:8000

check:
	$(RUN_SQLITE) $(PYTHON) manage.py check

check-migrations:
	$(RUN_SQLITE) $(PYTHON) manage.py makemigrations --check --dry-run

test:
	$(RUN_SQLITE) $(PYTHON) manage.py test

ci: check check-migrations test

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env $(IMAGE)
