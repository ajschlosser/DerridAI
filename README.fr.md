<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

![Logo DerridAI](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI est un environnement de recherche axé sur l’exécution locale et la préservation de la provenance, conçu pour créer, réviser, rechercher et interroger des corpus savants. Il réunit l’ingestion de sources, la construction de corpus avec validation humaine, l’enrichissement de métadonnées lié aux preuves, des index de recherche/vectoriels dérivés et une génération augmentée par récupération (RAG) fondée sur les preuves dans une seule application Docker.

DerridAI est aussi l’implémentation de référence d’origine de **cELF 1.0 — Capta-Enriched Lexical Format**, une architecture d’information qui préserve la provenance pour la recherche documentaire assistée par IA. L’implémentation maintient séparément l’identité des sources, l’identité et les révisions des notices, les assertions de métadonnées, les preuves, les affirmations générées et leurs liens de support, plutôt que de les aplatir dans une base vectorielle opaque.

Version actuelle : **0.81.0 — Fall River** ([notes de version](docs/notes/0.81.0.md)). Ce README décrit l’architecture actuelle de `master`, y compris les travaux postérieurs à Exeter déjà fusionnés dans le dépôt.

## Ce que fait DerridAI

- **Acquisition et ingestion de sources hétérogènes.** Importez PDF, texte brut, RTF, DOCX, images et audio; importez des URL et du contenu Project Gutenberg; ou utilisez Corpus Capture pour découvrir et acquérir des œuvres via des adaptateurs tels que Wikidata, Project Gutenberg et Wikisource. L’ingestion applique des limites de sécurité et de ressources propres au média et conserve la provenance de l’extracteur, de l’outil et de sa version.
- **Construction de corpus adaptée au média.** Corpus Builder sépare l’enregistrement de la source, l’extraction/transcription, le repérage des unités source, la structure/segmentation, l’enrichissement, la construction des notices, la révision et la publication. Les contrôles et coordonnées de preuve s’adaptent au média au lieu d’imposer des concepts de page/PDF à toutes les sources.
- **Provenance cELF et autorité des champs.** Les `FieldAssertion` canoniques distinguent dérivation, évaluation, autorité, état de valeur, confiance, preuve, acteur/modèle, identité stable du champ et révision de notice. Une confirmation humaine n’efface pas la provenance du modèle ou d’une procédure déterministe.
- **Révision des notices avec les preuves en contexte.** Les réviseurs peuvent modifier texte et métadonnées, inspecter les `SourceSpan` et les preuves provenant d’autres notices, comparer les révisions, parcourir cartes sémantiques et relations, accepter ou rejeter des suggestions et publier des décisions auditables. Les enregistrements optimistes maintiennent une interface réactive tout en sérialisant les écritures conflictuelles sur une même notice.
- **Schémas de métadonnées configurables et précédents révisés.** Les schémas définissent des champs stables, types, valeurs contrôlées, règles de preuve/révision, indices POS/NER, portée du champ, consignes au modèle et politique de récupération. Les exemples révisés deviennent des précédents bornés et liés à des preuves pour les enrichissements futurs, sans remplacer les décisions canoniques du réviseur.
- **Document Intelligence optionnelle.** Une couche d’analyse dérivée et indépendante du fournisseur peut ajouter entités, coréférence, locuteurs de citations et relations de contenu sémantique. Les packs spaCy constituent la base multilingue; un worker BookNLP isolé est disponible comme amélioration facultative en anglais. Ces annotations restent des analyses reconstruisibles, jamais une preuve source ni une autorité du corpus.
- **Recherche dans des projections dérivées sans les confondre avec le corpus.** ChromaDB stocke des projections sémantiques/de recherche et des caches reconstruisibles, en mode embarqué ou serveur HTTP. Recherche dense, lexicale, MMR, fusion RRF, filtres, routage linguistique et réordonnancement borné par cross-encoder sont disponibles selon le contexte.
- **Research/RAG fondé sur les preuves.** Research prend en charge la récupération hybride, le reranking, un mode de preuves sélectionnées, des budgets de preuve, la génération diffusée et annulable, le rendu déterministe des citations, la persistance des affirmations/supports, la validation des affirmations, la mémoire des réponses/affirmations et l’évaluation par LLM. Les notices dont la provenance est incomplète sont exclues des preuves au lieu d’être considérées silencieusement comme un support valide.
- **Inspection et configuration des pipelines d’IA.** Pipeline Studio expose définitions versionnées, affectations, traces d’exécution, métriques de latence/erreur/fallback par étape, traces au point d’utilisation, comparaison A/B Research non persistante et benchmarks Research à cas fixes. Les étapes de récupération, mémoire, précédents de métadonnées et suggestions de preuves peuvent être explicites, tandis que les garde-fous de provenance et d’autorité restent structurels.
- **Transports API distincts selon la responsabilité.** REST possède les commandes et mutations; une façade GraphQL cELF en lecture seule compose des lectures typées; un canal WebSocket authentifié envoie les notifications d’opérations en temps réel. Les messages temps réel ne constituent jamais l’état canonique et les clients peuvent se resynchroniser depuis REST/GraphQL.
- **Recherche multi-utilisateur contrôlée.** Les rôles intégrés Administrateur et Chercheur, ainsi que des rôles personnalisés limités aux fonctions sûres pour les chercheurs, sont appliqués par l’interface et l’API. Le texte source visible par les chercheurs est résumé à la frontière API, les jobs sont associés à leur propriétaire et les mutations corpus/système réservées aux administrateurs restent inaccessibles.
- **Opérations longues observables.** Builds de corpus, révision LLM, RAG, notation, imports, modèles/packs linguistiques et mises à jour vectorielles apparaissent comme des opérations annulables avec instantanés/historique durables et progression en temps réel. Après un redémarrage, un travail interrompu en mémoire est marqué en échec plutôt que rejoué silencieusement.
- **Interface accessible et multilingue.** L’anglais et le français canadien sont les locales de première classe avec parité de clés imposée; la couverture des README est plus large. WCAG 2.2 AA, clavier, focus visible, reflow, réduction des animations, couleurs forcées/contraste élevé et tests de chaînes longues/localisation font partie des critères de livraison. Le Centre d’aide fournit des guides par page, des FAQ de workflow et un glossaire en langage clair.
- **Sauvegarde de l’environnement de recherche.** Sauvegarde/restauration couvre espaces de travail, historique d’audit, profils de fournisseurs, actifs source, état système/provenance et collections Chroma avec leurs embeddings.

Voir le [Guide de l’utilisateur](docs/USER_GUIDE.md) pour la référence complète des fonctionnalités.

## Modèle de traçabilité cELF

Le modèle savant de DerridAI suit la distinction cELF entre l’état documentaire/savant faisant autorité et les projections informatiques reconstruisibles. À traçabilité complète, le chemin conceptuel est :

```text
SourceDocument
  -> SourceSpan
  -> Record
  -> RecordRevision
  -> FieldAssertion
  -> Evidence Acquisition
  -> EvidenceRef
  -> EvidencePacket
  -> GenerationRun
  -> GeneratedClaim
  -> SupportBinding
```

Ainsi, une affirmation générée peut être auditée en remontant vers son support, sa preuve, la révision de notice, le segment source et le document source. Embeddings, rang de récupération, scores de reranker, caches, état de l’interface et autres valeurs propres à une opération restent des états dérivés; ils ne deviennent pas des propriétés intrinsèques de la notice source.

Voir [SPECIFICATION.md](SPECIFICATION.md) pour la spécification normative cELF 1.0.

## Architecture

### Services d’exécution

- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js et nginx. C’est l’application navigateur; elle proxifie `/api/` et consomme REST, GraphQL et les notifications temps réel. Storybook est un profil de développement facultatif.
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, le client ChromaDB, PyMuPDF, sentence-transformers et spaCy. C’est la frontière applicative faisant autorité pour l’authentification, les opérations source/corpus, les lectures cELF, la provenance, RAG, les pipelines, les jobs et l’état système.
- `document-nlp` — worker BookNLP facultatif et isolé pour Document Intelligence en anglais. Il reçoit du texte révisé borné et n’a aucune autorité sur le corpus.
- `chroma` — serveur HTTP Chroma facultatif. `PersistentClient` embarqué reste le mode par défaut; les deux modes stockent des projections de recherche/vectorielles dérivées.
- `ollama` — service Ollama local facultatif. DerridAI peut aussi utiliser Ollama déjà actif sur l’hôte ou tout endpoint compatible OpenAI configuré.

La pile Compose par défaut démarre `web` et `api`; les autres services sont des profils facultatifs ou des fournisseurs externes.

### Autorité et persistance

DerridAI ne traite volontairement pas tous les stockages comme également autoritatifs :

- **État savant canonique** — actifs/identité des sources, notices et révisions, assertions de champ, décisions de révision, liens exacts de preuve/support et état de publication.
- **État serveur durable** — authentification et état système/provenance/jobs/pipelines dans SQLite sous `./data`.
- **État dérivé/reconstruisible** — index Chroma, embeddings, projections d’exemples de métadonnées, scores de récupération, projections de contenu sémantique, sorties Document Intelligence et caches.
- **État d’espace de travail du navigateur** — préférences et travail non enregistré, séparés de l’autorité du corpus.

### Séparation des transports

- **REST** : toutes les commandes et mutations, notamment imports, décisions de révision, jobs, publication, administration, sauvegarde et restauration.
- **GraphQL** : façade de requêtes typées cELF en lecture seule à `POST /api/graphql`; aucune racine mutation ou subscription.
- **WebSocket** : canal authentifié de notifications à `WS /api/ws/events`; jamais source de vérité.

Pour le détail des modules, frontières de persistance et flux de données, voir [Architecture](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md) et [Realtime](docs/REALTIME.md).

## Démarrage

### 1. Prérequis

Installez Git, Docker Engine/Desktop avec la commande `docker compose` et un endpoint LLM. La configuration par défaut attend Ollama sur l’hôte.

Modèles par défaut :

```text
gemma4:e2b
bge-m3:latest
```

### 2. Cloner et configurer

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell :

```powershell
Copy-Item .env.example .env
```

Avec Docker Desktop sous WSL, définissez `HOST_UID` et `HOST_GID` dans `.env` avec la sortie de `id -u` et `id -g`.

N’exportez pas globalement les variables de stockage de test telles que `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` ou `CHROMA_PATH`; Compose donne priorité aux variables déjà exportées lors de l’interpolation.

### 3. Préparer les modèles

Avec Ollama déjà actif sur l’hôte :

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Valeurs par défaut :

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Ou utilisez le profil Compose Ollama :

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Puis définissez `OLLAMA_BASE_URL=http://ollama:11434`.

### 4. Démarrer DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Endpoints par défaut :

- Application : <http://localhost:8181>
- API : <http://127.0.0.1:8000>
- Documentation OpenAPI : <http://127.0.0.1:8000/docs>

Au premier lancement, créez le compte administrateur initial dans le navigateur. Aucun identifiant par défaut n’est fourni.

### 5. Vérifier l’installation

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

La réponse doit contenir `"ok": true`, la version et, lorsqu’il est disponible, le commit Git intégré.

Diagnostic étendu :

```bash
./scripts/diagnose.sh
```

PowerShell :

```powershell
.\scripts\diagnose.ps1
```

### 6. Services facultatifs

```bash
# Ollama local
docker compose --profile ollama up -d ollama

# Serveur HTTP Chroma (puis CHROMA_MODE=http)
docker compose --profile chroma up -d chroma

# Extension BookNLP anglaise pour Document Intelligence
docker compose --profile document-nlp up -d document-nlp

# Surface de développement Storybook
docker compose --profile dev up storybook
```

Consultez [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) avant d’activer ou d’installer des packs NLP.

### 7. Arrêter ou reconstruire

```bash
docker compose down

# après récupération de changements
docker compose down
docker compose up -d --build
```

Si une ancienne version a laissé des fichiers appartenant à root sous `data/`, exécutez `./scripts/fix-data-permissions.sh` sur un système Unix compatible.

## Développement

La CI utilise Python 3.12 et Node 22.

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

Contrôles locaux rapides :

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

Utilisez `npm run format:repo` depuis `web/` pour formater tous les fichiers pris en charge par Prettier. Les snapshots HTML DOM legacy générés sont volontairement exclus.

Pour la couverture navigateur, Storybook, la parité CI et les règles de contribution, voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Carte du dépôt

- `api/app/` — backend FastAPI : sources/corpus, services de lecture cELF, GraphQL, temps réel, provenance, pipelines, RAG, fournisseurs, persistance et jobs.
- `web/src/` — application Vue 3 : vues, composants, stores Pinia, routage, clients API, client temps réel, domaines et couche de compatibilité legacy restante.
- `booknlp-worker/` — worker BookNLP facultatif et isolé.
- `tests/` — tests backend, régression, contrats, cohérence de version et architecture.
- `web/tests/frontend/` — tests Vitest.
- `web/tests/e2e/` — Playwright, Storybook, accessibilité et caractérisation.
- `docs/` — contrats d’architecture/domaines actuels et notes de version historiques.
- `data/` — état local d’exécution; ignoré par Git sauf fichiers de réservation. Ne jamais en committer le contenu.

## Documentation

- [Guide de l’utilisateur](docs/USER_GUIDE.md) — fonctionnalités et workflows
- [Architecture](docs/ARCHITECTURE.md) — exécution, autorité, persistance et flux
- [Spécification cELF 1.0](SPECIFICATION.md) — modèle normatif et exigences de conformité
- [Contexte du projet](docs/PROJECT_CONTEXT.md) — rationale savante et capacités implémentées/intentionnelles
- [GraphQL](docs/GRAPHQL.md) — façade de lecture cELF
- [Realtime](docs/REALTIME.md) — protocole WebSocket et resynchronisation
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — analyse linguistique dérivée et packs
- [Ingestion des sources](docs/INGESTION_VALIDATION.md) — sécurité, limites et fidélité d’extraction
- [Schémas de métadonnées](docs/METADATA_SCHEMAS.md) — contrats de champs configurables
- [Mémoire des métadonnées](docs/METADATA_MEMORY.md) — précédents révisés et frontières d’autorité
- [Migration FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md) — modèle d’assertion canonique
- [CONTRIBUTING.md](CONTRIBUTING.md) et [AGENTS.md](AGENTS.md) — règles de développement

L’historique des versions se trouve dans [CHANGELOG.md](CHANGELOG.md) et `docs/notes/<version>.md`. Les notes de version sont des archives historiques, pas la description de l’architecture actuelle.

## Licence

DerridAI est distribué sous la [GNU Affero General Public License v3.0](LICENSE).

Copyright © 2026 Aaron John Schlosser, PhD. L’application affiche également © 2026 The New England Transcendental Club of California.
