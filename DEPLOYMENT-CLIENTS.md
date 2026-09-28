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

## 5. Paiement Mobile Money et rappels automatiques

**Paiement T-Money / Flooz (PayGate Global).** Créez un compte marchand sur [paygateglobal.com](https://paygateglobal.com), puis :

1. Mettez la clé API dans `PAYGATE_AUTH_TOKEN` (dans `clients/shared.env` pour tous les clients, ou dans `clients/<client>/.env`).
2. Dans l'espace marchand PayGate, déclarez l'URL de notification : `https://<domaine-du-client>/webhooks/paygate/`.
3. Renseignez `KOTIZA_SITE_URL=https://<domaine-du-client>` : le lien de paiement est ajouté aux rappels.

Le membre voit alors un bouton « Payer ma cotisation » dans « Mon espace ». Il reçoit la demande sur son téléphone, la valide avec son code secret, et la cotisation passe en « Confirmée » toute seule. Kotiza ne fait jamais confiance au message reçu : il revérifie chaque paiement auprès de PayGate, y compris le montant.

**SMS (eSMS Africa).** Renseignez `ESMS_API_KEY` (clé `esms_live_…`, menu Developers > API Keys sur esmsafrica.io) et rechargez le solde du compte (environ 30 FCFA par SMS vers le Togo). Faites approuver un nom d'expéditeur (ex. `KOTIZA`) et mettez-le dans `ESMS_SENDER_ID`, sinon les SMS partent au nom « eSMS ». eSMS Africa est prioritaire sur Twilio pour les SMS.

**Rappels WhatsApp (et SMS de repli) via Twilio.** Renseignez `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM` et/ou `TWILIO_WHATSAPP_FROM`. WhatsApp exige un modèle de message validé par Meta (`TWILIO_WHATSAPP_TEMPLATE_SID`). Sans modèle, WhatsApp refuse l'envoi et le SMS prend le relais. Sans aucune configuration, les rappels partent seulement par email et dans l'application.

Tâches automatiques (`crontab -e`) :

```
# Rappels de cotisation le 5 et le 15 de chaque mois à 9h
0 9 5,15 * * cd /chemin/vers/kotiza && ./docker/multi/kotiza-clients.sh task all reminders >> logs/tasks.log 2>&1
# Vérification des paiements Mobile Money restés en attente, toutes les 15 minutes
*/15 * * * * cd /chemin/vers/kotiza && ./docker/multi/kotiza-clients.sh task all payments >> logs/tasks.log 2>&1
```

## Tester sans vrai certificat

Pour un essai, `CERTBOT_STAGING=1 ./docker/multi/kotiza-clients.sh new ...` demande un certificat de test à Let's Encrypt. Il n'est pas reconnu par les navigateurs, mais il ne consomme pas les quotas.
