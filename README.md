# Life EPM

Application de gestion pour l'Église Pentecôte Missionnaire. La pile comprend Next.js/React, Tailwind CSS, FastAPI, PostgreSQL et Alembic. L'adaptateur Africa's Talking pour les SMS est intégré mais reste désactivé tant que ses paramètres privés ne sont pas configurés.

## Démarrage local

Prérequis : Python 3.12+, Node.js, npm et un service PostgreSQL local.

1. Copier `.env.example` vers `.env` (`Copy-Item .env.example .env` dans PowerShell) si `.env` n'existe pas.
2. Garder PostgreSQL configuré avec la base et l'utilisateur existants `life_epm`; définir un secret JWT aléatoire d'au moins 32 caractères et un mot de passe provisoire unique d'au moins 12 caractères. Si les identifiants PostgreSQL locaux diffèrent de ceux de `.env`, renseigner `DATABASE_URL` dans `.env` au format `postgresql+psycopg://life_epm:mot-de-passe@localhost:5432/life_epm`.
3. Depuis la racine du projet, lancer le script qui applique les migrations et ouvre l'API et l'interface dans deux fenêtres PowerShell :

```powershell
.\scripts\start.ps1
```

Ouvrir [http://localhost:3000](http://localhost:3000). L'API est disponible sur [http://localhost:8000](http://localhost:8000), et sa documentation de développement sur `/docs`.

Le compte initial est nommé **Pasteur BOBOU Josué E.** ; son nom complet, son identifiant et son mot de passe provisoire sont lus depuis `.env` (`LIFE_EPM_ADMIN_FULL_NAME`, `LIFE_EPM_ADMIN_USERNAME`, `LIFE_EPM_ADMIN_PASSWORD`). Le changement du mot de passe provisoire est obligatoire à la première connexion. Tant que ce changement est requis, la valeur de `.env` est réappliquée au démarrage; un mot de passe déjà changé n'est jamais écrasé.

Pour arrêter l'application, fermer les deux fenêtres PowerShell. PostgreSQL conserve ses propres données.

## Développement

Terminal backend, depuis `backend` :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DATABASE_URL = "postgresql+psycopg://life_epm:YOUR_URL_ENCODED_PASSWORD@localhost:5432/life_epm"
$env:JWT_SECRET = "un-secret-aleatoire-d-au-moins-32-caracteres"
$env:BOOTSTRAP_ADMIN_PASSWORD = "un-mot-de-passe-provisoire-de-12-caracteres"
alembic upgrade head
uvicorn app.main:app --reload
```

Dans un autre terminal, à la racine :

```powershell
npm ci
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

## Vérification

```powershell
npm run build
npm run typecheck
```

Depuis `backend`, avec l'environnement virtuel activé :

```powershell
$env:PYTHONPATH = "."
pytest
```

## Accès direct à toutes les pages

Toutes les rubriques s'ouvrent dans l'application après connexion. Les liens ci-dessous ouvrent directement la rubrique demandée; ils ne contournent pas les permissions du compte. Si l'application est sur un autre ordinateur, remplacez `localhost:3000` par son adresse ou son nom de domaine.

| Page | Accès direct | Où modifier l'écran |
|---|---|---|
| Connexion et changement de mot de passe | [Ouvrir la connexion](http://localhost:3000/) | Écrans `LoginScreen` et `PasswordScreen` dans [app/page.tsx](./app/page.tsx); routes `/auth/login` et `/auth/change-password` dans [routes.py](./backend/app/routes.py). |
| Tableau de bord | [Ouvrir le tableau de bord](http://localhost:3000/?page=dashboard) | [Dashboard dans `app/page.tsx`](./app/page.tsx) (`Dashboard`); données dans `/dashboard` de [routes.py](./backend/app/routes.py). |
| Fidèles | [Ouvrir les fidèles](http://localhost:3000/?page=fideles) | `ModulePage` et `RecordModal` dans [app/page.tsx](./app/page.tsx); routes `/members` dans [routes.py](./backend/app/routes.py); champs dans [schemas.py](./backend/app/schemas.py); table `Member` dans [models.py](./backend/app/models.py). |
| Cultes | [Ouvrir les cultes](http://localhost:3000/?page=cultes&group=culte) | Onglet et formulaire dans [app/page.tsx](./app/page.tsx); routes `/services` et `/services/{service_id}/attendance/{member_id}` dans [routes.py](./backend/app/routes.py). |
| Programmes | [Ouvrir les programmes](http://localhost:3000/?page=cultes&group=programme) | Même écran que les cultes, choix du groupe et liste de types dans [app/page.tsx](./app/page.tsx); données `ChurchService` dans [models.py](./backend/app/models.py). |
| Finances — opérations | [Ouvrir les opérations](http://localhost:3000/?page=finances&tab=operations) | Onglets et champs financiers dans [app/page.tsx](./app/page.tsx); `/finances` dans [routes.py](./backend/app/routes.py); règles de validation dans [schemas.py](./backend/app/schemas.py). |
| Finances — budgets | [Ouvrir les budgets](http://localhost:3000/?page=finances&tab=budgets) | Formulaire budgétaire dans [app/page.tsx](./app/page.tsx); `/budgets` dans [routes.py](./backend/app/routes.py); modèle `BudgetLine` dans [models.py](./backend/app/models.py). |
| Prières | [Ouvrir les prières](http://localhost:3000/?page=prieres) | Filtres et affichage dans `StoryBoard` de [app/page.tsx](./app/page.tsx); routes `/prayers` dans [routes.py](./backend/app/routes.py). |
| Témoignages | [Ouvrir les témoignages](http://localhost:3000/?page=prieres) | Les témoignages partagent cette page avec les prières; affichage `StoryBoard` dans [app/page.tsx](./app/page.tsx); routes `/testimonies` dans [routes.py](./backend/app/routes.py). |
| Mariages et fiançailles | [Ouvrir les mariages](http://localhost:3000/?page=familles&tab=marriages) | Onglet et formulaire `familles` dans [app/page.tsx](./app/page.tsx); routes `/families/marriages` dans [routes.py](./backend/app/routes.py). |
| Naissances | [Ouvrir les naissances](http://localhost:3000/?page=familles&tab=births) | Onglet et champs de naissance dans [app/page.tsx](./app/page.tsx); routes `/families/births` dans [routes.py](./backend/app/routes.py). |
| Paramètres — identité et logo de l'église | [Ouvrir l'identité](http://localhost:3000/?page=parametres&tab=identity) | `SettingsWorkspace` et `ChurchIdentityForm` dans [app/page.tsx](./app/page.tsx); routes `/church` et `/church/logo` dans [routes.py](./backend/app/routes.py); colonnes du modèle `Church` dans [models.py](./backend/app/models.py). |
| Paramètres — zones et cellules | [Ouvrir les zones](http://localhost:3000/?page=parametres&tab=zones) | Onglet dans [app/page.tsx](./app/page.tsx); routes `/zones`, `/sectors` dans [routes.py](./backend/app/routes.py). |
| Paramètres — utilisateurs et rôles | [Ouvrir les utilisateurs dans Paramètres](http://localhost:3000/?page=parametres&tab=users) | Onglet de paramètres dans [app/page.tsx](./app/page.tsx). L'administration détaillée est aussi dans [Utilisateurs & rôles](http://localhost:3000/?page=utilisateurs). |
| Paramètres — certificats | [Ouvrir les certificats](http://localhost:3000/?page=parametres&tab=certificates) | `CertificateWorkspace` dans [app/page.tsx](./app/page.tsx) : attestations de membre et certificats de baptême imprimables. |
| Utilisateurs et rôles | [Ouvrir les utilisateurs](http://localhost:3000/?page=utilisateurs) | Page et formulaire utilisateur dans [app/page.tsx](./app/page.tsx); routes `/users` dans [routes.py](./backend/app/routes.py); permissions dans [security.py](./backend/app/security.py). |
| Messagerie | [Ouvrir la messagerie](http://localhost:3000/?page=sms) | Conversations privées et de groupe dans [app/page.tsx](./app/page.tsx); routes protégées dans [routes.py](./backend/app/routes.py); modèles et migration dans [models.py](./backend/app/models.py) et [versions/](./backend/alembic/versions/). L'onglet SMS aux fidèles n'affiche que les personnes ayant consenti; l'envoi exige une configuration Africa's Talking. |

### Où modifier chaque partie

Les commentaires du code servent de repères supplémentaires. Pour modifier une fonctionnalité, suivez généralement le parcours interface → API → validation → modèle de données :

| Partie à modifier | Fichier et rôle |
|---|---|
| Menu, libellés, identifiants des pages | [app/page.tsx](./app/page.tsx) — `navigationGroups`, `labels`. |
| Liens directs `?page=...` et sélection d'onglets | [app/page.tsx](./app/page.tsx) — `readPageLocation`, `writePageLocation`, état et fonctions de navigation de `Home`. |
| Chargement des listes et synthèses | [app/page.tsx](./app/page.tsx) — `loadSection`. Si la page est vide, vérifier aussi la route API correspondante; le composant `MessengerWorkspace` charge ses conversations directement. |
| Présentation d'une rubrique | [app/page.tsx](./app/page.tsx) — `Dashboard` ou `ModulePage`; les filtres et formulaires ont leurs composants dédiés dans le même fichier. |
| Champs des formulaires de création | [app/page.tsx](./app/page.tsx) — définitions `fields` dans `RecordModal`. |
| Données envoyées à l'API | [app/page.tsx](./app/page.tsx) — `saveRecord` et `api`. |
| Couleurs, tailles, affichage mobile | [app/globals.css](./app/globals.css) — variables `:root`, styles des composants, puis règles `@media`. |
| Champs acceptés, formats et validations | [backend/app/schemas.py](./backend/app/schemas.py) — modèles Pydantic `...Create` et `...Output`. |
| URL d'API, réponses, règles d'accès | [backend/app/routes.py](./backend/app/routes.py) — routes FastAPI; chaque route indique aussi les rôles autorisés. La messagerie vérifie l'appartenance à chaque conversation. |
| Tables et relations de la base | [backend/app/models.py](./backend/app/models.py) — modèles SQLAlchemy. |
| Connexion, cookies et mots de passe | [backend/app/security.py](./backend/app/security.py). |
| Paramètres chargés depuis `.env` | [backend/app/config.py](./backend/app/config.py) et [`.env.example`](./.env.example). Ne partagez jamais le vrai fichier `.env`. |
| Création initiale de l'église, compte admin et données de démo | [backend/app/main.py](./backend/app/main.py). |
| Connexion à PostgreSQL et sessions de requête | [backend/app/db.py](./backend/app/db.py). |
| Structure HTML et titre du navigateur | [app/layout.tsx](./app/layout.tsx). |
| Proxy web vers l'API | [next.config.ts](./next.config.ts). |
| Démarrage local et sauvegardes PostgreSQL | [scripts/](./scripts/) et [backend/alembic.ini](./backend/alembic.ini). |
| Modifications de structure de base | Ajouter une nouvelle migration dans [backend/alembic/versions/](./backend/alembic/versions/); ne pas modifier une ancienne migration déjà appliquée. |
| Tests de l'API | [backend/tests/test_api.py](./backend/tests/test_api.py); ajouter un test quand une route ou une permission change. |
| Documentation générale et étapes d'installation | [README.md](./README.md). |

Les liens de pages modifient l'URL dans l'application et sont conservés après connexion. Les fonctionnalités restent soumises au rôle du compte : une page peut être inaccessible si ce rôle ne l'autorise pas. Les rubriques de suivi pastoral et de patrimoine ont été retirées; leurs anciennes lignes restent conservées dans les tables `pastoral_followups` et `assets`, sans écran ni route API.

Les fenêtres de création, de pointage et de choix sont des formulaires modaux, pas des pages avec une URL indépendante; elles se trouvent dans [app/page.tsx](./app/page.tsx) (`RecordModal`, `AttendanceModal`, `FamilyTypeDialog`).

### Diagnostic rapide des erreurs

Pour diagnostiquer une erreur, consulter les messages affichés dans les fenêtres de l'API et de l'interface :

```powershell
Invoke-WebRequest http://localhost:8000/api/health
```

Une erreur d'affichage se diagnostique généralement dans [app/page.tsx](./app/page.tsx) ou [app/globals.css](./app/globals.css); une réponse HTTP invalide dans [backend/app/routes.py](./backend/app/routes.py) ou [backend/app/schemas.py](./backend/app/schemas.py). Les erreurs PostgreSQL apparaissent dans la fenêtre de l'API. Ne copiez pas de secrets du fichier `.env` dans un rapport partagé.

## Modules actuellement raccordés à l'API

- Session sécurisée par cookie HTTP-only, changement obligatoire du mot de passe provisoire et rôles administrateur, secrétariat, trésorerie et berger.
- Fiches des fidèles avec génération séquentielle du numéro EPM, recherche, zones, secteurs et cellules.
- Tableaux de bord des fidèles (présences, absences explicitement pointées et baptêmes) et des cultes (pointages et taux calculé à partir des présences/absences renseignées).
- Espace « Cultes & programmes » séparé en deux listes; les programmes incluent notamment l'évangélisation, la jeunesse, les familles missionnaires, les conférences, les séminaires et les retraites.
- Planification des cultes et programmes avec pointage de présence ou d'absence; un membre non pointé n'est pas compté automatiquement absent.
- Paramètres organisés comme dans le prototype en quatre rubriques : identité de l'église, zones & cellules, utilisateurs & rôles et certificats.
- Certificats d'appartenance et de baptême d'eau imprimables ou exportables en PDF depuis le navigateur; l'émission n'est pas archivée dans la base.
- Export CSV des listes actuellement chargées, avec les permissions d'accès et les données filtrées par l'API.
- Espace financier unique réunissant opérations et budgets, avec synthèse annuelle XOF, opérations immuables et contrôle d'accès séparant la trésorerie du secrétariat.
- Sujets de prière, témoignages et tableaux de bord dédiés aux mariages et aux naissances, avec des formulaires distincts.
- Identité de l'église et logo PNG/JPEG/WebP (2 Mo maximum) modifiables par le super administrateur; le fichier est conservé dans la base et affiché dans le menu. Mise à jour des noms de démonstration hérités vers « Église Pentecôte Missionnaire » et les initiales EPM lors de la migration.
- Page commune « Prières & témoignages » avec filtres, formulaires adaptés à chaque type, confidentialité des prières et conversion d'un sujet exaucé en témoignage.
- Données de démonstration fictives facultatives (`LIFE_EPM_DEMO_DATA_ENABLED=true`), ajoutées uniquement lorsque l'église n'a encore aucun fidèle; les fiches portent un indicateur explicite.
- Sélection de versets de la Louis Segond 1910 (domaine public), affichée dans le menu et renouvelée à chaque connexion réussie sans répéter immédiatement le précédent. Pour ajouter ou modifier les versets, éditer `bibleVerses` dans [app/page.tsx](./app/page.tsx). Il s'agit d'une sélection destinée à cette carte, pas encore d'une Bible complète consultable.
- SMS : intégration Africa's Talking via Celery, lots limités à 500 numéros, consentement explicite et vérification des statuts retournés par le fournisseur. Les SMS restent désactivés par défaut.

### Activer Africa's Talking en environnement de test

Les variables SMS sont lues par l'API et le worker depuis `.env`. Pour tester sans envoyer de vrais SMS, renseigner un compte sandbox, garder `LIFE_EPM_SMS_SANDBOX=true` et utiliser les identifiants fournis par Africa's Talking :

```text
LIFE_EPM_SMS_PROVIDER=africas_talking
LIFE_EPM_SMS_USERNAME=...
LIFE_EPM_SMS_API_KEY=...
LIFE_EPM_SMS_SENDER=
LIFE_EPM_SMS_SANDBOX=true
```

Redémarrer l'API et le worker après la configuration. Les clés restent privées : ne les placez jamais dans le navigateur, le dépôt ou un rapport. En production, utiliser les secrets gérés (par exemple AWS Secrets Manager) et ne passer à `LIFE_EPM_SMS_SANDBOX=false` qu'après validation du compte, du sender ID et des tarifs auprès du fournisseur. Les statuts d'acceptation de l'API fournisseur ne garantissent pas la livraison au téléphone.

### Sauvegardes

- En local : `.\scripts\backup-database.ps1` crée un dump PostgreSQL au format custom dans `backups\`. Protéger ces fichiers comme des données personnelles et en conserver une copie hors de l'ordinateur.
- AWS : [deploy/aws/README.md](./deploy/aws/README.md) décrit le plan quotidien de 35 jours et les prérequis. Le modèle CloudFormation est limité au service AWS Backup; il ne déploie pas l'application.
- Tester périodiquement la restauration dans une base temporaire séparée. Une sauvegarde qui n'a jamais été restaurée n'est pas vérifiée.

## Avant la mise en production

Le dépôt prépare la configuration SMS et une politique AWS Backup, mais aucun déploiement AWS, compte, région, domaine ou certificat n'est établi depuis cet environnement. Pour une URL publique permanente, créer et examiner l'infrastructure cible, configurer `LIFE_EPM_FRONTEND_ORIGIN`, `NEXT_PUBLIC_API_URL` et `LIFE_EPM_COOKIE_SECURE=true`, injecter les secrets privés et placer les services derrière HTTPS. Il reste à réaliser le déploiement AWS, valider une restauration réelle et tester les SMS avec un compte approuvé. Faire auditer la sécurité et les autorisations, et valider les parcours métier avec les responsables de l'église avant l'utilisation réelle des données.
