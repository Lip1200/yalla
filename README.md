# Yalla - Backend API

Yalla est un réseau social de santé bienveillant conçu pour accompagner les personnes souffrant d'obésité ou de diabète. L'application intègre des fonctionnalités de suivi, de gamification via des défis, des interactions sociales, et inclut une réservation de restaurants en groupe (via intégration TheFork).

## Architecture

Ce projet backend est conçu sous forme de **Monolithe Modulaire (Modular Monolith)** en utilisant **FastAPI**.
L'objectif est d'avoir une arborescence évolutive permettant à plusieurs développeurs d'avancer en parallèle sans provoquer de conflits Git complexes.

La structure des dossiers est la suivante :

- **`src/core/`** : Contient tout le socle technique transversal de l'application : configuration générale, connexion à la base de données, sécurisation (tokens JWT), et gestionnaire d'exceptions globales.
- **`src/modules/`** : Isoler les logiques métiers par domaine (Feature-Based).
  Chaque module (par ex. `restaurants`, `users`) contient :
  - `router.py` : Déclaration des routes (`APIRouter`) de FastAPI pour ce module.
  - `schemas.py` : Définition des structures de données et de la validation avec **Pydantic**.
  - `service.py` : Logique métier (Business Logic) et interactions avec des API externes ou de calculs complexes.
  - `models.py` : Modèles ORM (généralement SQLAlchemy) pour l'interaction avec la base de données.

**Pourquoi cette structure ?**
1. **Validation stricte** : Chaque développeur définit précisément la forme de ses données (ex: `Restaurant` ou `User`) dans son propre `schemas.py`. Pydantic et FastAPI valideront automatiquement les requêtes entrantes.
2. **Indépendance des routes** : Au lieu d'avoir un fichier `main.py` de 2000 lignes, chaque routeur est indépendant. FastAPI consolide tous ces APIRouter dans le fichier principal `src/main.py`.
3. **Réduction des Merge Conflicts** : La séparation verticale par feature minimise les risques que deux développeurs touchent le même fichier.

## Workflow Git

Pour maintenir le projet propre, nous appliquons une convention de branches rattachée aux modules métier :

- La branche principale de développement est **`develop`**. (Ne jamais coder directement sur `main` ou `develop`).
- Pour toute nouvelle tâche, créez une branche de fonctionnalité (feature) basée sur `develop`, avec un préfixe indiquant la nature de la modification et le module impacté :
  - `feature/restaurants-thefork` (Nouvelle fonctionnalité module restaurant)
  - `feature/users-profile-update` (Nouvelle fonctionnalité module users)
  - `fix/challenges-score` (Correction de bug module challenges)

**Exemple :**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/restaurants-thefork
# ... travaillez dans src/modules/restaurants/ ...
```

## Lancement rapide

### 1. Installation des dépendances avec uv

Nous utilisons **uv**, un gestionnaire de paquets ultra-rapide en Rust pour Python.
Si ce n'est pas déjà fait, [installez uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# uv va automatiquement créer l'environnement virtuel (.venv) et installer les dépendances
uv sync
```

### 2. Lancer le serveur en local

Avec uv, vous pouvez lancer le serveur directement :

```bash
uv run uvicorn src.main:app --reload
```

Le flag `--reload` permet de redémarrer le serveur automatiquement lorsque vous modifiez un fichier.

### 3. Documentation de l'API

Une fois le serveur lancé, accédez à la documentation générée automatiquement par FastAPI (Swagger UI) à cette adresse :
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**
