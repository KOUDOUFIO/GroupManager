# Héberger plusieurs clients sur un serveur

Chaque organisation cliente a **sa propre installation** Kotiza : sa base de données, son cache, ses fichiers et son domaine. Aucune donnée n'est partagée entre clients. Un seul nginx route chaque domaine vers la bonne installation et gère le HTTPS.

Tout se pilote avec un seul script : `docker/multi/kotiza-clients.sh`.

> Pour un seul site (sans gestion de clients), suivez plutôt `DEPLOYMENT.md`.

## 1. Préparer le serveur (une seule fois)

Prérequis : un VPS avec Docker (2 Go de RAM pour 4 à 6 petits clients), et ce dépôt cloné dessus.

```bash
./docker/multi/kotiza-clients.sh init
```

Puis complétez `clients/shared.env` (réglages communs à tous les clients) :

- `KOTIZA_OPERATOR_EMAIL` : **votre** email (compte `kotiza-support` et alertes Let's Encrypt).
- `KOTIZA_BILLING_CONTACT` : ce que voit un client dont l'abonnement expire, par ex. `Mobile Money +228 90 00 00 00 - contact@kotiza.com`.
- `EMAIL_*` : l'envoi des emails (mot de passe oublié, rappels).

Le dossier `clients/` contient les secrets et les données : il est ignoré par Git. **Sauvegardez-le hors du serveur.**

## 2. Ajouter un client

1. **DNS** : faites pointer le domaine du client (ex. `amicale.kotiza.com`) vers l'IP du serveur (enregistrement `A`). Attendez qu'il réponde avant l'étape suivante.
2. Créez l'installation, ici avec 30 jours d'essai :

   ```bash
   ./docker/multi/kotiza-clients.sh new amicale amicale.kotiza.com bureau@amicale.org 30
   ```

Le script affiche **deux comptes, une seule fois** :

| Compte | Pour qui | Accès après expiration |
|---|---|---|
| `admin` | le client (rôle Administrateur) | **bloqué** |
| `kotiza-support` | vous (superutilisateur) | toujours actif |

Transmettez `admin` au client et demandez-lui de changer son mot de passe. Gardez `kotiza-support` pour vous (support, export des données).

## 3. Encaisser un abonnement (paiement manuel)

1. Le client vous paie par Mobile Money ou virement.
2. Vous prolongez son accès :

   ```bash
   ./docker/multi/kotiza-clients.sh extend amicale 2027-01-31
   ```

3. Vous lui envoyez sa facture.

**Ce qui se passe à l'échéance :**
- 14 jours avant, l'administrateur du client voit un bandeau de rappel avec votre contact.
- Le lendemain de la date de fin, le site affiche « Abonnement expiré » à tout le monde, sauf à `kotiza-support`. Les données ne sont pas supprimées.
- Après un `extend`, l'accès revient en quelques secondes.

## 4. Suivi au quotidien

```bash
./docker/multi/kotiza-clients.sh status          # clients, fin d'abonnement, jours restants
./docker/multi/kotiza-clients.sh backup all      # sauvegarde de toutes les bases
./docker/multi/kotiza-clients.sh update          # après un `git pull` : nouvelle version pour tous
```

Sauvegarde automatique chaque nuit à 3h (`crontab -e`) :

```
0 3 * * * cd /chemin/vers/kotiza && ./docker/multi/kotiza-clients.sh backup all >> logs/backup.log 2>&1
```

Les sauvegardes vont dans `clients/<client>/backups/` et sont conservées 14 jours. Copiez-les régulièrement hors du serveur.

## Tester sans vrai certificat

Pour un essai, `CERTBOT_STAGING=1 ./docker/multi/kotiza-clients.sh new ...` demande un certificat de test à Let's Encrypt. Il n'est pas reconnu par les navigateurs, mais il ne consomme pas les quotas.
