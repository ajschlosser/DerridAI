<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI est une application Docker axée sur l’exécution locale pour créer, auditer et interroger des corpus savants de textes philosophiques. Elle ingère des sources PDF, texte/RTF/DOCX, image, audio, URL et Project Gutenberg afin de produire des notices savantes qui préservent la provenance; prend en charge la révision humaine ou par LLM et l’enrichissement de métadonnées lié à des preuves; construit des projections de recherche ChromaDB dérivées; et exécute sur le résultat une chaîne de génération augmentée par récupération (RAG) fondée sur les preuves.

Version actuelle : **0.80.0 — Beverly** ([notes de version](docs/notes/0.80.0.md)).

## Fonctionnalités

- **Corpus Builder** — un flux séquencé Source → Structure/transcription → LLM et enrichissement → Construction des notices → Révision, dont les contrôles s’adaptent au média sélectionné. L’extraction est bornée et préserve la provenance; les révisions de structure ou de texte et les preuves sous la responsabilité du réviseur demeurent auditables.
- **Révision des notices** — espaces de travail JSONL avec historique d’audit, modification de métadonnées en lot ou à l’échelle d’une œuvre, différences, navigation vers la source ou les preuves, et propriété des champs par un humain ou un LLM. Les notices canoniques `FieldAssertion` préservent la provenance de la valeur, l’autorité, les preuves et l’identité stable du champ, tandis que les métadonnées définies par le schéma circulent dans la révision, Search, Record Inspector, les retouches et la présentation Research.
- **Révision et outils LLM** — exécutions au premier plan, en arrière-plan et Auto-improve en arrière-plan à partir de profils de fournisseurs Ollama ou compatibles OpenAI nommés, chacun avec sa propre limite de concurrence et son propre état de préchauffage.
- **Magasins vectoriels** — collections ChromaDB persistantes sur le système de fichiers local ou sur un serveur Chroma en cours d’exécution, avec miroirs linguistiques anglais/français, upserts en arrière-plan et aller-retour JSONL.
- **Recherche RAG** — récupération hybride, reranking par cross-encoder, routage linguistique, mode de preuves sélectionnées, génération diffusée en continu et annulable, mémoire de provenance des réponses et des affirmations, bibliothèque de réponses mise en cache et évaluation par LLM.
- **Rôles** — comptes Administrateur et Chercheur; les chercheurs voient un texte de preuves résumé et ne peuvent pas modifier les corpus.
- **Sauvegarde et restauration** — une seule archive ZIP contenant les espaces de travail, l’historique d’audit, les profils de fournisseurs, les actifs sources du corpus et chaque collection Chroma avec ses embeddings.
- **Bilingue et accessible** — l’anglais et le français canadien sont des langues de première classe, avec parité des clés imposée. L’accès au clavier, le focus visible, le comportement réactif avec redistribution du contenu, la prise en charge des couleurs forcées et la conformité WCAG 2.2 AA font partie des critères d’acceptation.

Consultez le [Guide de l’utilisateur](docs/USER_GUIDE.md) pour la référence complète des fonctionnalités.

## Architecture

<!-- prettier-ignore -->
| Service     | Pile technologique                                                   | Notes                                                                                                                                                  |
| ----------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, servi par nginx | Transmet `/api/` vers l’API; Storybook est offert comme service de développement facultatif                                                          |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | Les fichiers d’autorité du corpus/de construction et l’état SQLite d’authentification/système/provenance résident sous `./data`; Chroma conserve les projections dérivées de recherche/résultats |
| Backend LLM | Ollama (par défaut) ou tout point de terminaison compatible OpenAI  | S’exécute sur l’hôte ou ailleurs; ne fait pas partie de la pile Compose par défaut                                                                     |

Pour les limites de responsabilité du code et de persistance, consultez [Architecture](docs/ARCHITECTURE.md).

## Prise en main

Les étapes suivantes constituent le chemin pris en charge à partir d’un dépôt fraîchement cloné. Elles sont volontairement explicites afin qu’un nouveau développeur puisse les répéter sans dépendre d’un répertoire de données DerridAI existant ni d’un environnement shell préconfiguré.

### 1. Prérequis

Installez Git, Docker Engine/Desktop avec la commande `docker compose`, ainsi qu’un point de terminaison LLM. La configuration par défaut suppose qu’Ollama s’exécute sur l’hôte.

Les modèles Ollama par défaut sont :

```text
gemma4:e2b
bge-m3:latest
```

Si vous utilisez un autre modèle Ollama ou un fournisseur compatible OpenAI, modifiez `.env` avant de démarrer DerridAI.

### 2. Cloner et configurer

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

Équivalent PowerShell :

```powershell
Copy-Item .env.example .env
```

Sous Docker Desktop avec WSL, définissez `HOST_UID` et `HOST_GID` dans `.env` avec la sortie de `id -u` et `id -g`. Ainsi, les fichiers Chroma/SQLite montés par bind restent la propriété de votre utilisateur hôte.

N’exportez pas globalement dans votre shell les variables de stockage de test DerridAI telles que `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` ou `CHROMA_PATH`. Compose interpole les variables exportées avant que les valeurs du fichier soient transmises au conteneur.

### 3. Rendre les modèles configurés disponibles

Pour Ollama déjà en cours d’exécution sur l’hôte :

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Le fichier `.env.example` par défaut utilise :

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Vous pouvez aussi utiliser le service Ollama Compose facultatif :

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Définissez ensuite `OLLAMA_BASE_URL=http://ollama:11434` dans `.env`.

### 4. Valider la configuration Compose et démarrer DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Les liaisons par défaut sont l’application <http://localhost:8181>, l’API <http://127.0.0.1:8000> et la documentation de l’API <http://127.0.0.1:8000/docs>.

Au premier lancement, DerridAI vous demande de créer le compte administrateur initial. Aucun identifiant par défaut n’est fourni.

### 5. Vérifier l’installation

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Le point de terminaison live devrait retourner du JSON contenant `"ok": true`, la version de l’application et le commit Git intégré lorsqu’il est disponible. Les services `web` et `api` devraient être signalés comme sains dans `docker compose ps`.

Pour un diagnostic local plus complet :

```bash
./scripts/diagnose.sh
```

PowerShell :

```powershell
.\scripts\diagnose.ps1
```

### 6. Arrêter ou reconstruire

Arrêtez l’application sans supprimer le répertoire `./data` monté par bind :

```bash
docker compose down
```

Reconstruisez après avoir récupéré des changements :

```bash
docker compose down
docker compose up -d --build
```

Si une version antérieure a laissé des fichiers appartenant à root sous `data/`, exécutez `./scripts/fix-data-permissions.sh` sur les hôtes de type Unix pris en charge.

## Configuration de développement

La CI utilise Python 3.12 et Node 22; utilisez ces versions localement pour reproduire les échecs.

Environnement backend/tests :

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Environnement frontend :

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Exécutez les contrôles locaux rapides de qualité depuis la racine du dépôt :

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py
mypy
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py

cd web
npm run format:repo:check
npm run lint
npm run typecheck
npm run typecheck:tests
npm run test:unit
npm run build
```

Utilisez `npm run format:repo` depuis `web/` pour formater tous les fichiers source, de configuration et de documentation pris en charge par Prettier dans le dépôt. Le HTML généré des anciens instantanés DOM est intentionnellement exclu.

Pour la couverture navigateur, Storybook, la parité CI et les règles de contribution, consultez [CONTRIBUTING.md](CONTRIBUTING.md).

## Carte du dépôt

- `api/app/` — application FastAPI, ingestion/révision du corpus, provenance, persistance, RAG, fournisseurs et tâches d’arrière-plan.
- `web/src/` — application Vue, composants réutilisables, modules de domaine, stores et couche de compatibilité avec l’ancien runtime, en voie de réduction.
- `tests/` — tests backend, de régression et de contrat.
- `web/tests/frontend/` — tests de composants et de domaine Vitest.
- `web/tests/e2e/` — couverture Playwright de l’application, Storybook, accessibilité et caractérisation de l’ancien comportement.
- `docs/` — contrats actuels d’architecture et de domaine, ainsi que les notes de version historiques sous `docs/notes/`.
- `data/` — état d’exécution local; ignoré par Git à l’exception des espaces réservés. Ne validez jamais son contenu.

## Documentation

Commencez par les documents qui décrivent le comportement actuel :

- [Guide de l’utilisateur](docs/USER_GUIDE.md) — référence des fonctionnalités, opérations, sauvegarde et limites
- [Architecture](docs/ARCHITECTURE.md) — limites d’exécution, autorité, persistance et flux de données
- [Contexte du projet](docs/PROJECT_CONTEXT.md) — justification savante et capacités mises en œuvre par rapport aux capacités prévues
- [Contribution](CONTRIBUTING.md) — configuration du développeur humain, contrôles de qualité et règles de modification
- [AGENTS.md](AGENTS.md) — règles supplémentaires pour les agents de codage
- Contrats ciblés : [ingestion des sources](docs/INGESTION_VALIDATION.md), [schémas de métadonnées](docs/METADATA_SCHEMAS.md), [migration FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md), [mémoire des métadonnées](docs/METADATA_MEMORY.md), [jetons de conception](docs/DESIGN_TOKENS.md) et [localisation fr-CA](docs/LOCALIZATION_FR_CA.md)

L’historique des versions se trouve dans [CHANGELOG.md](CHANGELOG.md) et `docs/notes/<version>.md`. Les notes propres à une version sont des archives historiques; elles ne constituent ni l’architecture actuelle ni les documents du carnet de travail.

## Licence

Copyright © 2026 Aaron John Schlosser, PhD. DerridAI est distribué sous la [GNU Affero General Public License, version 3](LICENSE) (`AGPL-3.0-only`). L’écran de connexion, le menu du compte et Paramètres → À propos de DerridAI affichent `© 2026 The New England Transcendental Club of California`.
