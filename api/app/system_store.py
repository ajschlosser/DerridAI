# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import re
import threading
from pathlib import Path
from typing import Any

from .config import settings
from .persistence import system_repository

# Server-owned configuration shared across browser sessions. Keeping researcher
# provider policy here avoids leaking provider API keys through client storage.
DEFAULT_EN_US: dict[str, str] = {
    "app.name": "DerridAI",
    "app.subtitle": "Corpus Viewer",
    "nav.dashboard": "Dashboard",
    "nav.records": "Records",
    "nav.record": "Record",
    "nav.works": "Works",
    "nav.search": "Search",
    "nav.pdf": "PDF Explorer",
    "nav.compare": "Compare",
    "nav.vector": "Vector Stores",
    "nav.rag": "Research",
    "nav.faq": "Response FAQ",
    "nav.cache": "Response Cache",
    "nav.providers": "LLM Providers",
    "nav.config": "Settings",
    "nav.users": "Users & roles",
    "ui.loading": "Loading…",
    "ui.search": "Search",
    "ui.clear": "Clear",
    "ui.expand_all": "Expand all",
    "ui.collapse_all": "Collapse all",
    "ui.copy_inline": "Copy inline citation",
    "ui.copy_full": "Copy full citation",
    "ui.add_evidence": "Add to evidence",
    "ui.remove_evidence": "Remove from evidence",
    "research.corpus_search": "Corpus search",
    "research.search_loading": "Searching the corpus…",
    "research.search_embedding": "Embedding your query and comparing it with the selected collection…",
    "research.search_empty": "Enter a query to search the selected corpus database.",
    "research.similarity": "Similarity",
    "research.similarity_help": "A ranking signal derived from vector distance. Higher values indicate closer semantic proximity; it is not a probability or confidence score.",
    "research.summary_policy": "Researcher view · Edmundson summary · 2–3 sentences",
    "dashboard.databases": "databases",
    "research.page_title": "Research",
    "research.page_subtitle": "Ask the corpus, inspect the evidence, and keep provenance attached to the answer.",
    "research.ask_title": "What are you researching?",
    "research.ask_help": "Ask a scholarly question. DerridAI will retrieve, rerank, synthesize, and bind the answer to inspectable evidence.",
    "research.question": "Research question",
    "research.question_placeholder": "Ask about a concept, passage, relation, attribution, or disagreement…",
    "research.instructions": "Additional instructions",
    "research.instructions_placeholder": "Optional constraints on framing, comparison, citation, or answer form.",
    "research.optional": "Optional",
    "research.added": "Added",
    "research.recent_questions": "Recent questions",
    "research.search_history": "Search recent questions",
    "research.no_recent_questions": "No matching recent questions.",
    "research.characters": "characters",
    "research.corpus": "Corpus",
    "research.context": "Research context",
    "research.no_database": "No corpus database",
    "research.retrieval": "Retrieval",
    "research.model": "Model",
    "research.none": "None",
    "research.profile": "Research profile",
    "research.retrieval_profile": "Retrieval",
    "research.answer_language": "Answer language",
    "research.language_auto": "Automatic",
    "research.language_help": "Source-language routing remains independent.",
    "research.model_auto": "Automatic model",
    "research.preset_balanced": "Balanced",
    "research.preset_precision": "High precision",
    "research.preset_recall": "High recall",
    "research.preset_evidence": "Selected evidence only",
    "research.preset_custom": "Custom",
    "research.retrieval_ready": "Retrieval ready",
    "research.no_profile": "No profile",
    "research.run": "Research",
    "research.starting": "Starting…",
    "research.runs": "Runs",
    "research.expert_settings": "Expert settings",
    "research.answer": "Answer",
    "research.copy_answer": "Copy answer",
    "research.grade": "Analyze & grade",
    "research.run_details": "Run details",
    "research.works_cited": "Works Cited",
    "research.evidence_records": "evidence records",
    "research.cached": "Cached",
    "research.rerun": "Re-run with these parameters",
    "research.answer_waiting": "Your research answer will appear here",
    "research.answer_waiting_help": "Ask a question above. The answer stays in the workspace with its evidence rather than opening in a modal.",
    "research.answer_evidence": "Answer evidence",
    "research.inspect_evidence": "Inspect evidence for",
    "research.evidence_panel": "Evidence",
    "research.evidence_list": "Evidence list",
    "research.evidence": "Evidence",
    "research.records": "records",
    "research.no_selected_evidence": "No pinned evidence",
    "research.no_selected_evidence_help": "Add records from Search, Works, or Record View. Retrieval can still find evidence automatically.",
    "research.speaker": "Speaker",
    "research.position_holder": "Position holder",
    "research.stance": "Stance",
    "research.discourse_role": "Discourse role",
    "research.target": "Target",
    "research.proposition_status": "Proposition status",
    "research.quoted_speaker": "Quoted speaker",
    "research.full_citation": "Full citation",
    "research.collection": "Collection",
    "research.rerank_score": "Rerank score",
    "research.selected_preview_unavailable": "Passage preview is unavailable for evidence selected before this release; the full record is resolved when Research runs.",
    "research.topics": "Topics",
    "research.concepts": "Concepts",
    "research.researcher_evidence_summary": "Corpus text may be summarized for researcher accounts.",
    "research.pipeline_options": "Retrieval, evidence & generation",
    "research.expert_help": "These settings are for reproducibility, evaluation, and unusual research tasks. Normal research should not require them.",
    "research.retrieval_expert_help": "Tune recall, rank fusion, reranking, and multilingual query routing.",
    "research.document_languages": "Document languages",
    "research.retrieval_routes": "Retrieval routes",
    "research.evidence_citations": "Evidence & citations",
    "research.evidence_citations_help": "Control evidence packet size and deterministic source binding.",
    "research.generation": "Generation",
    "research.researcher_profile_locked": "Generation settings are fixed by the administrator-approved Research profile.",
    "research.generation_override_help": "Optional per-run overrides; the saved provider profile is not changed.",
    "research.discover_models": "Discover models",
    "research.apply_settings": "Apply to Research",
    "research.invalid_provider_options": "Provider options must be a valid JSON object.",
    "research.research_history": "Research history",
    "research.current_run": "Current run",
    "research.pipeline_stage": "Pipeline stage",
    "research.retrieval_diagnostics": "Retrieval diagnostics",
    "research.provider": "Provider",
    "research.active_runs": "active",
    "research.retained_runs": "retained",
    "research.no_runs": "No Research runs yet",
    "research.no_runs_help": "Completed and active runs will appear here.",
    "research.untitled_run": "Untitled research run",
    "research.evidence_only": "Evidence only",
    "research.loading_workspace": "Loading Research workspace…",
    "research.question_restored": "Recent question restored",
    "research.answer_copied": "Answer copied",
    "research.settings_applied": "Research settings applied",
    "research.models_found": "models found",
    "research.rerun_loaded": "Run parameters loaded into the composer",
    "research.remove_run_confirm": "Remove this retained Research run and its result?",
    "research.prompt_required": "Enter a research question.",
    "research.auto_grade": "Auto-grade final response",
    "research.auto_grade_help": "Runs as the final background-pipeline step.",
    "research.bind_citations": "Bind evidence tags to citations",
    "research.bind_citations_help": "Validate evidence identifiers before final source formatting.",
    "research.cancelled": "Cancelled",
    "research.cancelling": "Cancelling",
    "research.clipboard_failed": "Could not access the clipboard",
    "research.complete": "Complete",
    "research.cross_encoder_model": "Cross-encoder model",
    "research.database_required": "A corpus database or selected evidence is required.",
    "research.decomposition_tokens": "Query-decomposition tokens",
    "research.evidence_required": "Select at least one evidence record for evidence-only research.",
    "research.failed": "Failed",
    "research.fetch_k_help": "MMR candidate pool",
    "research.grading_profile": "Grading profile",
    "research.include_works_cited": "Append Works Cited",
    "research.k_help": "Candidates retained per retrieval route",
    "research.lambda_help": "Relevance vs. diversity",
    "research.no_evidence_text": "No retained passage text for this evidence item.",
    "research.no_profile_configured": "No Research LLM profile is available.",
    "research.off": "Off",
    "research.on": "On",
    "research.provider_options": "Provider options JSON",
    "research.query_decomposition": "Query decomposition",
    "research.query_decomposition_help": "Generate subqueries and French formulations before retrieval.",
    "research.queued": "Queued",
    "research.record_char_limit": "Chars / evidence record",
    "research.rerank_top_n": "Rerank top N",
    "research.reranker": "Reranker",
    "research.research_in_progress": "Research in progress",
    "research.rrf_help": "Rank-fusion smoothing constant",
    "research.run_failed": "The Research run failed.",
    "research.running": "Running",
    "research.saved_prompt": "Saved prompt",
    "research.seed": "Seed",
    "research.temperature": "Temperature",
    "research.thinking": "Thinking",
    "research.total_char_limit": "Total evidence chars",
    "research.waiting": "Waiting for the pipeline…",
    "permissions.rag_denied": "Your role cannot run Research pipelines.",
    "rag.selected_evidence": "Selected evidence",
    "rag.skip_retrieval": "Use selected evidence only (skip retrieval)",
    "users.last_login": "Last login",
    "users.login_count": "Logins",
    "language.title": "Language",
    "language.manage": "Manage languages",
    "section.overview": "Overview",
    "section.corpus": "Corpus",
    "section.research": "Research",
    "section.tools": "Tools",
    "section.system": "System",
    "ui.open_jsonl": "Open JSONL",
    "ui.merge_tabs": "Merge tabs",
    "ui.create_subset": "Create subset",
    "ui.bulk_edit": "Bulk edit field",
    "ui.clean_ocr": "Clean OCR Artifacts",
    "ui.review_flagged": "Review flagged",
    "ui.auto_improve_flagged": "Auto-improve flagged",
    "ui.upsert_queue": "Upsert queue",
    "ui.operations": "Operations",
    "ui.export": "Export",
    "ui.edit_record": "Edit record",
    "ui.sign_out": "Sign out",
    "ui.previous": "Previous",
    "ui.next": "Next",
    "ui.records_loaded": "records loaded",
    "ui.columns": "Columns",
    "ui.actions": "Record actions",
    "ui.inline": "Inline",
    "ui.full": "Full",
    "ui.evidence": "Evidence",
    "ui.cancel": "Cancel",
    "ui.save": "Save",
    "ui.remove": "Remove",
    "ui.refresh": "Refresh",
    "ui.create": "Create",
    "ui.download": "Download",
    "ui.close": "Close",
    "ui.configure_columns": "Configure columns",
    "ui.no_matches": "No matches",
    "ui.loading_dictionary": "Loading dictionary…",
    "ui.record_actions": "Record actions",
    "ui.jsonl_tabs": "JSONL tabs",
    "ui.corpus_dbs": "corpus DBs",
    "ui.db_records": "DB records",
    "ui.cached_responses": "cached responses",
    "ui.authentication_authorization": "Authentication and authorization",
    "ui.language_dictionaries_translation": "Language dictionaries and translation",
    "ui.back": "Back",
    "ui.forward": "Forward",
    "ui.expand_sidebar": "Expand sidebar",
    "ui.collapse_sidebar": "Collapse sidebar",
    "users.title": "Users & roles",
    "users.description": "Admins can access the complete corpus workspace. Researchers can use Research plus read-only corpus database and work search; corpus text is server-side Edmundson summarized.",
    "users.create": "Create user",
    "users.create_help": "Researcher is the least-privileged role and is the recommended default.",
    "users.username": "Username",
    "users.temporary_password": "Temporary password",
    "users.role": "Role",
    "users.accounts": "Accounts",
    "users.refresh": "Refresh",
    "users.loading": "Loading users…",
    "users.never": "Never",
    "users.reset_password": "Reset password",
    "users.delete": "Delete",
    "users.researcher_profiles": "Researcher LLM profiles",
    "users.researcher_profiles_help": "Only these static profiles are available to researchers. Provider secrets stay server-side. Local Ollama profiles respect max concurrency; additional researcher RAG jobs wait for an available slot.",
    "users.new_password": "New password",
    "users.password_help": "Minimum 6 characters.",
    "users.delete_help": "This removes the account and all of its active sessions. Existing RAG job data is not deleted automatically.",
    "language.page_title": "Languages & internationalization",
    "language.page_description": "Built-in locales are U.S. English and French (Canada). Install additional locale dictionaries by ISO language-location code using an LLM, then edit every UI string directly.",
    "language.install": "Install language",
    "language.install_dictionary": "Install translated dictionary",
    "language.install_help": "The canonical en-US dictionary is translated with the selected provider. Keys remain unchanged.",
    "language.locale_code": "Locale code",
    "language.name": "Name",
    "language.flag": "Flag / symbol",
    "language.provider": "Provider",
    "language.model": "Model",
    "language.base_url": "Base URL",
    "language.api_key": "API key",
    "language.installed": "Installed locales",
    "language.add_key": "Add key",
    "language.key": "Key",
    "language.translation": "Translation",
    "language.remove_confirm": "Remove language?",
    "language.remove_language": "Remove language",
    "role.admin": "Administrator",
    "role.researcher": "Researcher",
    "research.workspace": "Research workspace",
    "research.readonly_policy": "RAG and corpus DB/work search are read-only. Text is returned as 2–3 sentence Edmundson summaries.",
    "research.readonly_chip": "Read-only corpus · Edmundson summaries",
    "ui.active": "Active",
    "ui.disabled": "Disabled",
    "ui.created": "created",
    "ui.enable": "Enable",
    "ui.disable": "Disable",
    "ui.saving": "Saving…",
    "ui.working": "Working…",
    "ui.set_password": "Set password",
    "ui.change_role": "Change role",
    "ui.current_role_locked": "Your current role cannot be changed from this row.",
    "ui.cannot_disable_self": "You cannot disable your current account.",
    "ui.cannot_delete_self": "You cannot delete your current account.",
    "users.save_profiles": "Save profiles",
    "users.add_profile": "Add profile",
    "users.profile_required": "Profile ID, name, and model are required.",
    "language.translating": "Translating…",
    "language.translate_install": "Translate & install",
    "language.save_dictionary": "Save dictionary",
    "language.remove_key": "Remove dictionary key",
    "language.translated_keys": "translated keys",
    "research.section": "Research",
    "research.browse_description": "Browse works and search vector databases without exposing editable or full-text corpus records.",
    "research.corpus_database": "Corpus database",
    "research.semantic_search": "Semantic DB search",
    "research.semantic_help": "Search the selected collection. Returned text is summarized before it reaches this browser.",
    "research.search_placeholder": "Search the corpus semantically",
    "research.no_matches": "No matching records. Try a broader query or another corpus database.",
}

DEFAULT_FR_CA: dict[str, str] = {
    "app.name": "DerridAI",
    "app.subtitle": "Visualiseur de corpus",
    "nav.dashboard": "Tableau de bord",
    "nav.records": "Fiches",
    "nav.record": "Fiche",
    "nav.works": "Œuvres",
    "nav.search": "Recherche",
    "nav.pdf": "Explorateur PDF",
    "nav.compare": "Comparer",
    "nav.vector": "Bases vectorielles",
    "nav.rag": "Recherche RAG",
    "nav.faq": "FAQ des réponses",
    "nav.cache": "Cache des réponses",
    "nav.providers": "Fournisseurs LLM",
    "nav.config": "Configuration",
    "nav.users": "Utilisateurs et rôles",
    "ui.loading": "Chargement…",
    "ui.search": "Rechercher",
    "ui.clear": "Effacer",
    "ui.expand_all": "Tout développer",
    "ui.collapse_all": "Tout réduire",
    "ui.copy_inline": "Copier la citation abrégée",
    "ui.copy_full": "Copier la citation complète",
    "ui.add_evidence": "Ajouter aux preuves",
    "ui.remove_evidence": "Retirer des preuves",
    "research.corpus_search": "Recherche dans le corpus",
    "research.search_loading": "Recherche dans le corpus…",
    "research.search_embedding": "Vectorisation de la requête et comparaison avec la collection sélectionnée…",
    "research.search_empty": "Entrez une requête pour rechercher dans la base de corpus sélectionnée.",
    "research.similarity": "Similarité",
    "research.similarity_help": "Signal de classement dérivé de la distance vectorielle. Une valeur plus élevée indique une plus grande proximité sémantique; ce n’est ni une probabilité ni un niveau de confiance.",
    "research.summary_policy": "Vue chercheur · résumé Edmundson · 2–3 phrases",
    "dashboard.databases": "bases",
    "research.page_title": "Recherche",
    "research.page_subtitle": "Interrogez le corpus, examinez les preuves et gardez la provenance liée à la réponse.",
    "research.ask_title": "Que recherchez-vous?",
    "research.ask_help": "Posez une question savante. DerridAI repère, reclasse et synthétise les passages pertinents, puis relie la réponse à des preuves vérifiables.",
    "research.question": "Question de recherche",
    "research.question_placeholder": "Interrogez un concept, un passage, une relation, une attribution ou un désaccord…",
    "research.instructions": "Instructions supplémentaires",
    "research.instructions_placeholder": "Contraintes facultatives sur le cadrage, la comparaison, les citations ou la forme de la réponse.",
    "research.optional": "Facultatif",
    "research.added": "Ajouté",
    "research.recent_questions": "Questions récentes",
    "research.search_history": "Rechercher dans les questions récentes",
    "research.no_recent_questions": "Aucune question récente correspondante.",
    "research.characters": "caractères",
    "research.corpus": "Corpus",
    "research.context": "Contexte de recherche",
    "research.no_database": "Aucune base de corpus",
    "research.retrieval": "Récupération",
    "research.model": "Modèle",
    "research.none": "Aucun",
    "research.profile": "Profil de recherche",
    "research.retrieval_profile": "Récupération",
    "research.answer_language": "Langue de réponse",
    "research.language_auto": "Automatique",
    "research.language_help": "Le routage par langue source reste indépendant.",
    "research.model_auto": "Modèle automatique",
    "research.preset_balanced": "Équilibré",
    "research.preset_precision": "Haute précision",
    "research.preset_recall": "Rappel élevé",
    "research.preset_evidence": "Preuves sélectionnées seulement",
    "research.preset_custom": "Personnalisé",
    "research.retrieval_ready": "Récupération prête",
    "research.no_profile": "Aucun profil",
    "research.run": "Rechercher",
    "research.starting": "Démarrage…",
    "research.runs": "Exécutions",
    "research.expert_settings": "Paramètres experts",
    "research.answer": "Réponse",
    "research.copy_answer": "Copier la réponse",
    "research.grade": "Analyser et évaluer",
    "research.run_details": "Détails de l’exécution",
    "research.works_cited": "Ouvrages cités",
    "research.evidence_records": "preuves",
    "research.cached": "Mise en cache",
    "research.rerun": "Relancer avec ces paramètres",
    "research.answer_waiting": "Votre réponse de recherche apparaîtra ici",
    "research.answer_waiting_help": "Posez une question ci-dessus. La réponse reste dans l’espace de travail avec ses preuves plutôt que dans une fenêtre modale.",
    "research.answer_evidence": "Preuves de la réponse",
    "research.inspect_evidence": "Examiner les preuves pour",
    "research.evidence_panel": "Preuves",
    "research.evidence_list": "Liste des preuves",
    "research.evidence": "Preuve",
    "research.records": "fiches",
    "research.no_selected_evidence": "Aucune preuve épinglée",
    "research.no_selected_evidence_help": "Ajoutez des fiches depuis Recherche, Œuvres ou la vue Fiche. La récupération peut toujours trouver des preuves automatiquement.",
    "research.speaker": "Locuteur",
    "research.position_holder": "Détenteur de la position",
    "research.stance": "Position",
    "research.discourse_role": "Rôle discursif",
    "research.target": "Cible",
    "research.proposition_status": "Statut de la proposition",
    "research.quoted_speaker": "Locuteur cité",
    "research.full_citation": "Citation complète",
    "research.collection": "Collection",
    "research.rerank_score": "Score de reclassement",
    "research.selected_preview_unavailable": "L’aperçu du passage n’est pas disponible pour les preuves sélectionnées avant cette version; la fiche complète est résolue lors de la recherche.",
    "research.topics": "Thèmes",
    "research.concepts": "Concepts",
    "research.researcher_evidence_summary": "Le texte du corpus peut être résumé pour les comptes chercheur.",
    "research.pipeline_options": "Récupération, preuves et génération",
    "research.expert_help": "Ces paramètres servent à la reproductibilité, à l’évaluation et aux tâches inhabituelles. Une recherche normale ne devrait pas les exiger.",
    "research.retrieval_expert_help": "Réglez le rappel, la fusion de rangs, le reclassement et le routage multilingue.",
    "research.document_languages": "Langues des documents",
    "research.retrieval_routes": "Voies de récupération",
    "research.evidence_citations": "Preuves et citations",
    "research.evidence_citations_help": "Contrôlez la taille du paquet de preuves et la liaison déterministe des sources.",
    "research.generation": "Génération",
    "research.researcher_profile_locked": "Les paramètres de génération sont fixés par le profil de recherche approuvé par l’administrateur.",
    "research.generation_override_help": "Remplacements facultatifs pour cette exécution; le profil enregistré n’est pas modifié.",
    "research.discover_models": "Découvrir les modèles",
    "research.apply_settings": "Appliquer à la recherche",
    "research.invalid_provider_options": "Les options du fournisseur doivent former un objet JSON valide.",
    "research.research_history": "Historique de recherche",
    "research.current_run": "Exécution actuelle",
    "research.pipeline_stage": "Étape du pipeline",
    "research.retrieval_diagnostics": "Diagnostics de récupération",
    "research.active_runs": "actives",
    "research.retained_runs": "conservées",
    "research.no_runs": "Aucune exécution de recherche",
    "research.no_runs_help": "Les exécutions terminées et actives apparaîtront ici.",
    "research.untitled_run": "Recherche sans titre",
    "research.evidence_only": "Preuves seulement",
    "research.loading_workspace": "Chargement de l’espace de recherche…",
    "research.question_restored": "Question récente restaurée",
    "research.answer_copied": "Réponse copiée",
    "research.settings_applied": "Paramètres de recherche appliqués",
    "research.models_found": "modèles trouvés",
    "research.rerun_loaded": "Paramètres chargés dans le composeur",
    "research.remove_run_confirm": "Retirer cette exécution de recherche et son résultat?",
    "research.prompt_required": "Entrez une question de recherche.",
    "research.auto_grade": "Évaluer automatiquement la réponse finale",
    "research.auto_grade_help": "S’exécute comme dernière étape du pipeline en arrière-plan.",
    "research.bind_citations": "Lier les balises de preuve aux citations",
    "research.bind_citations_help": "Valider les identifiants de preuve avant le formatage final des sources.",
    "research.cancelled": "Annulée",
    "research.cancelling": "Annulation",
    "research.clipboard_failed": "Impossible d’accéder au presse-papiers",
    "research.complete": "Terminée",
    "research.cross_encoder_model": "Modèle de cross-encoder",
    "research.database_required": "Une base de corpus ou des preuves sélectionnées sont requises.",
    "research.decomposition_tokens": "Jetons de décomposition de requête",
    "research.evidence_required": "Sélectionnez au moins une preuve pour une recherche limitée aux preuves.",
    "research.failed": "Échouée",
    "research.fetch_k_help": "Réservoir de candidats MMR",
    "research.grading_profile": "Profil d’évaluation",
    "research.include_works_cited": "Ajouter les ouvrages cités",
    "research.k_help": "Candidats conservés par voie de récupération",
    "research.lambda_help": "Pertinence par rapport à la diversité",
    "research.no_evidence_text": "Aucun passage conservé pour cette preuve.",
    "research.no_profile_configured": "Aucun profil LLM de recherche n’est disponible.",
    "research.off": "Désactivé",
    "research.on": "Activé",
    "research.provider_options": "Options du fournisseur en JSON",
    "research.query_decomposition": "Décomposition de la requête",
    "research.query_decomposition_help": "Générer des sous-requêtes et des formulations françaises avant la récupération.",
    "research.queued": "En file",
    "research.record_char_limit": "Caractères / preuve",
    "research.rerank_top_n": "N premiers à reclasser",
    "research.reranker": "Reclassement",
    "research.research_in_progress": "Recherche en cours",
    "research.rrf_help": "Constante de lissage de fusion des rangs",
    "research.run_failed": "L’exécution de recherche a échoué.",
    "research.running": "En cours",
    "research.saved_prompt": "Question enregistrée",
    "research.seed": "Graine",
    "research.temperature": "Température",
    "research.thinking": "Raisonnement",
    "research.total_char_limit": "Total de caractères de preuve",
    "research.waiting": "En attente du pipeline…",
    "permissions.rag_denied": "Votre rôle ne permet pas d’exécuter les pipelines de recherche.",
    "rag.selected_evidence": "Preuves sélectionnées",
    "rag.skip_retrieval": "Utiliser uniquement les preuves sélectionnées (sans récupération)",
    "users.last_login": "Dernière connexion",
    "users.login_count": "Connexions",
    "language.title": "Langue",
    "language.manage": "Gérer les langues",
    "section.overview": "Aperçu",
    "section.corpus": "Corpus",
    "section.research": "Recherche",
    "section.tools": "Outils",
    "section.system": "Système",
    "ui.open_jsonl": "Ouvrir JSONL",
    "ui.merge_tabs": "Fusionner les onglets",
    "ui.create_subset": "Créer un sous-ensemble",
    "ui.bulk_edit": "Modifier un champ en lot",
    "ui.clean_ocr": "Nettoyer les artefacts OCR",
    "ui.review_flagged": "Examiner les éléments signalés",
    "ui.auto_improve_flagged": "Améliorer les éléments signalés",
    "ui.upsert_queue": "File de synchronisation",
    "ui.operations": "Opérations",
    "ui.export": "Exporter",
    "ui.edit_record": "Modifier la fiche",
    "ui.sign_out": "Déconnexion",
    "ui.previous": "Précédent",
    "ui.next": "Suivant",
    "ui.records_loaded": "fiches chargées",
    "ui.columns": "Colonnes",
    "ui.actions": "Actions de la fiche",
    "ui.inline": "Abrégée",
    "ui.full": "Complète",
    "ui.evidence": "Preuve",
    "ui.cancel": "Annuler",
    "ui.save": "Enregistrer",
    "ui.remove": "Retirer",
    "ui.refresh": "Actualiser",
    "ui.create": "Créer",
    "ui.download": "Télécharger",
    "ui.close": "Fermer",
    "ui.configure_columns": "Configurer les colonnes",
    "ui.no_matches": "Aucun résultat",
    "ui.loading_dictionary": "Chargement du dictionnaire…",
    "ui.record_actions": "Actions de la fiche",
    "ui.jsonl_tabs": "onglets JSONL",
    "ui.corpus_dbs": "BD de corpus",
    "ui.db_records": "fiches en BD",
    "ui.cached_responses": "réponses en cache",
    "ui.authentication_authorization": "Authentification et autorisation",
    "ui.language_dictionaries_translation": "Dictionnaires de langue et traduction",
    "ui.back": "Retour",
    "ui.forward": "Suivant",
    "ui.expand_sidebar": "Développer la barre latérale",
    "ui.collapse_sidebar": "Réduire la barre latérale",
    "users.title": "Utilisateurs et rôles",
    "users.description": "Les administrateurs ont accès à tout l’espace de corpus. Les chercheurs peuvent utiliser la recherche RAG et consulter les bases et œuvres en lecture seule; le texte du corpus est résumé côté serveur avec Edmundson.",
    "users.create": "Créer un utilisateur",
    "users.create_help": "Chercheur est le rôle le moins privilégié et le choix recommandé par défaut.",
    "users.username": "Nom d’utilisateur",
    "users.temporary_password": "Mot de passe temporaire",
    "users.role": "Rôle",
    "users.accounts": "Comptes",
    "users.refresh": "Actualiser",
    "users.loading": "Chargement des utilisateurs…",
    "users.never": "Jamais",
    "users.reset_password": "Réinitialiser le mot de passe",
    "users.delete": "Supprimer",
    "users.researcher_profiles": "Profils LLM pour chercheurs",
    "users.researcher_profiles_help": "Seuls ces profils statiques sont offerts aux chercheurs. Les secrets restent côté serveur. Les profils Ollama locaux respectent la concurrence maximale; les requêtes RAG supplémentaires attendent qu’une place se libère.",
    "users.new_password": "Nouveau mot de passe",
    "users.password_help": "Minimum de 6 caractères.",
    "users.delete_help": "Cette action supprime le compte et toutes ses sessions actives. Les données des tâches RAG existantes ne sont pas supprimées automatiquement.",
    "language.page_title": "Langues et internationalisation",
    "language.page_description": "Les langues intégrées sont l’anglais américain et le français (Canada). Installez d’autres dictionnaires par code ISO langue-région avec un LLM, puis modifiez directement chaque chaîne d’interface.",
    "language.install": "Installer une langue",
    "language.install_dictionary": "Installer un dictionnaire traduit",
    "language.install_help": "Le dictionnaire canonique en-US est traduit avec le fournisseur choisi. Les clés restent inchangées.",
    "language.locale_code": "Code de langue",
    "language.name": "Nom",
    "language.flag": "Drapeau / symbole",
    "language.provider": "Fournisseur",
    "language.model": "Modèle",
    "language.base_url": "URL de base",
    "language.api_key": "Clé API",
    "language.installed": "Langues installées",
    "language.add_key": "Ajouter une clé",
    "language.key": "Clé",
    "language.translation": "Traduction",
    "language.remove_confirm": "Supprimer la langue?",
    "language.remove_language": "Supprimer la langue",
    "role.admin": "Administrateur",
    "role.researcher": "Chercheur",
    "research.workspace": "Espace de recherche",
    "research.readonly_policy": "La recherche RAG et la consultation des bases et œuvres sont en lecture seule. Le texte est retourné sous forme de résumés Edmundson de 2 à 3 phrases.",
    "research.readonly_chip": "Corpus en lecture seule · résumés Edmundson",
    "ui.active": "Actif",
    "ui.disabled": "Désactivé",
    "ui.created": "créé",
    "ui.enable": "Activer",
    "ui.disable": "Désactiver",
    "ui.saving": "Enregistrement…",
    "ui.working": "Traitement…",
    "ui.set_password": "Définir le mot de passe",
    "ui.change_role": "Changer le rôle",
    "ui.current_role_locked": "Votre rôle actuel ne peut pas être modifié dans cette ligne.",
    "ui.cannot_disable_self": "Vous ne pouvez pas désactiver votre compte actuel.",
    "ui.cannot_delete_self": "Vous ne pouvez pas supprimer votre compte actuel.",
    "users.save_profiles": "Enregistrer les profils",
    "users.add_profile": "Ajouter un profil",
    "users.profile_required": "L’identifiant, le nom et le modèle du profil sont requis.",
    "language.translating": "Traduction…",
    "language.translate_install": "Traduire et installer",
    "language.save_dictionary": "Enregistrer le dictionnaire",
    "language.remove_key": "Supprimer la clé du dictionnaire",
    "language.translated_keys": "clés traduites",
    "research.section": "Recherche",
    "research.browse_description": "Parcourez les œuvres et recherchez dans les bases vectorielles sans exposer de fiches modifiables ni le texte intégral du corpus.",
    "research.corpus_database": "Base de corpus",
    "research.semantic_search": "Recherche sémantique en BD",
    "research.semantic_help": "Recherchez dans la collection sélectionnée. Le texte retourné est résumé avant d’atteindre ce navigateur.",
    "research.search_placeholder": "Rechercher sémantiquement dans le corpus",
    "research.no_matches": "Aucune fiche correspondante. Essayez une requête plus générale ou une autre base de corpus.",
}


# 0.30.5: work metadata enrichment, annotation organization, workflow UI,
# and dictionary-editor descriptions. Keep English and French key sets exact.
DEFAULT_EN_US.update({
    "nav.annotations": "Annotations",
    "dynamic.records": "records",
    "dynamic.works": "works",
    "ui.actions": "Actions",
    "ui.more_actions": "More actions",
    "ui.default": "Default",
    "ui.select_all": "Select all",
    "language.install_kicker": "New interface language",
    "language.install_steps": "Installation steps",
    "language.step_identity": "Language",
    "language.step_provider": "Provider profile",
    "language.step_review": "Install",
    "language.identity_section": "Language identity",
    "language.identity_section_help": "Choose the locale code and the label people will see in the language picker.",
    "language.locale_code_help": "BCP 47 locale identifier, for example de-DE or es-MX.",
    "language.name_help": "Human-readable language name shown in the picker.",
    "language.flag_help": "Unicode emoji or symbol shown beside the locale name.",
    "language.translation_section": "Translation provider",
    "language.translation_section_help": "Use an existing LLM provider profile so model, endpoint, credentials, and generation defaults stay consistent with the rest of DerridAI.",
    "language.provider_profile": "Provider profile",
    "language.concurrent_requests": "max concurrent request(s)",
    "language.model_not_set": "model not set",
    "language.provider_profile_help": "Uses the same provider profiles and model defaults as Research, PDF tools, and LLM review.",
    "language.provider_profile_required": "Configure an LLM provider profile before installing a dictionary.",
    "language.provider_model_required": "The selected provider profile does not have a model configured.",
    "language.no_provider_profiles": "No LLM provider profiles are configured",
    "language.no_provider_profiles_help": "Create a provider profile first, then return here to translate a dictionary.",
    "language.manage_providers": "Manage provider profiles",
    "language.new_language": "New language",
    "language.locale_pending": "Locale code required",
    "language.provider_pending": "Provider profile required",
    "language.install_review_note": "After installation, review and edit every translated field in the dictionary table.",
    "language.locale_count": "languages",
    "language.field_description": "Description",
    "language.description_nav": "Navigation label",
    "language.description_ui": "Interface action, status, or helper text",
    "language.description_users": "User and role management text",
    "language.description_language": "Language-settings interface text",
    "language.description_research": "Research workspace text",
    "language.description_rag": "Research and RAG workflow text",
    "language.description_section": "Section heading",
    "language.description_role": "Role label",
    "language.description_app": "Application identity text",
    "language.description_generic": "Interface text",
    "language.remove_help": "The installed dictionary will be deleted from this DerridAI instance.",
    "works.loading": "Loading works",
    "works.checking_database": "Checking vector database state…",
    "works.overview": "Work overview",
    "works.cover_alt": "Cover of {work}",
    "works.source_files": "source files",
    "works.search_records": "Search records",
    "works.edit_metadata": "Edit metadata",
    "works.populate_metadata_llm": "Populate metadata with LLM",
    "works.populate_metadata_help": "DerridAI searches Open Library, asks the selected LLM to identify the best edition, then returns proposed metadata changes for review. Nothing is applied automatically.",
    "works.populate_all_metadata": "Populate all metadata with LLM",
    "works.populate_all_metadata_label": "Populate metadata · {count} works",
    "works.unknown_author": "Unknown author",
    "works.translated_by": "Translated by",
    "works.sync": "Sync",
    "works.sync_all": "Sync all works",
    "works.review_flagged": "Review flagged ({count})",
    "works.auto_improve": "Auto-improve flagged",
    "works.remove_entire": "Remove entire work",
    "works.need_review": "need review",
    "works.files": "files",
    "works.filter_title": "Filter works by title",
    "works.shown": "shown",
    "works.select_collection": "Select a corpus collection first.",
    "works.loading_cards": "Loading {count} work cards",
    "works.all_records_label": "records across all works",
    "works.mixed": "Mixed",
    "works.mixed_across_records": "Mixed across records",
    "works.no_provider_profiles": "No LLM provider profiles are configured",
    "works.no_provider_profiles_help": "Create an LLM provider profile before populating work metadata.",
    "works.no_work_metadata_rows": "No work records are available for metadata lookup.",
    "works.provider_profile": "Provider profile",
    "works.provider_profile_help": "Uses the same configured provider profiles as RAG, PDF tools, and LLM review.",
    "works.provider_required": "Select an LLM provider profile.",
    "works.provider_model_required": "The selected provider profile does not have a model configured.",
    "works.concurrent_requests": "max concurrent request(s)",
    "works.metadata_workflow_kicker": "Bibliographic enrichment",
    "works.step_scope": "Works",
    "works.step_provider": "Provider profile",
    "works.step_review": "Review proposals",
    "works.lookup_scope": "Lookup scope",
    "works.lookup_scope_help": "Retrieve bibliographic metadata for {count} work(s).",
    "works.metadata_fields_help": "Proposals can include publisher, publication year/place, edition, translator, ISBN, language, citation, and cover image.",
    "works.background_operation": "Background operation",
    "works.background_operation_help": "You can leave the Works page. Open the completed operation to review and apply proposed changes.",
    "works.catalog_source": "Catalogue source",
    "works.start_metadata_lookup": "Start background lookup",
    "works.starting_metadata_lookup": "Starting…",
    "works.metadata_lookup_started": "Metadata lookup started for {count} work(s).",
    "works.metadata_lookup_failed": "Could not start metadata lookup",
    "works.review_metadata_proposals": "Review work metadata proposals",
    "works.proposed_field_changes": "proposed field changes",
    "works.metadata_no_match_count": "{count} work(s) had no usable catalogue match or returned an error.",
    "works.proposal_edit_help": "Edit proposed values if needed, then apply selected fields across every loaded record belonging to that work.",
    "works.field": "Field",
    "works.current_value": "Current",
    "works.proposed_value": "Proposed",
    "works.source_reason": "Source / reason",
    "works.catalogue_selected": "Open Library catalogue match selected by the LLM.",
    "works.no_metadata_changes": "No metadata changes were proposed.",
    "works.unmatched_works": "Unmatched / failed works",
    "works.no_catalogue_match": "No catalogue match",
    "works.apply_selected_metadata": "Apply selected metadata",
    "works.select_metadata_changes": "Select at least one proposed metadata change.",
    "works.apply_metadata_confirm": "Apply work metadata?",
    "works.apply_metadata_confirm_help": "Apply selected metadata across {works} work(s) and {records} associated records?",
    "works.apply_metadata": "Apply metadata",
    "works.metadata_applied": "Updated {records} records · {fields} tracked field changes",
    "works.no_works_to_populate": "No works are available to populate.",
    "works.open_overview": "Open work overview",
    "annotations.page_help": "Review annotations across the corpus. The default view groups discussion by work; switch to Recent for a chronological stream.",
    "annotations.search_placeholder": "Search annotations, tags, quotes, records, or works…",
    "annotations.by_work": "By work",
    "annotations.recent": "Recent",
    "annotations.annotation_count": "annotations",
    "annotations.recent_annotations": "Recent annotations",
    "annotations.recent_help": "Newest annotations across all loaded works.",
    "annotations.empty": "No annotations match the current search.",
    "annotations.open_record": "Open record",
    "annotations.record_note": "Record note",
    "annotations.unknown_author": "Unknown author",
    "annotations.view_all": "View all",
    "annotations.none_yet": "No annotations yet.",
    "dashboard.latest_annotation": "Latest annotation",
    "dashboard.latest_annotation_help": "Most recent corpus annotation",
})
DEFAULT_FR_CA.update({
    "nav.annotations": "Annotations",
    "dynamic.records": "fiches",
    "dynamic.works": "œuvres",
    "ui.actions": "Actions",
    "ui.more_actions": "Autres actions",
    "ui.default": "Par défaut",
    "ui.select_all": "Tout sélectionner",
    "language.install_kicker": "Nouvelle langue d’interface",
    "language.install_steps": "Étapes de l’installation",
    "language.step_identity": "Langue",
    "language.step_provider": "Profil fournisseur",
    "language.step_review": "Installation",
    "language.identity_section": "Identité de la langue",
    "language.identity_section_help": "Choisissez le code régional et le libellé affiché dans le sélecteur de langue.",
    "language.locale_code_help": "Identifiant régional BCP 47, par exemple de-DE ou es-MX.",
    "language.name_help": "Nom lisible affiché dans le sélecteur de langue.",
    "language.flag_help": "Émoji ou symbole Unicode affiché à côté du nom de la langue.",
    "language.translation_section": "Fournisseur de traduction",
    "language.translation_section_help": "Utilisez un profil fournisseur LLM existant afin que le modèle, le point de terminaison, les identifiants et les réglages restent cohérents avec le reste de DerridAI.",
    "language.provider_profile": "Profil fournisseur",
    "language.concurrent_requests": "requête(s) simultanée(s) max.",
    "language.model_not_set": "modèle non défini",
    "language.provider_profile_help": "Utilise les mêmes profils fournisseurs et paramètres de modèle que Recherche, les outils PDF et la révision LLM.",
    "language.provider_profile_required": "Configurez un profil fournisseur LLM avant d’installer un dictionnaire.",
    "language.provider_model_required": "Le profil fournisseur sélectionné n’a pas de modèle configuré.",
    "language.no_provider_profiles": "Aucun profil fournisseur LLM n’est configuré",
    "language.no_provider_profiles_help": "Créez d’abord un profil fournisseur, puis revenez ici pour traduire un dictionnaire.",
    "language.manage_providers": "Gérer les profils fournisseurs",
    "language.new_language": "Nouvelle langue",
    "language.locale_pending": "Code régional requis",
    "language.provider_pending": "Profil fournisseur requis",
    "language.install_review_note": "Après l’installation, vérifiez et modifiez chaque champ traduit dans le tableau du dictionnaire.",
    "language.locale_count": "langues",
    "language.field_description": "Description",
    "language.description_nav": "Libellé de navigation",
    "language.description_ui": "Action, état ou aide de l’interface",
    "language.description_users": "Texte de gestion des utilisateurs et rôles",
    "language.description_language": "Texte des paramètres de langue",
    "language.description_research": "Texte de l’espace Recherche",
    "language.description_rag": "Texte des flux Recherche et RAG",
    "language.description_section": "Titre de section",
    "language.description_role": "Libellé de rôle",
    "language.description_app": "Texte d’identité de l’application",
    "language.description_generic": "Texte d’interface",
    "language.remove_help": "Le dictionnaire installé sera supprimé de cette instance DerridAI.",
    "works.loading": "Chargement des œuvres",
    "works.checking_database": "Vérification de la base vectorielle…",
    "works.overview": "Aperçu de l’œuvre",
    "works.cover_alt": "Couverture de {work}",
    "works.source_files": "fichiers sources",
    "works.search_records": "Rechercher les fiches",
    "works.edit_metadata": "Modifier les métadonnées",
    "works.populate_metadata_llm": "Renseigner les métadonnées avec le LLM",
    "works.populate_metadata_help": "DerridAI interroge Open Library, demande au LLM sélectionné d’identifier la meilleure édition, puis renvoie des modifications proposées à vérifier. Rien n’est appliqué automatiquement.",
    "works.populate_all_metadata": "Renseigner toutes les métadonnées avec le LLM",
    "works.populate_all_metadata_label": "Renseigner les métadonnées · {count} œuvres",
    "works.unknown_author": "Auteur inconnu",
    "works.translated_by": "Traduit par",
    "works.sync": "Synchroniser",
    "works.sync_all": "Synchroniser toutes les œuvres",
    "works.review_flagged": "Examiner les signalements ({count})",
    "works.auto_improve": "Améliorer les signalements",
    "works.remove_entire": "Supprimer toute l’œuvre",
    "works.need_review": "à examiner",
    "works.files": "fichiers",
    "works.filter_title": "Filtrer les œuvres par titre",
    "works.shown": "affichées",
    "works.select_collection": "Sélectionnez d’abord une collection de corpus.",
    "works.loading_cards": "Chargement de {count} cartes d’œuvres",
    "works.all_records_label": "fiches de toutes les œuvres",
    "works.mixed": "Mixte",
    "works.mixed_across_records": "Valeurs mixtes selon les fiches",
    "works.no_provider_profiles": "Aucun profil fournisseur LLM n’est configuré",
    "works.no_provider_profiles_help": "Créez un profil fournisseur LLM avant de renseigner les métadonnées des œuvres.",
    "works.no_work_metadata_rows": "Aucune fiche d’œuvre n’est disponible pour la recherche de métadonnées.",
    "works.provider_profile": "Profil fournisseur",
    "works.provider_profile_help": "Utilise les mêmes profils fournisseurs configurés que RAG, les outils PDF et la révision LLM.",
    "works.provider_required": "Sélectionnez un profil fournisseur LLM.",
    "works.provider_model_required": "Le profil fournisseur sélectionné n’a pas de modèle configuré.",
    "works.concurrent_requests": "requête(s) simultanée(s) max.",
    "works.metadata_workflow_kicker": "Enrichissement bibliographique",
    "works.step_scope": "Œuvres",
    "works.step_provider": "Profil fournisseur",
    "works.step_review": "Vérifier les propositions",
    "works.lookup_scope": "Portée de la recherche",
    "works.lookup_scope_help": "Obtenir les métadonnées bibliographiques de {count} œuvre(s).",
    "works.metadata_fields_help": "Les propositions peuvent inclure l’éditeur, l’année/le lieu de publication, l’édition, le traducteur, l’ISBN, la langue, la citation et la couverture.",
    "works.background_operation": "Opération en arrière-plan",
    "works.background_operation_help": "Vous pouvez quitter la page Œuvres. Ouvrez l’opération terminée pour vérifier et appliquer les modifications proposées.",
    "works.catalog_source": "Source du catalogue",
    "works.start_metadata_lookup": "Lancer la recherche en arrière-plan",
    "works.starting_metadata_lookup": "Démarrage…",
    "works.metadata_lookup_started": "Recherche de métadonnées lancée pour {count} œuvre(s).",
    "works.metadata_lookup_failed": "Impossible de lancer la recherche de métadonnées",
    "works.review_metadata_proposals": "Vérifier les propositions de métadonnées",
    "works.proposed_field_changes": "modifications de champs proposées",
    "works.metadata_no_match_count": "{count} œuvre(s) n’ont pas de correspondance exploitable ou ont renvoyé une erreur.",
    "works.proposal_edit_help": "Modifiez les valeurs proposées si nécessaire, puis appliquez les champs sélectionnés à toutes les fiches chargées appartenant à cette œuvre.",
    "works.field": "Champ",
    "works.current_value": "Actuel",
    "works.proposed_value": "Proposé",
    "works.source_reason": "Source / justification",
    "works.catalogue_selected": "Correspondance Open Library sélectionnée par le LLM.",
    "works.no_metadata_changes": "Aucune modification de métadonnées n’a été proposée.",
    "works.unmatched_works": "Œuvres sans correspondance / en échec",
    "works.no_catalogue_match": "Aucune correspondance de catalogue",
    "works.apply_selected_metadata": "Appliquer les métadonnées sélectionnées",
    "works.select_metadata_changes": "Sélectionnez au moins une modification de métadonnées proposée.",
    "works.apply_metadata_confirm": "Appliquer les métadonnées de l’œuvre ?",
    "works.apply_metadata_confirm_help": "Appliquer les métadonnées sélectionnées à {works} œuvre(s) et {records} fiches associées ?",
    "works.apply_metadata": "Appliquer les métadonnées",
    "works.metadata_applied": "{records} fiches mises à jour · {fields} modifications de champs suivies",
    "works.no_works_to_populate": "Aucune œuvre n’est disponible à renseigner.",
    "works.open_overview": "Ouvrir l’aperçu de l’œuvre",
    "annotations.page_help": "Examinez les annotations du corpus. La vue par défaut les regroupe par œuvre; passez à Récentes pour un flux chronologique.",
    "annotations.search_placeholder": "Rechercher dans les annotations, étiquettes, citations, fiches ou œuvres…",
    "annotations.by_work": "Par œuvre",
    "annotations.recent": "Récentes",
    "annotations.annotation_count": "annotations",
    "annotations.recent_annotations": "Annotations récentes",
    "annotations.recent_help": "Annotations les plus récentes parmi toutes les œuvres chargées.",
    "annotations.empty": "Aucune annotation ne correspond à la recherche actuelle.",
    "annotations.open_record": "Ouvrir la fiche",
    "annotations.record_note": "Note de fiche",
    "annotations.unknown_author": "Auteur inconnu",
    "annotations.view_all": "Tout afficher",
    "annotations.none_yet": "Aucune annotation pour le moment.",
    "dashboard.latest_annotation": "Dernière annotation",
    "dashboard.latest_annotation_help": "Annotation de corpus la plus récente",
})

# Restored 0.30.x shell, search, researcher-workspace, and accessibility strings.
DEFAULT_EN_US.update({'annotations.researcher_help': 'Annotations are organized by work when available in the current workspace.', 'auth.assigned_account': 'Use your assigned DerridAI account.', 'auth.confirm_password': 'Confirm password', 'auth.create_admin': 'Create administrator', 'auth.create_first_admin': 'Create the first administrator', 'auth.first_admin_help': 'The first account is an administrator. Additional admin and researcher accounts can be created afterward.', 'auth.first_run': 'First-run setup', 'auth.password': 'Password', 'auth.password_note': 'Passwords must contain at least 6 characters. No default administrator credentials are created.', 'auth.passwords_no_match': 'Passwords do not match.', 'auth.required': 'Authentication required', 'auth.sign_in': 'Sign in', 'auth.sign_in_title': 'Sign in to DerridAI', 'auth.username': 'Username', 'auth.working': 'Working…', 'compare.need_two': 'Two records are needed', 'compare.need_two_help': 'Browse records or run a search first, then return to Compare.', 'compare.record_a': 'Record A', 'compare.record_b': 'Record B', 'context.global_search': 'Global Search', 'dashboard.advanced_filters': 'Advanced filters', 'dashboard.all_works': 'All works', 'dashboard.annotations': 'Annotations', 'dashboard.annotations_help': 'Collect notes, tags, and discussion threads attached to corpus evidence.', 'dashboard.browse_works': 'Browse works', 'dashboard.corpus_overview': 'Corpus Overview', 'dashboard.databases': 'Databases', 'dashboard.default_provider': 'Default provider', 'dashboard.global_search': 'Global Search', 'dashboard.interface_language': 'Interface language', 'dashboard.language_settings': 'Language Settings', 'dashboard.language_settings_help': 'Choose the interface language and manage translation dictionaries.', 'dashboard.llm_provider_help': 'Configure the provider used for LLM-assisted workflows.', 'dashboard.llm_provider_settings': 'LLM Provider Settings', 'dashboard.manage_languages': 'Manage languages', 'dashboard.manage_provider': 'Manage provider', 'dashboard.model': 'Model', 'dashboard.no_recent_activity': 'No recent tracked changes.', 'dashboard.no_record_selected': 'Open a record to keep it close at hand here.', 'dashboard.not_configured': 'Not configured', 'dashboard.quote': '“Il n’y a pas de hors-texte.”', 'dashboard.recent_activity': 'Recent Activity', 'dashboard.record': 'Record', 'dashboard.record_view': 'Record View', 'dashboard.records': 'Records', 'dashboard.search_corpus_placeholder': 'Search the corpus…', 'dashboard.search_help': 'Search across works, metadata, annotations, and—when available—the semantic database.', 'dashboard.start_searching': 'Start searching', 'dashboard.tagline': 'Search. Compare. Annotate. Always already.', 'dashboard.top_avg_record_length': 'Top 5 Works by Average Record Length', 'dashboard.top_works_records': 'Top 5 Works by Record Count', 'dashboard.total_words': 'Total words', 'dashboard.updated_record': 'Updated record', 'dashboard.view_all_works': 'View all works', 'dashboard.welcome': 'Welcome to DerridAI', 'dashboard.works': 'Works', 'dashboard.year_not_recorded': 'Year not recorded', 'dynamic.selected_evidence': 'selected evidence', 'language.english_us': 'English', 'language.french_ca': 'Français (Canada)', 'nav.home': 'Home', 'nav.more_tools': 'More tools', 'operations.drag_help': 'Drag operations anywhere · double-click to reset', 'operations.foreground_sync_active_help': 'Wait for the current large foreground sync to finish before starting another.', 'operations.foreground_sync_active_title': 'Large sync already running', 'operations.foreground_sync_batch': 'Committing records {start}–{end} of {total}', 'operations.foreground_sync_committed': 'Committed {count} records', 'operations.foreground_sync_complete': 'Completed {count} records without creating a background operation.', 'operations.foreground_sync_done': 'Synced {count} records to {store}', 'operations.foreground_sync_failed': 'Sync failed: {message}', 'operations.foreground_sync_failed_title': 'Large sync failed', 'operations.foreground_sync_help': 'Large syncs run in small foreground batches so the browser remains responsive.', 'operations.foreground_sync_title': 'Syncing {count} records', 'operations.minimize': 'Minimize operations', 'operations.show': 'Show operations', 'record.find_text': 'Find in record text', 'record.matches': 'matches', 'record.metadata': 'Metadata', 'record.summary': 'Researcher summary', 'research.add_filter': 'Add filter', 'research.add_metadata_filter': 'Add metadata filter', 'research.clear_filters': 'Clear filters', 'research.compare_help': 'Compare researcher-visible summarized records side by side.', 'research.filter_value': 'Exact filter value', 'research.filter_works': 'Filter works by title', 'research.filters_only': 'Filters only', 'research.global_search_admin_help': 'Search loaded records or switch to semantic search in the selected corpus database.', 'research.global_search_help': 'Search summarized records by text or switch to semantic ranking in the selected corpus database.', 'research.loaded_record_search_placeholder': 'Search record text across all loaded files', 'research.loading_databases': 'Loading corpus databases…', 'research.metadata_filters': 'Metadata filters', 'research.no_database': 'No corpus database available', 'research.no_database_admin_help': 'Create or restore a corpus database to use semantic search.', 'research.no_database_help': 'An administrator must create or restore a corpus database before researcher search and Research can be used.', 'research.no_filters': 'No database filters applied.', 'research.no_records': 'No records available', 'research.no_works': 'No works loaded yet.', 'research.none_selected': 'No database selected', 'research.open': 'Open', 'research.recent_activity_private': 'Local edit activity is visible to administrators.', 'research.record_actions': 'Record actions', 'research.record_search_empty': 'Run a search to find summarized records.', 'research.record_search_placeholder': 'Search record text…', 'research.results': 'results', 'research.search_failed': 'Search failed', 'research.search_method': 'Search method', 'research.search_results': 'Search results', 'research.selected_database_help': 'Searches run against this selected database only.', 'research.semantic_db_search': 'Semantic DB Search', 'research.traditional_search': 'Record search', 'research.works_menu_help': 'Browse works in the selected corpus database. Select a work for an overview, then browse its summarized records.', 'settings.appearance': 'Appearance', 'settings.appearance_help': 'Choose the interface color theme for your workspace.', 'settings.appearance_saved': 'Appearance saved', 'settings.browser_workspace_note': 'Theme preferences are saved in this browser workspace.', 'settings.color_theme': 'Color theme', 'settings.researcher_workspace': 'Research workspace', 'settings.researcher_workspace_help': 'Researcher accounts use summarized corpus text and do not expose database or source-management controls.', 'settings.save_appearance': 'Save appearance', 'settings.theme_blue': 'Reference blue', 'settings.theme_blue_help': 'The blue palette used in the visual reference.', 'settings.theme_green': 'DerridAI green', 'settings.theme_green_help': 'The original restrained green palette.', 'settings.theme_slate': 'Slate', 'settings.theme_slate_help': 'A neutral graphite-blue research palette.', 'time.days_ago': '{count} d ago', 'time.hours_ago': '{count} hr ago', 'time.just_now': 'just now', 'time.minutes_ago': '{count} min ago', 'time.recently': 'Recently', 'ui.admin_actions': 'Actions', 'ui.close_file': 'Close file', 'ui.copied': 'Copied', 'ui.corpus_viewer': 'Corpus Viewer', 'ui.edit': 'Edit', 'ui.global_search_placeholder': 'Search the corpus, works, concepts, or annotations…', 'ui.loading_derridai': 'Loading DerridAI…', 'ui.navigation_history': 'Navigation history', 'ui.need_records_bulk_edit': 'Load JSONL records before bulk editing.', 'ui.need_records_export': 'Load JSONL records before exporting.', 'ui.need_records_ocr': 'Load JSONL records before cleaning OCR artifacts.', 'ui.need_records_subset': 'Load JSONL records before creating a subset.', 'ui.need_two_tabs_merge': 'Load at least two JSONL tabs to merge them.', 'ui.none': 'None', 'ui.primary_navigation': 'Primary navigation', 'ui.selected': 'Selected', 'ui.skip_to_content': 'Skip to main content', 'works.browse_records': 'Browse records', 'works.untitled': 'Untitled work', 'nav.dashboard': 'Home', 'nav.record': 'Record View', 'nav.rag': 'Research', 'nav.config': 'Settings', 'users.description': 'Admins can access the complete corpus workspace. Researchers can use Research plus read-only corpus DB/work search; corpus text is server-side Edmundson summarized.'})
DEFAULT_FR_CA.update({'annotations.researcher_help': 'Les annotations sont organisées par œuvre lorsqu’elles sont disponibles dans l’espace de travail actuel.', 'auth.assigned_account': 'Utilisez le compte DerridAI qui vous a été attribué.', 'auth.confirm_password': 'Confirmer le mot de passe', 'auth.create_admin': 'Créer l’administrateur', 'auth.create_first_admin': 'Créer le premier administrateur', 'auth.first_admin_help': 'Le premier compte est administrateur. D’autres comptes administrateur et chercheur peuvent ensuite être créés.', 'auth.first_run': 'Configuration initiale', 'auth.password': 'Mot de passe', 'auth.password_note': 'Les mots de passe doivent comporter au moins 6 caractères. Aucun identifiant administrateur par défaut n’est créé.', 'auth.passwords_no_match': 'Les mots de passe ne correspondent pas.', 'auth.required': 'Authentification requise', 'auth.sign_in': 'Se connecter', 'auth.sign_in_title': 'Se connecter à DerridAI', 'auth.username': 'Nom d’utilisateur', 'auth.working': 'Traitement…', 'compare.need_two': 'Deux fiches sont nécessaires', 'compare.need_two_help': 'Parcourez des fiches ou lancez une recherche, puis revenez à Comparer.', 'compare.record_a': 'Fiche A', 'compare.record_b': 'Fiche B', 'context.global_search': 'Recherche globale', 'dashboard.advanced_filters': 'Filtres avancés', 'dashboard.all_works': 'Toutes les œuvres', 'dashboard.annotations': 'Annotations', 'dashboard.annotations_help': 'Rassemblez les notes, étiquettes et fils de discussion associés aux preuves du corpus.', 'dashboard.browse_works': 'Parcourir les œuvres', 'dashboard.corpus_overview': 'Aperçu du corpus', 'dashboard.databases': 'Bases de données', 'dashboard.default_provider': 'Fournisseur par défaut', 'dashboard.global_search': 'Recherche globale', 'dashboard.interface_language': 'Langue de l’interface', 'dashboard.language_settings': 'Paramètres de langue', 'dashboard.language_settings_help': 'Choisissez la langue de l’interface et gérez les dictionnaires de traduction.', 'dashboard.llm_provider_help': 'Configurez le fournisseur utilisé pour les flux assistés par LLM.', 'dashboard.llm_provider_settings': 'Paramètres du fournisseur LLM', 'dashboard.manage_languages': 'Gérer les langues', 'dashboard.manage_provider': 'Gérer le fournisseur', 'dashboard.model': 'Modèle', 'dashboard.no_recent_activity': 'Aucune modification suivie récente.', 'dashboard.no_record_selected': 'Ouvrez une fiche pour la garder à portée de main ici.', 'dashboard.not_configured': 'Non configuré', 'dashboard.quote': '« Il n’y a pas de hors-texte. »', 'dashboard.recent_activity': 'Activité récente', 'dashboard.record': 'Fiche', 'dashboard.record_view': 'Vue de fiche', 'dashboard.records': 'Fiches', 'dashboard.search_corpus_placeholder': 'Rechercher dans le corpus…', 'dashboard.search_help': 'Recherchez dans les œuvres, les métadonnées, les annotations et, lorsqu’elle est disponible, la base sémantique.', 'dashboard.start_searching': 'Commencer la recherche', 'dashboard.tagline': 'Rechercher. Comparer. Annoter. Toujours déjà.', 'dashboard.top_avg_record_length': '5 principales œuvres par longueur moyenne des fiches', 'dashboard.top_works_records': '5 principales œuvres par nombre de fiches', 'dashboard.total_words': 'Nombre total de mots', 'dashboard.updated_record': 'Fiche mise à jour', 'dashboard.view_all_works': 'Voir toutes les œuvres', 'dashboard.welcome': 'Bienvenue dans DerridAI', 'dashboard.works': 'Œuvres', 'dashboard.year_not_recorded': 'Année non indiquée', 'dynamic.selected_evidence': 'preuves sélectionnées', 'language.english_us': 'Anglais (É.-U.)', 'language.french_ca': 'Français (Canada)', 'nav.home': 'Accueil', 'nav.more_tools': 'Autres outils', 'operations.drag_help': 'Faites glisser les opérations n’importe où · double-cliquez pour réinitialiser', 'operations.foreground_sync_active_help': 'Attendez la fin de la grande synchronisation au premier plan avant d’en lancer une autre.', 'operations.foreground_sync_active_title': 'Grande synchronisation déjà en cours', 'operations.foreground_sync_batch': 'Validation des fiches {start} à {end} sur {total}', 'operations.foreground_sync_committed': '{count} fiches validées', 'operations.foreground_sync_complete': '{count} fiches terminées sans créer d’opération en arrière-plan.', 'operations.foreground_sync_done': '{count} fiches synchronisées vers {store}', 'operations.foreground_sync_failed': 'Échec de la synchronisation : {message}', 'operations.foreground_sync_failed_title': 'Échec de la grande synchronisation', 'operations.foreground_sync_help': 'Les grandes synchronisations sont traitées par petits lots au premier plan afin que le navigateur reste réactif.', 'operations.foreground_sync_title': 'Synchronisation de {count} fiches', 'operations.minimize': 'Réduire les opérations', 'operations.show': 'Afficher les opérations', 'record.find_text': 'Rechercher dans le texte de la fiche', 'record.matches': 'correspondances', 'record.metadata': 'Métadonnées', 'record.summary': 'Résumé chercheur', 'research.add_filter': 'Ajouter un filtre', 'research.add_metadata_filter': 'Ajouter un filtre de métadonnées', 'research.clear_filters': 'Effacer les filtres', 'research.compare_help': 'Comparez côte à côte les fiches résumées visibles par les chercheurs.', 'research.filter_value': 'Valeur exacte du filtre', 'research.filter_works': 'Filtrer les œuvres par titre', 'research.filters_only': 'Filtres uniquement', 'research.global_search_admin_help': 'Recherchez dans les fiches chargées ou passez à la recherche sémantique dans la base de corpus sélectionnée.', 'research.global_search_help': 'Recherchez dans les fiches résumées par texte ou passez au classement sémantique dans la base de corpus sélectionnée.', 'research.loaded_record_search_placeholder': 'Rechercher dans le texte des fiches de tous les fichiers chargés', 'research.loading_databases': 'Chargement des bases de corpus…', 'research.metadata_filters': 'Filtres de métadonnées', 'research.no_database': 'Aucune base de corpus disponible', 'research.no_database_admin_help': 'Créez ou restaurez une base de corpus pour utiliser la recherche sémantique.', 'research.no_database_help': 'Un administrateur doit créer ou restaurer une base de corpus avant que la recherche chercheur et Recherche puissent être utilisés.', 'research.no_filters': 'Aucun filtre de base de données appliqué.', 'research.no_records': 'Aucune fiche disponible', 'research.no_works': 'Aucune œuvre chargée.', 'research.none_selected': 'Aucune base sélectionnée', 'research.open': 'Ouvrir', 'research.recent_activity_private': 'L’activité locale de modification est visible par les administrateurs.', 'research.record_actions': 'Actions sur la fiche', 'research.record_search_empty': 'Lancez une recherche pour trouver des fiches résumées.', 'research.record_search_placeholder': 'Rechercher dans le texte des fiches…', 'research.results': 'résultats', 'research.search_failed': 'Échec de la recherche', 'research.search_method': 'Méthode de recherche', 'research.search_results': 'Résultats de recherche', 'research.selected_database_help': 'Les recherches portent uniquement sur cette base sélectionnée.', 'research.semantic_db_search': 'Recherche sémantique BD', 'research.traditional_search': 'Recherche de fiches', 'research.works_menu_help': 'Parcourez les œuvres de la base de corpus sélectionnée. Sélectionnez une œuvre pour voir son aperçu, puis parcourez ses fiches résumées.', 'settings.appearance': 'Apparence', 'settings.appearance_help': 'Choisissez le thème de couleur de votre espace de travail.', 'settings.appearance_saved': 'Apparence enregistrée', 'settings.browser_workspace_note': 'Les préférences de thème sont enregistrées dans cet espace de travail du navigateur.', 'settings.color_theme': 'Thème de couleur', 'settings.researcher_workspace': 'Espace de recherche', 'settings.researcher_workspace_help': 'Les comptes chercheur utilisent du texte de corpus résumé et n’affichent pas les contrôles de gestion des bases ou des sources.', 'settings.save_appearance': 'Enregistrer l’apparence', 'settings.theme_blue': 'Bleu de référence', 'settings.theme_blue_help': 'La palette bleue utilisée dans la référence visuelle.', 'settings.theme_green': 'Vert DerridAI', 'settings.theme_green_help': 'La palette verte sobre d’origine.', 'settings.theme_slate': 'Ardoise', 'settings.theme_slate_help': 'Une palette de recherche neutre, bleu graphite.', 'time.days_ago': 'il y a {count} j', 'time.hours_ago': 'il y a {count} h', 'time.just_now': 'à l’instant', 'time.minutes_ago': 'il y a {count} min', 'time.recently': 'Récemment', 'ui.admin_actions': 'Actions', 'ui.close_file': 'Fermer le fichier', 'ui.copied': 'Copié', 'ui.corpus_viewer': 'Visualiseur de corpus', 'ui.edit': 'Modifier', 'ui.global_search_placeholder': 'Rechercher dans le corpus, les œuvres, les concepts ou les annotations…', 'ui.loading_derridai': 'Chargement de DerridAI…', 'ui.navigation_history': 'Historique de navigation', 'ui.need_records_bulk_edit': 'Chargez des fiches JSONL avant la modification en lot.', 'ui.need_records_export': 'Chargez des fiches JSONL avant l’exportation.', 'ui.need_records_ocr': 'Chargez des fiches JSONL avant le nettoyage OCR.', 'ui.need_records_subset': 'Chargez des fiches JSONL avant de créer un sous-ensemble.', 'ui.need_two_tabs_merge': 'Chargez au moins deux onglets JSONL pour les fusionner.', 'ui.none': 'Aucun', 'ui.primary_navigation': 'Navigation principale', 'ui.selected': 'Sélectionné', 'ui.skip_to_content': 'Aller au contenu principal', 'works.browse_records': 'Parcourir les fiches', 'works.untitled': 'Œuvre sans titre', 'nav.dashboard': 'Accueil', 'nav.record': 'Vue de fiche', 'nav.rag': 'Recherche', 'nav.config': 'Paramètres', 'users.description': 'Les administrateurs ont accès à tout l’espace du corpus. Les chercheurs peuvent utiliser Recherche ainsi que la recherche en lecture seule dans les bases et les œuvres; le texte du corpus est résumé côté serveur avec Edmundson.'})

# Record-view accessibility/help strings restored from the 0.30.x line.
DEFAULT_EN_US.update({
    "record.add_evidence_help": "Add this record to the selected evidence set used by Research and evidence-only RAG runs.",
    "record.select_help": "Select this record for bulk review, editing, or synchronization actions.",
    "record.clear_find": "Clear find query",
    "record.clear_find_empty": "Enter a find query before clearing it.",
})
DEFAULT_FR_CA.update({
    "record.add_evidence_help": "Ajoutez cette fiche aux preuves sélectionnées utilisées par Recherche et les exécutions RAG fondées uniquement sur les preuves.",
    "record.select_help": "Sélectionnez cette fiche pour les actions de révision, modification ou synchronisation en lot.",
    "record.clear_find": "Effacer la recherche",
    "record.clear_find_empty": "Saisissez une recherche avant de l’effacer.",
})

_LOCALE_RE = re.compile(
    r"^(?P<language>[A-Za-z]{2,3})(?:-(?P<script>[A-Za-z]{4}))?(?:-(?P<region>[A-Za-z]{2}|[0-9]{3}))?(?:-(?P<variants>[A-Za-z0-9][A-Za-z0-9-]{0,24}))?$"
)

def normalize_locale_code(code: str) -> str:
    """Normalize the common BCP 47 forms used for interface locales.

    Supports language-only tags plus optional script, region, and variants, for
    example ``de``, ``pt-BR`` and ``zh-Hant-TW``. The parser remains deliberately
    conservative rather than accepting arbitrary private-use tags.
    """
    value = str(code or "").strip().replace("_", "-")
    match = _LOCALE_RE.fullmatch(value)
    if not match:
        raise ValueError("Language code must be a valid BCP 47 locale such as de-DE, pt-BR, or zh-Hant-TW.")
    parts = [match.group("language").lower()]
    script = match.group("script")
    region = match.group("region")
    variants = match.group("variants")
    if script:
        parts.append(script.title())
    if region:
        parts.append(region.upper() if region.isalpha() else region)
    if variants:
        parts.extend(part.lower() for part in variants.split("-") if part)
    return "-".join(parts)


DEFAULT_EN_US.update({"auth.session_expired":"Your session expired. Sign in again."})
DEFAULT_FR_CA.update({"auth.session_expired":"Votre session a expiré. Connectez-vous de nouveau."})


# 0.30.6 Vector Store Cleanup strings.
DEFAULT_EN_US.update({
    "vector.page_help": "Create, sync, browse, search, and export persistent Chroma collections used by DerridAI.",
    "vector.create_collection": "Create collection",
    "vector.create_collection_help": "Configure the collection first, then optionally sync loaded works.",
    "vector.new_collection": "New vector collection",
    "vector.creation_steps": "Collection creation steps",
    "vector.create_step_basics": "Collection",
    "vector.create_step_embedding": "Embeddings",
    "vector.create_step_sync": "Sync works",
    "vector.collection_basics": "Collection basics",
    "vector.collection_basics_help": "Name the collection and describe how DerridAI should treat it.",
    "vector.collection_name": "Collection name",
    "vector.collection_name_help": "Use a short stable name. You can browse and search it from Vector Stores.",
    "vector.collection_name_required": "Enter a collection name",
    "vector.collection_role": "Collection role",
    "vector.collection_role_help": "Primary collections are the main corpus database; language-specific collections are derived or scoped by language.",
    "vector.role_primary": "Primary",
    "vector.role_general": "General",
    "vector.role_language": "Language-specific",
    "vector.language_tags": "Language tags",
    "vector.language_tags_help": "Optional descriptive tags. Leave both unchecked for a mixed-language collection.",
    "vector.embedding_setup": "Embedding setup",
    "vector.embedding_setup_help": "Choose how new records in this collection will receive embeddings.",
    "vector.embedding_provider": "Embedding provider",
    "vector.provider_ollama": "Ollama",
    "vector.provider_ollama_help": "Generate embeddings with a configured local Ollama model.",
    "vector.provider_chroma": "Chroma default",
    "vector.provider_chroma_help": "Let Chroma use its default embedding function.",
    "vector.provider_precomputed": "Precomputed",
    "vector.provider_precomputed_help": "Records must already contain embedding vectors; semantic query embedding is unavailable.",
    "vector.embedding_model": "Embedding model",
    "vector.embedding_model_help": "This setting is locked once the collection contains records.",
    "vector.embedding_model_required": "Choose an Ollama embedding model",
    "vector.sync_available_works": "Sync available works",
    "vector.sync_available_works_help": "Optionally add loaded corpus works immediately after the collection is created. You can also leave the collection empty.",
    "vector.available_loaded_works": "Available loaded works",
    "vector.available_works_count": "{count} works from the current browser workspace",
    "vector.no_loaded_works": "No loaded JSONL works are available to sync.",
    "vector.create_large_sync_help": "Because this selection contains {count} records, DerridAI will sync it in foreground batches after creating the collection. Keep this tab open until it finishes.",
    "vector.create_and_sync": "Create & sync selected works",
    "vector.create_empty": "Create empty collection",
    "vector.creating_collection": "Creating collection…",
    "vector.selected_works_label": "{count} selected works",
    "vector.collection_created_sync": "Created {name}; selected works are syncing.",
    "vector.collection_created": "Created {name}",
    "vector.create_failed": "Could not create collection",
    "vector.empty_kicker": "Vector Stores",
    "vector.empty_title": "Create your first corpus collection",
    "vector.empty_help": "A vector collection gives DerridAI a persistent corpus database for semantic search, researcher browsing, and RAG. Configure the collection first, then optionally sync any works already loaded in the browser workspace.",
    "vector.create_first_collection": "Create first collection",
    "vector.summary": "Vector store summary",
    "vector.collections": "Collections",
    "vector.selected_collection": "Selected collection",
    "vector.collection_switch_help": "Choose a collection to manage or browse it.",
    "vector.collection": "Collection",
    "vector.unsynced_changes": "Unsynced local changes",
    "vector.unsynced_changes_count": "{count} unsynced local changes",
    "vector.unsynced_changes_what": "What is this list?",
    "vector.unsynced_changes_help": "These are browser-workspace records that changed since their last confirmed sync, plus records DerridAI has confirmed are missing from the selected collection. Removing an item suppresses only its current version; a later change queues it again.",
    "vector.no_unsynced_changes": "No confirmed unsynced local changes.",
    "vector.no_unsynced_changes_help": "DerridAI has not found any loaded workspace records that changed since their last sync or are confirmed missing from this collection.",
    "vector.sync_selected": "Sync selected",
    "vector.delete_collection": "Delete collection",
    "vector.role_language_title": "Role & language",
    "vector.role_language_help": "Collection role and language tags describe how this database should be used.",
    "vector.embedding_configuration": "Embedding configuration",
    "vector.embedding_locked_help": "Embedding settings are locked after records have been added. Create a new empty collection to change them.",
    "vector.embedding_edit_help": "Choose how DerridAI creates vectors for this collection.",
    "vector.model_not_used": "This provider does not use an Ollama model name.",
    "vector.import_export": "Import & export records",
    "vector.import_export_help": "Sync loaded JSONL records into this collection, or export collection records back to clean JSONL. Exporting does not modify the collection.",
    "vector.sync_into_collection": "Sync into collection",
    "vector.sync_active_jsonl": "Sync active JSONL",
    "vector.sync_all_loaded": "Sync all loaded JSONL",
    "vector.load_jsonl_first": "Load and select a JSONL tab first.",
    "vector.load_jsonl_any_first": "Load at least one JSONL tab first.",
    "vector.sync_behavior_help": "Sync updates matching records and inserts new ones. Any sync above 500 records requires confirmation, runs in foreground batches of 500, and blocks other DerridAI actions until it finishes or you cancel.",
    "vector.export_from_collection": "Export from collection",
    "vector.open_db_jsonl": "Open full collection as JSONL tab",
    "vector.download_db_jsonl": "Download full collection JSONL",
    "vector.open_current_work": "Open current work as JSONL",
    "vector.download_current_work": "Download current work",
    "vector.page_export_title": "Current table page",
    "vector.page_export_help": "Open only the records currently visible on this paginated table as a temporary JSONL tab. This is not a full collection export.",
    "vector.open_current_page": "Open current table page as JSONL tab",
    "vector.semantic_search": "Semantic search",
    "vector.semantic_search_help": "Find records by meaning using this collection's configured embedding provider.",
    "vector.semantic_precomputed_help": "Semantic search is unavailable because this collection stores precomputed vectors without a query embedding function.",
    "vector.semantic_search_placeholder": "Search this collection by meaning…",
    "vector.search_results_empty": "Search results will appear here.",
    "vector.language_collections": "Language collections",
    "vector.language_derive_help": "Create separate English and French collections by routing records according to document_language metadata.",
    "vector.generate_language_collections": "Generate EN / FR collections",
    "vector.advanced": "Advanced",
    "vector.select_collection": "Select a collection",
    "vector.select_collection_help": "Choose a collection from the list to manage settings, sync records, search, or browse its contents.",
    "vector.storage_settings": "Storage settings",
    "vector.storage_help": "Chroma persists its database in a server-side directory. The container path is the directory DerridAI sees; the host path is the mapped folder on the machine running DerridAI, which is what survives container restarts and is included in normal host backups.",
    "vector.container_path": "Container path",
    "vector.host_path": "Host folder",
    "vector.change_storage_path": "Change storage path",
    "vector.apply_storage_path": "Apply storage path",
    "vector.change_storage_warning": "Changing this path switches DerridAI to a different Chroma persistence directory. Existing collections remain in their original directory until you switch back.",
    "vector.enter_storage_path": "Enter a Chroma storage path",
    "vector.checking_path": "Checking…",
    "vector.storage_changed": "Chroma storage changed to {path}",
    "vector.storage_change_failed": "Could not change Chroma storage: {message}",
    "operations.large_sync_foreground_title": "Large sync runs in the foreground",
    "operations.large_sync_foreground_help": "{count} records will be synced in foreground batches so the browser stays responsive. Keep this DerridAI tab open until the sync finishes.",
    "operations.continue_sync": "Continue sync",
    "record.inline_citation": "Inline cite",
    "record.full_citation": "Full cite",
    "section.storage": "Storage",
    "ui.clear_selection": "Clear selection",
    "ui.delete": "Delete",
    "dynamic.page": "page",
    "research.all_records": "All records",
    "research.no_work_metadata": "No work metadata was found in this collection.",
    "research.of": "of",
    "ui.first_page": "Already on the first page.",
    "ui.last_page": "Already on the last page.",
    "ui.rows_per_page": "Rows per page",
    "vector.browse_works": "Browse works",
    "vector.browse_works_help": "Open a work to browse only its records in this collection.",
    "vector.open_work_records": "Open records",
})
DEFAULT_FR_CA.update({
    "vector.page_help": "Créez, synchronisez, parcourez, recherchez et exportez les collections Chroma persistantes utilisées par DerridAI.",
    "vector.create_collection": "Créer une collection",
    "vector.create_collection_help": "Configurez d’abord la collection, puis synchronisez éventuellement les œuvres chargées.",
    "vector.new_collection": "Nouvelle collection vectorielle",
    "vector.creation_steps": "Étapes de création de la collection",
    "vector.create_step_basics": "Collection",
    "vector.create_step_embedding": "Vectorisation",
    "vector.create_step_sync": "Synchroniser les œuvres",
    "vector.collection_basics": "Paramètres de base",
    "vector.collection_basics_help": "Nommez la collection et indiquez comment DerridAI doit l’utiliser.",
    "vector.collection_name": "Nom de la collection",
    "vector.collection_name_help": "Utilisez un nom court et stable. Vous pourrez la parcourir et la rechercher depuis les bases vectorielles.",
    "vector.collection_name_required": "Saisissez un nom de collection",
    "vector.collection_role": "Rôle de la collection",
    "vector.collection_role_help": "Les collections principales constituent la base du corpus; les collections linguistiques sont dérivées ou limitées par langue.",
    "vector.role_primary": "Principale",
    "vector.role_general": "Générale",
    "vector.role_language": "Spécifique à une langue",
    "vector.language_tags": "Étiquettes de langue",
    "vector.language_tags_help": "Étiquettes descriptives facultatives. Laissez les deux décochées pour une collection multilingue.",
    "vector.embedding_setup": "Configuration des vecteurs",
    "vector.embedding_setup_help": "Choisissez comment les nouveaux enregistrements de cette collection recevront leurs vecteurs.",
    "vector.embedding_provider": "Fournisseur de vecteurs",
    "vector.provider_ollama": "Ollama",
    "vector.provider_ollama_help": "Générer les vecteurs avec un modèle Ollama local configuré.",
    "vector.provider_chroma": "Chroma par défaut",
    "vector.provider_chroma_help": "Laisser Chroma utiliser sa fonction de vectorisation par défaut.",
    "vector.provider_precomputed": "Pré-calculés",
    "vector.provider_precomputed_help": "Les enregistrements doivent déjà contenir des vecteurs; la recherche sémantique par requête n’est pas disponible.",
    "vector.embedding_model": "Modèle de vectorisation",
    "vector.embedding_model_help": "Ce paramètre est verrouillé dès que la collection contient des enregistrements.",
    "vector.embedding_model_required": "Choisissez un modèle de vectorisation Ollama",
    "vector.sync_available_works": "Synchroniser les œuvres disponibles",
    "vector.sync_available_works_help": "Ajoutez éventuellement les œuvres du corpus déjà chargées juste après la création. Vous pouvez aussi laisser la collection vide.",
    "vector.available_loaded_works": "Œuvres chargées disponibles",
    "vector.available_works_count": "{count} œuvres dans l’espace de travail du navigateur",
    "vector.no_loaded_works": "Aucune œuvre JSONL chargée n’est disponible pour la synchronisation.",
    "vector.create_large_sync_help": "Comme cette sélection contient {count} enregistrements, DerridAI la synchronisera par lots au premier plan après la création. Gardez cet onglet ouvert jusqu’à la fin.",
    "vector.create_and_sync": "Créer et synchroniser les œuvres sélectionnées",
    "vector.create_empty": "Créer une collection vide",
    "vector.creating_collection": "Création de la collection…",
    "vector.selected_works_label": "{count} œuvres sélectionnées",
    "vector.collection_created_sync": "{name} créée; les œuvres sélectionnées sont en cours de synchronisation.",
    "vector.collection_created": "{name} créée",
    "vector.create_failed": "Impossible de créer la collection",
    "vector.empty_kicker": "Bases vectorielles",
    "vector.empty_title": "Créez votre première collection de corpus",
    "vector.empty_help": "Une collection vectorielle fournit à DerridAI une base de corpus persistante pour la recherche sémantique, la navigation des chercheurs et le RAG. Configurez-la, puis synchronisez éventuellement les œuvres déjà chargées.",
    "vector.create_first_collection": "Créer la première collection",
    "vector.summary": "Résumé des bases vectorielles",
    "vector.collections": "Collections",
    "vector.selected_collection": "Collection sélectionnée",
    "vector.collection_switch_help": "Choisissez une collection à gérer ou à parcourir.",
    "vector.collection": "Collection",
    "vector.unsynced_changes": "Modifications locales non synchronisées",
    "vector.unsynced_changes_count": "{count} modifications locales non synchronisées",
    "vector.unsynced_changes_what": "Que contient cette liste?",
    "vector.unsynced_changes_help": "Il s’agit des enregistrements de l’espace de travail modifiés depuis leur dernière synchronisation confirmée, ainsi que de ceux dont DerridAI a confirmé l’absence dans la collection sélectionnée. Retirer un élément ne masque que sa version actuelle; une modification ultérieure le remettra dans la file.",
    "vector.no_unsynced_changes": "Aucune modification locale non synchronisée confirmée.",
    "vector.no_unsynced_changes_help": "DerridAI n’a trouvé aucun enregistrement chargé modifié depuis sa dernière synchronisation ni confirmé absent de cette collection.",
    "vector.sync_selected": "Synchroniser la sélection",
    "vector.delete_collection": "Supprimer la collection",
    "vector.role_language_title": "Rôle et langue",
    "vector.role_language_help": "Le rôle et les étiquettes de langue décrivent l’utilisation prévue de cette base.",
    "vector.embedding_configuration": "Configuration des vecteurs",
    "vector.embedding_locked_help": "Les paramètres de vectorisation sont verrouillés après l’ajout d’enregistrements. Créez une nouvelle collection vide pour les modifier.",
    "vector.embedding_edit_help": "Choisissez comment DerridAI crée les vecteurs de cette collection.",
    "vector.model_not_used": "Ce fournisseur n’utilise pas de nom de modèle Ollama.",
    "vector.import_export": "Importer et exporter des enregistrements",
    "vector.import_export_help": "Synchronisez les enregistrements JSONL chargés vers cette collection, ou exportez les enregistrements de la collection vers un JSONL propre. L’export ne modifie pas la collection.",
    "vector.sync_into_collection": "Synchroniser vers la collection",
    "vector.sync_active_jsonl": "Synchroniser le JSONL actif",
    "vector.sync_all_loaded": "Synchroniser tous les JSONL chargés",
    "vector.load_jsonl_first": "Chargez et sélectionnez d’abord un onglet JSONL.",
    "vector.load_jsonl_any_first": "Chargez d’abord au moins un onglet JSONL.",
    "vector.sync_behavior_help": "La synchronisation met à jour les fiches correspondantes et insère les nouvelles. Toute synchronisation de plus de 500 fiches exige une confirmation, s’exécute au premier plan par lots de 500 et bloque les autres actions DerridAI jusqu’à sa fin ou son annulation.",
    "vector.export_from_collection": "Exporter depuis la collection",
    "vector.open_db_jsonl": "Ouvrir toute la collection dans un onglet JSONL",
    "vector.download_db_jsonl": "Télécharger le JSONL complet de la collection",
    "vector.open_current_work": "Ouvrir l’œuvre actuelle en JSONL",
    "vector.download_current_work": "Télécharger l’œuvre actuelle",
    "vector.page_export_title": "Page actuelle du tableau",
    "vector.page_export_help": "Ouvrez uniquement les enregistrements visibles sur cette page paginée dans un onglet JSONL temporaire. Il ne s’agit pas d’un export complet de la collection.",
    "vector.open_current_page": "Ouvrir la page actuelle du tableau en JSONL",
    "vector.semantic_search": "Recherche sémantique",
    "vector.semantic_search_help": "Trouvez des enregistrements par leur sens à l’aide du fournisseur de vectorisation configuré pour cette collection.",
    "vector.semantic_precomputed_help": "La recherche sémantique est indisponible car cette collection contient des vecteurs pré-calculés sans fonction de vectorisation des requêtes.",
    "vector.semantic_search_placeholder": "Rechercher cette collection par le sens…",
    "vector.search_results_empty": "Les résultats de recherche apparaîtront ici.",
    "vector.language_collections": "Collections linguistiques",
    "vector.language_derive_help": "Créez des collections anglaise et française séparées en acheminant les enregistrements selon les métadonnées document_language.",
    "vector.generate_language_collections": "Générer les collections EN / FR",
    "vector.advanced": "Avancé",
    "vector.select_collection": "Sélectionnez une collection",
    "vector.select_collection_help": "Choisissez une collection dans la liste pour gérer ses paramètres, synchroniser des enregistrements, effectuer des recherches ou parcourir son contenu.",
    "vector.storage_settings": "Paramètres de stockage",
    "vector.storage_help": "Chroma conserve sa base dans un répertoire côté serveur. Le chemin du conteneur est celui que DerridAI voit; le dossier hôte est le dossier mappé sur la machine qui exécute DerridAI, qui survit aux redémarrages du conteneur et peut être sauvegardé normalement.",
    "vector.container_path": "Chemin du conteneur",
    "vector.host_path": "Dossier hôte",
    "vector.change_storage_path": "Modifier le chemin de stockage",
    "vector.apply_storage_path": "Appliquer le chemin de stockage",
    "vector.change_storage_warning": "La modification de ce chemin fait basculer DerridAI vers un autre répertoire de persistance Chroma. Les collections existantes restent dans leur répertoire d’origine jusqu’à ce que vous y reveniez.",
    "vector.enter_storage_path": "Saisissez un chemin de stockage Chroma",
    "vector.checking_path": "Vérification…",
    "vector.storage_changed": "Stockage Chroma modifié vers {path}",
    "vector.storage_change_failed": "Impossible de modifier le stockage Chroma : {message}",
    "operations.large_sync_foreground_title": "La grande synchronisation s’exécute au premier plan",
    "operations.large_sync_foreground_help": "{count} enregistrements seront synchronisés par lots au premier plan afin que le navigateur reste réactif. Gardez cet onglet DerridAI ouvert jusqu’à la fin.",
    "operations.continue_sync": "Continuer la synchronisation",
    "record.inline_citation": "Citation abrégée",
    "record.full_citation": "Citation complète",
    "section.storage": "Stockage",
    "ui.clear_selection": "Effacer la sélection",
    "ui.delete": "Supprimer",
    "dynamic.page": "page",
    "research.all_records": "Tous les enregistrements",
    "research.no_work_metadata": "Aucune métadonnée d’œuvre n’a été trouvée dans cette collection.",
    "research.of": "sur",
    "ui.first_page": "Vous êtes déjà à la première page.",
    "ui.last_page": "Vous êtes déjà à la dernière page.",
    "ui.rows_per_page": "Lignes par page",
    "vector.browse_works": "Parcourir les œuvres",
    "vector.browse_works_help": "Ouvrez une œuvre pour ne parcourir que ses enregistrements dans cette collection.",
    "vector.open_work_records": "Ouvrir les enregistrements",
})

# 0.30.7 dashboard and vector-store cleanup strings.
DEFAULT_EN_US.update({
    "vector.workspace_actions": "Collection workspace",
    "vector.manage_collections": "Manage collections",
    "vector.manage_collections_help": "Create a new collection or refresh the collection list after changes made elsewhere.",
    "vector.storage_settings_help": "Review where Chroma data is stored. Most installations should leave these settings unchanged.",
    "vector.persistent_storage": "Persistent storage",
    "vector.host_path_help": "This is the persistent folder on the machine running DerridAI. Back up this folder to preserve collections.",
    "vector.container_path_help": "This is the corresponding path inside the DerridAI service. It is mainly useful for deployment troubleshooting.",
    "vector.change_storage_location": "Change data location",
    "vector.storage_change_caution": "Changing storage location does not move existing collections.",
    "vector.storage_change_caution_help": "DerridAI will begin using the new directory. Existing collections remain in the current directory until you switch back or move them outside the app.",
    "vector.new_container_path": "New container path",
    "vector.new_container_path_help": "Enter the server-side Chroma persistence directory. Only change this when you understand the deployment mapping.",
    "dashboard.top_total_words": "Top 5 Works by Total Words",
    "dashboard.top_works_records": "Top 5 Works by Number of Records",
    "dashboard.previous_chart": "Previous chart",
    "dashboard.next_chart": "Next chart",
    "dashboard.work_charts": "Work charts",
    "dashboard.last_viewed_record": "Last viewed record",
    "dashboard.random_record": "A record from the corpus",
    "dashboard.no_record_available": "No record is available to open.",
})
DEFAULT_FR_CA.update({
    "vector.workspace_actions": "Espace des collections",
    "vector.manage_collections": "Gérer les collections",
    "vector.manage_collections_help": "Créez une collection ou actualisez la liste après des modifications effectuées ailleurs.",
    "vector.storage_settings_help": "Consultez l’emplacement des données Chroma. La plupart des installations devraient conserver ces paramètres tels quels.",
    "vector.persistent_storage": "Stockage persistant",
    "vector.host_path_help": "Dossier persistant sur la machine qui exécute DerridAI. Sauvegardez ce dossier pour préserver les collections.",
    "vector.container_path_help": "Chemin correspondant à l’intérieur du service DerridAI. Il sert surtout au dépannage du déploiement.",
    "vector.change_storage_location": "Changer l’emplacement des données",
    "vector.storage_change_caution": "Changer l’emplacement de stockage ne déplace pas les collections existantes.",
    "vector.storage_change_caution_help": "DerridAI commencera à utiliser le nouveau répertoire. Les collections existantes restent dans le répertoire actuel jusqu’à ce que vous y reveniez ou les déplaciez hors de l’application.",
    "vector.new_container_path": "Nouveau chemin du conteneur",
    "vector.new_container_path_help": "Saisissez le répertoire de persistance Chroma côté serveur. Ne le modifiez que si vous comprenez la correspondance du déploiement.",
    "dashboard.top_total_words": "5 œuvres principales par nombre total de mots",
    "dashboard.top_works_records": "5 œuvres principales par nombre de fiches",
    "dashboard.previous_chart": "Graphique précédent",
    "dashboard.next_chart": "Graphique suivant",
    "dashboard.work_charts": "Graphiques des œuvres",
    "dashboard.last_viewed_record": "Dernière fiche consultée",
    "dashboard.random_record": "Une fiche du corpus",
    "dashboard.no_record_available": "Aucune fiche n’est disponible à ouvrir.",
})

# 0.30.8 dashboard, works, compare, researcher-provider, and annotation strings.
DEFAULT_EN_US.update({
    "operations.no_finished": "There are no finished operations to clear.",
    "operations.clear_finished": "Clear finished",
    "works.database_context": "Works synchronization database",
    "works.database_context_help": "Sync status and Sync actions on this page refer to the selected corpus database. Changing it does not change your loaded JSONL files.",
    "works.leave_metadata_title": "Open provider profiles?",
    "works.leave_metadata_help": "This will close the metadata workflow and navigate to LLM Providers. Your lookup has not started yet.",
    "works.open_providers": "Open providers",
    "compare.page_help": "Compare record metadata and text with focused, side-by-side field differences.",
    "compare.workspace_records": "Workspace records",
    "compare.paste_records": "Paste records",
    "compare.clear_pasted": "Clear pasted records",
    "annotations.shared": "Shared annotation",
    "annotations.remove_title": "Remove annotation?",
    "annotations.remove_help": "This removes the shared annotation. This action cannot be undone.",
    "annotations.annotate_selection": "Annotate selection",
    "annotations.note": "Note",
    "annotations.note_placeholder": "Add a note about this selection…",
    "annotations.tags": "Tags",
    "annotations.tags_placeholder": "Comma-separated tags",
    "annotations.save": "Save annotation",
    "annotations.saved": "Record annotation saved",
    "annotations.selected": "Selected",
    "annotations.selected_text": "Selected text",
    "annotations.add_note_tags": "Add note / tags",
    "users.provider_ready": "Provider ready",
    "users.provider_unavailable": "Provider unavailable",
    "users.remove_profile_confirm": "Remove this researcher LLM profile?",
    "users.no_researcher_profiles": "No researcher LLM profiles yet",
    "users.no_researcher_profiles_help": "Add an approved provider so researchers can run Research without seeing administrator credentials or unrestricted provider configuration.",
    "users.add_first_profile": "Add first profile",
    "users.profile_save_help": "Changes to existing cards are staged until you save them.",
    "users.add_researcher_provider": "Add researcher LLM provider",
    "users.add_researcher_provider_help": "Configure the endpoint, discover available models, then choose the model researchers may use.",
    "users.new_provider": "New provider",
    "users.profile_id": "Profile ID",
    "users.profile_id_help": "Stable identifier used by researcher jobs.",
    "users.profile_name": "Display name",
    "users.provider_type": "Provider type",
    "users.base_url": "Base URL",
    "users.base_url_help": "Endpoint researchers will use through this server-side profile.",
    "users.model": "Model",
    "users.model_placeholder": "Choose a discovered model or enter an ID",
    "users.discover_models": "Test / discover models",
    "users.models_discovered": "models discovered",
    "users.discover_models_help": "Test the provider to discover available models.",
    "users.max_concurrent": "Max concurrent requests",
    "users.max_concurrent_help": "Limits simultaneous researcher calls through this profile.",
    "users.api_key": "API key",
    "users.api_key_placeholder": "Leave blank to preserve stored key",
    "users.api_key_stored_help": "A key is already stored server-side. Blank preserves it.",
    "users.api_key_optional_help": "Optional unless your endpoint requires authentication.",
    "ui.show_api_key": "Show API key",
    "ui.hide_api_key": "Hide API key",
    "annotations.open_failed": "Could not open annotated record",
    "record.no_storage_id": "This database record has no storage ID.",
})
DEFAULT_FR_CA.update({
    "operations.no_finished": "Aucune opération terminée à effacer.",
    "operations.clear_finished": "Effacer les terminées",
    "works.database_context": "Base de synchronisation des œuvres",
    "works.database_context_help": "L’état de synchronisation et les actions Synchroniser de cette page concernent la base de corpus sélectionnée. La changer ne modifie pas vos fichiers JSONL chargés.",
    "works.leave_metadata_title": "Ouvrir les profils de fournisseurs?",
    "works.leave_metadata_help": "Cela fermera le flux de métadonnées et ouvrira les fournisseurs LLM. La recherche n’a pas encore commencé.",
    "works.open_providers": "Ouvrir les fournisseurs",
    "compare.page_help": "Comparez les métadonnées et le texte des fiches avec des différences ciblées côte à côte.",
    "compare.workspace_records": "Fiches de l’espace de travail",
    "compare.paste_records": "Coller des fiches",
    "compare.clear_pasted": "Effacer les fiches collées",
    "annotations.shared": "Annotation partagée",
    "annotations.remove_title": "Supprimer l’annotation?",
    "annotations.remove_help": "Cette action supprime l’annotation partagée et ne peut pas être annulée.",
    "annotations.annotate_selection": "Annoter la sélection",
    "annotations.note": "Note",
    "annotations.note_placeholder": "Ajoutez une note sur cette sélection…",
    "annotations.tags": "Étiquettes",
    "annotations.tags_placeholder": "Étiquettes séparées par des virgules",
    "annotations.save": "Enregistrer l’annotation",
    "annotations.saved": "Annotation de fiche enregistrée",
    "annotations.selected": "Sélectionné",
    "annotations.selected_text": "Texte sélectionné",
    "annotations.add_note_tags": "Ajouter une note / des étiquettes",
    "users.provider_ready": "Fournisseur prêt",
    "users.provider_unavailable": "Fournisseur indisponible",
    "users.remove_profile_confirm": "Supprimer ce profil LLM chercheur?",
    "users.no_researcher_profiles": "Aucun profil LLM chercheur",
    "users.no_researcher_profiles_help": "Ajoutez un fournisseur approuvé afin que les chercheurs puissent utiliser Recherche sans voir les identifiants administrateur ni une configuration de fournisseur sans restriction.",
    "users.add_first_profile": "Ajouter le premier profil",
    "users.profile_save_help": "Les modifications des cartes existantes sont préparées jusqu’à leur enregistrement.",
    "users.add_researcher_provider": "Ajouter un fournisseur LLM chercheur",
    "users.add_researcher_provider_help": "Configurez le point de terminaison, découvrez les modèles disponibles, puis choisissez le modèle que les chercheurs pourront utiliser.",
    "users.new_provider": "Nouveau fournisseur",
    "users.profile_id": "ID du profil",
    "users.profile_id_help": "Identifiant stable utilisé par les tâches chercheur.",
    "users.profile_name": "Nom d’affichage",
    "users.provider_type": "Type de fournisseur",
    "users.base_url": "URL de base",
    "users.base_url_help": "Point de terminaison utilisé par les chercheurs via ce profil côté serveur.",
    "users.model": "Modèle",
    "users.model_placeholder": "Choisir un modèle découvert ou saisir un ID",
    "users.discover_models": "Tester / découvrir les modèles",
    "users.models_discovered": "modèles découverts",
    "users.discover_models_help": "Testez le fournisseur pour découvrir les modèles disponibles.",
    "users.max_concurrent": "Requêtes simultanées maximales",
    "users.max_concurrent_help": "Limite les appels chercheur simultanés via ce profil.",
    "users.api_key": "Clé API",
    "users.api_key_placeholder": "Laisser vide pour conserver la clé stockée",
    "users.api_key_stored_help": "Une clé est déjà stockée côté serveur. Laisser vide la conserve.",
    "users.api_key_optional_help": "Facultatif sauf si votre point de terminaison exige une authentification.",
    "ui.show_api_key": "Afficher la clé API",
    "ui.hide_api_key": "Masquer la clé API",
    "annotations.open_failed": "Impossible d’ouvrir la fiche annotée",
    "record.no_storage_id": "Cette fiche de base de données n’a pas d’identifiant de stockage.",
})

# 0.35.0 — remaining compatibility/UI localization coverage.
DEFAULT_EN_US.update({'storage.settings': 'Storage settings', 'storage.review_chroma': 'Review where Chroma data is stored.', 'storage.persistent': 'Persistent storage', 'storage.host_folder': 'Host folder', 'storage.host_folder_help': 'Persistent folder on the machine running DerridAI.', 'storage.container_path': 'Container path', 'storage.container_path_help': 'Corresponding path inside the DerridAI service.', 'storage.change_location': 'Change data location', 'storage.new_container_path': 'New container path', 'storage.apply_path': 'Apply path', 'storage.review_paths': 'Review the persistent host folder and service path.', 'storage.advanced_deployment': 'Advanced deployment setting.', 'storage.change_location_short': 'Change location', 'ui.advanced': 'Advanced', 'vector.collection_creation_steps': 'Collection creation steps', 'research.selected_evidence_count_one': '{count} selected evidence', 'research.selected_evidence_count_many': '{count} selected evidence', 'research.database_count_one': '{count} database', 'research.database_count_many': '{count} databases', 'language.what_happens_next': 'What happens next', 'language.dictionary_key': 'Dictionary key', 'language.dictionary_value': 'Dictionary value', 'users.configured_account_one': '{count} configured account', 'users.configured_account_many': '{count} configured accounts', 'users.model_not_set': 'model not set', 'users.profile_id_placeholder': 'research-local', 'users.profile_name_placeholder': 'Local research model', 'legacy.filter_placeholder': 'Filter…', 'legacy.grades': 'Grades', 'legacy.open_in_faq': 'Open in FAQ', 'legacy.no_cached_responses': 'No cached responses yet.', 'legacy.no_cached_rag_search': 'No cached RAG responses match this search.', 'legacy.run_mode': 'Run mode', 'legacy.background_operation': 'Background operation', 'legacy.interactive_foreground': 'Interactive foreground', 'legacy.background_review': 'Background review', 'legacy.background_auto_improve': 'Background Auto-improve', 'legacy.model_selection_mode': 'Model selection mode', 'legacy.selection_mode': 'Selection mode', 'legacy.model_kind': 'Model kind', 'legacy.model_kind_filter': 'Model kind filter', 'legacy.auto_router': 'Auto router', 'legacy.discovered_model': 'Discovered model', 'legacy.choose_discovered_model': 'Choose discovered model', 'legacy.manual_model_id': 'Manual model ID', 'legacy.any': 'Any', 'legacy.general_chat': 'General/chat', 'legacy.reasoning': 'Reasoning', 'legacy.coding': 'Coding', 'legacy.fast_small': 'Fast/small', 'legacy.free_llm_openai_model_selection': 'FreeLLM / OpenAI model selection', 'legacy.kind_filter_help': "The kind filter narrows the endpoint's discovered model IDs by name. Auto router sends model auto; Manual accepts any compatible model ID.", 'legacy.reranker': 'Reranker', 'legacy.default_reranker': 'Default reranker', 'legacy.cross_encoder': 'Cross-encoder', 'legacy.lexical_vector_fallback': 'Lexical/vector fallback', 'legacy.lexical_vector': 'Lexical/vector', 'legacy.no_reranking': 'No reranking', 'legacy.none': 'None', 'legacy.search_record_id_work_file': 'Search record ID, work, or source file', 'legacy.type_record_work_author_file': 'Type record ID, work, author, or file…', 'legacy.expand_inspect_records': 'Expand to inspect or preview these records', 'legacy.only_changed_expanded': 'Only changed fields are expanded by default.', 'legacy.pipeline_timings': 'Pipeline timings', 'legacy.pipeline_timings_source': 'Adapted from the supplied DerridAI pipeline stages', 'legacy.no_record_selected': 'No record is selected.', 'legacy.clear': 'Clear', 'legacy.start_typing_records': 'Start typing to search loaded records.', 'legacy.preview_record': 'Preview record', 'legacy.differences': 'Differences', 'legacy.identical_compared_fields': 'These records are identical across all compared fields.', 'legacy.response_faq': 'Response FAQ', 'legacy.completed_rag_cached': 'Completed RAG runs will be cached automatically and appear here.', 'legacy.run_rag_query': 'Run a RAG query', 'legacy.search_cached_questions': 'Search cached questions', 'legacy.clear_search': 'Clear search', 'legacy.expand_all': 'Expand all', 'legacy.collapse_all': 'Collapse all', 'legacy.grade_every_response': 'Grade every response', 'legacy.new_rag_query': 'New RAG query', 'legacy.created': 'Created', 'legacy.question': 'Question', 'legacy.generation': 'Generation', 'legacy.evidence': 'Evidence'})
DEFAULT_FR_CA.update({'storage.settings': 'Paramètres de stockage', 'storage.review_chroma': 'Vérifiez l’emplacement où les données Chroma sont stockées.', 'storage.persistent': 'Stockage persistant', 'storage.host_folder': 'Dossier hôte', 'storage.host_folder_help': 'Dossier persistant sur l’ordinateur qui exécute DerridAI.', 'storage.container_path': 'Chemin dans le conteneur', 'storage.container_path_help': 'Chemin correspondant à l’intérieur du service DerridAI.', 'storage.change_location': 'Modifier l’emplacement des données', 'storage.new_container_path': 'Nouveau chemin dans le conteneur', 'storage.apply_path': 'Appliquer le chemin', 'storage.review_paths': 'Vérifiez le dossier persistant de l’hôte et le chemin du service.', 'storage.advanced_deployment': 'Paramètre de déploiement avancé.', 'storage.change_location_short': 'Modifier l’emplacement', 'ui.advanced': 'Avancé', 'vector.collection_creation_steps': 'Étapes de création de la collection', 'research.selected_evidence_count_one': '{count} preuve sélectionnée', 'research.selected_evidence_count_many': '{count} preuves sélectionnées', 'research.database_count_one': '{count} base de données', 'research.database_count_many': '{count} bases de données', 'language.what_happens_next': 'Ce qui se passe ensuite', 'language.dictionary_key': 'Clé du dictionnaire', 'language.dictionary_value': 'Valeur du dictionnaire', 'users.configured_account_one': '{count} compte configuré', 'users.configured_account_many': '{count} comptes configurés', 'users.model_not_set': 'modèle non défini', 'users.profile_id_placeholder': 'recherche-locale', 'users.profile_name_placeholder': 'Modèle de recherche local', 'legacy.filter_placeholder': 'Filtrer…', 'legacy.grades': 'Évaluations', 'legacy.open_in_faq': 'Ouvrir dans la FAQ', 'legacy.no_cached_responses': 'Aucune réponse mise en cache pour le moment.', 'legacy.no_cached_rag_search': 'Aucune réponse RAG mise en cache ne correspond à cette recherche.', 'legacy.run_mode': 'Mode d’exécution', 'legacy.background_operation': 'Tâche en arrière-plan', 'legacy.interactive_foreground': 'Exécution interactive au premier plan', 'legacy.background_review': 'Révision en arrière-plan', 'legacy.background_auto_improve': 'Amélioration automatique en arrière-plan', 'legacy.model_selection_mode': 'Mode de sélection du modèle', 'legacy.selection_mode': 'Mode de sélection', 'legacy.model_kind': 'Type de modèle', 'legacy.model_kind_filter': 'Filtre du type de modèle', 'legacy.auto_router': 'Routage automatique', 'legacy.discovered_model': 'Modèle détecté', 'legacy.choose_discovered_model': 'Choisir un modèle détecté', 'legacy.manual_model_id': 'ID de modèle saisi manuellement', 'legacy.any': 'Tous', 'legacy.general_chat': 'Général/conversation', 'legacy.reasoning': 'Raisonnement', 'legacy.coding': 'Programmation', 'legacy.fast_small': 'Rapide/léger', 'legacy.free_llm_openai_model_selection': 'Sélection de modèle FreeLLM / OpenAI', 'legacy.kind_filter_help': 'Le filtre de type restreint les ID de modèles détectés par le point de terminaison selon leur nom. Le routage automatique envoie le modèle auto; le mode manuel accepte tout ID de modèle compatible.', 'legacy.reranker': 'Reclassement', 'legacy.default_reranker': 'Reclassement par défaut', 'legacy.cross_encoder': 'Encodeur croisé', 'legacy.lexical_vector_fallback': 'Solution de rechange lexicale/vectorielle', 'legacy.lexical_vector': 'Lexical/vectoriel', 'legacy.no_reranking': 'Aucun reclassement', 'legacy.none': 'Aucun', 'legacy.search_record_id_work_file': 'Rechercher l’ID de fiche, l’œuvre ou le fichier source', 'legacy.type_record_work_author_file': 'Saisissez un ID de fiche, une œuvre, un auteur ou un fichier…', 'legacy.expand_inspect_records': 'Développez pour examiner ou prévisualiser ces fiches', 'legacy.only_changed_expanded': 'Seuls les champs modifiés sont développés par défaut.', 'legacy.pipeline_timings': 'Durées des étapes du pipeline', 'legacy.pipeline_timings_source': 'Adapté des étapes du pipeline DerridAI fournies', 'legacy.no_record_selected': 'Aucune fiche n’est sélectionnée.', 'legacy.clear': 'Effacer', 'legacy.start_typing_records': 'Commencez à saisir du texte pour rechercher les fiches chargées.', 'legacy.preview_record': 'Prévisualiser la fiche', 'legacy.differences': 'Différences', 'legacy.identical_compared_fields': 'Ces fiches sont identiques pour tous les champs comparés.', 'legacy.response_faq': 'FAQ des réponses', 'legacy.completed_rag_cached': 'Les exécutions RAG terminées seront automatiquement mises en cache et apparaîtront ici.', 'legacy.run_rag_query': 'Lancer une requête RAG', 'legacy.search_cached_questions': 'Rechercher dans les questions mises en cache', 'legacy.clear_search': 'Effacer la recherche', 'legacy.expand_all': 'Tout développer', 'legacy.collapse_all': 'Tout réduire', 'legacy.grade_every_response': 'Évaluer chaque réponse', 'legacy.new_rag_query': 'Nouvelle requête RAG', 'legacy.created': 'Création', 'legacy.question': 'Question', 'legacy.generation': 'Génération', 'legacy.evidence': 'Preuves'})

# 0.35.0 — legacy compatibility text fragments not representable as leaf controls.
DEFAULT_EN_US.update({'legacy.go': 'Go', 'legacy.load': 'Load', 'legacy.auto': 'Auto', 'legacy.when': 'When', 'legacy.think': 'Think', 'legacy.warmup': 'Warmup', 'legacy.default': 'default', 'legacy.random': 'random', 'legacy.verify': 'verify', 'legacy.changed': 'changed', 'legacy.untagged': 'untagged', 'legacy.model_default': 'model default', 'legacy.decision_state': 'decision state', 'legacy.linked_pdf': 'the linked PDF', 'legacy.clear_history': 'Clear history', 'legacy.clear_all_histories': 'Clear all histories', 'legacy.llm_review': 'LLM review', 'legacy.llm_operation': 'LLM operation', 'legacy.unknown_error': 'unknown error', 'legacy.no_changes_proposed': 'No changes proposed', 'legacy.running_rag_pipeline': 'Running RAG pipeline', 'legacy.no_pending_changes': 'No pending changes yet', 'legacy.mixed_leave_unchanged': 'Mixed / leave unchanged', 'legacy.not_warmed': 'Not warmed this session', 'legacy.cross_file_work_overview': 'Cross-file work overview', 'legacy.review_available_results': 'Review available results', 'legacy.load_jsonl_first': 'Load JSONL records first.', 'legacy.type_choose_model': 'Type or choose a model ID', 'legacy.type_choose_installed_model': 'Type or choose an installed model', 'legacy.column_already_last': 'This column is already last.', 'legacy.column_already_first': 'This column is already first.', 'legacy.already_last_page': 'You are already on the last page.', 'legacy.already_first_page': 'You are already on the first page.', 'legacy.no_next_newer': 'There is no next item or newer version.', 'legacy.no_earlier_location': 'There is no earlier navigation location.', 'legacy.no_forward_location': 'There is no forward navigation location.', 'legacy.no_updates_history': 'This record has no updates history', 'legacy.no_loaded_updates_history': 'No loaded records have updates history', 'legacy.clear_all_updates_confirm': 'Clear all update histories?', 'legacy.clear_record_updates_confirm': 'Clear record update history?', 'legacy.choose_previous_rag': 'Choose a previous RAG question first.', 'legacy.select_record_first': 'Select a record first.', 'legacy.select_change_first': 'Select at least one proposed change first.', 'legacy.every_field_shown': 'Every available field is already shown.', 'legacy.no_current_pdf_persist': 'Could not persist current PDF asset', 'legacy.no_current_pdf_restore': 'Could not restore current PDF asset', 'legacy.no_workspace_restore': 'Could not restore IndexedDB workspace', 'legacy.no_workspace_prefs': 'IndexedDB preference persistence failed', 'legacy.open_jsonl': 'Open a JSONL file', 'legacy.inspect_differences': 'Inspect field and text differences', 'legacy.provider_overview_help': 'Create and configure reusable providers once; select them wherever DerridAI uses an LLM.', 'legacy.provider_concurrency_help': 'Concurrency is profile-specific. Ollama normally starts at 1 concurrent request; FreeLLM/OpenAI-compatible profiles default to 32 and can be adjusted from 1–64.', 'legacy.provider_profiles_help': 'Reusable endpoint + model + generation settings for every LLM workflow. OpenAI-compatible profiles query GET /models when the endpoint supports it. Ollama profiles sharing an endpoint share one execution gate and use that endpoint’s lowest configured concurrency cap.', 'legacy.merge_tabs_help': 'Unselected tabs remain unchanged. Selected tabs are removed from the workspace after the merge is created; their underlying source files on disk are not deleted.', 'legacy.backup_restore_help': 'Create one portable compressed archive containing the browser workspace, loaded JSONL records, audit history, provider/RAG configuration, current PDF, and every Chroma collection with its stored vectors.', 'legacy.remove_work_help': 'Remove every record for this work from selected loaded JSONL files and, optionally, from the selected Chroma collection. Primary collection deletion also removes matching records from its language collections.', 'legacy.self_grade_help': 'This grade used the same model as answer generation; interpret it as self-evaluation rather than an independent grade.', 'legacy.same_model_grade_help': 'This provider/model was also used to generate the RAG answer. Self-grading can be systematically biased; use a different model for a more independent evaluation.', 'legacy.filter_logic_help_prefix': 'Groups are evaluated first. At the top level, AND binds before OR. This supports expressions like', 'legacy.vector_defaults_prefix': 'New collections default to Ollama embeddings with', 'legacy.vector_defaults_suffix': '. Chroma language collections use coarse', 'legacy.kind_filter_prefix': "The kind filter narrows the endpoint's discovered model IDs by name. Auto router sends model", 'legacy.kind_filter_suffix': '; Manual accepts any compatible model ID.', 'legacy.selected_changes_note': 'selected · accepted changes are removed from this pending queue immediately', 'legacy.work_metadata_help_prefix': 'only for fields that should be changed across every associated record. Changing', 'legacy.work_metadata_help_suffix': "renames the work for all loaded records. Every modified field is written to each record's", 'legacy.history_suffix': 'history.', 'legacy.cached_faq_suffix': '. It is available from Response FAQ.', 'legacy.rag_language_exists_suffix': 'exists, RAG uses the matching language collection. Missing requested languages fall back to the source collection and are filtered by'})
DEFAULT_FR_CA.update({'legacy.go': 'Aller', 'legacy.load': 'Charger', 'legacy.auto': 'Automatique', 'legacy.when': 'Lorsque', 'legacy.think': 'Réflexion', 'legacy.warmup': 'Préchauffage', 'legacy.default': 'par défaut', 'legacy.random': 'aléatoire', 'legacy.verify': 'vérifier', 'legacy.changed': 'modifié', 'legacy.untagged': 'sans étiquette', 'legacy.model_default': 'valeur par défaut du modèle', 'legacy.decision_state': 'état de décision', 'legacy.linked_pdf': 'le PDF lié', 'legacy.clear_history': 'Effacer l’historique', 'legacy.clear_all_histories': 'Effacer tous les historiques', 'legacy.llm_review': 'Révision par LLM', 'legacy.llm_operation': 'Tâche LLM', 'legacy.unknown_error': 'erreur inconnue', 'legacy.no_changes_proposed': 'Aucune modification proposée', 'legacy.running_rag_pipeline': 'Pipeline RAG en cours', 'legacy.no_pending_changes': 'Aucune modification en attente', 'legacy.mixed_leave_unchanged': 'Valeurs mixtes / laisser inchangé', 'legacy.not_warmed': 'Pas encore préchauffé dans cette session', 'legacy.cross_file_work_overview': 'Vue d’ensemble de l’œuvre dans plusieurs fichiers', 'legacy.review_available_results': 'Réviser les résultats disponibles', 'legacy.load_jsonl_first': 'Chargez d’abord des fiches JSONL.', 'legacy.type_choose_model': 'Saisissez ou choisissez un ID de modèle', 'legacy.type_choose_installed_model': 'Saisissez ou choisissez un modèle installé', 'legacy.column_already_last': 'Cette colonne est déjà la dernière.', 'legacy.column_already_first': 'Cette colonne est déjà la première.', 'legacy.already_last_page': 'Vous êtes déjà à la dernière page.', 'legacy.already_first_page': 'Vous êtes déjà à la première page.', 'legacy.no_next_newer': 'Il n’y a aucun élément suivant ni aucune version plus récente.', 'legacy.no_earlier_location': 'Il n’y a aucun emplacement précédent dans l’historique de navigation.', 'legacy.no_forward_location': 'Il n’y a aucun emplacement suivant dans l’historique de navigation.', 'legacy.no_updates_history': 'Cette fiche n’a aucun historique de modifications', 'legacy.no_loaded_updates_history': 'Aucune fiche chargée n’a d’historique de modifications', 'legacy.clear_all_updates_confirm': 'Effacer tous les historiques de modifications?', 'legacy.clear_record_updates_confirm': 'Effacer l’historique des modifications de la fiche?', 'legacy.choose_previous_rag': 'Choisissez d’abord une question RAG précédente.', 'legacy.select_record_first': 'Sélectionnez d’abord une fiche.', 'legacy.select_change_first': 'Sélectionnez d’abord au moins une modification proposée.', 'legacy.every_field_shown': 'Tous les champs disponibles sont déjà affichés.', 'legacy.no_current_pdf_persist': 'Impossible d’enregistrer le PDF actuel dans le stockage persistant', 'legacy.no_current_pdf_restore': 'Impossible de restaurer le PDF actuel', 'legacy.no_workspace_restore': 'Impossible de restaurer l’espace de travail IndexedDB', 'legacy.no_workspace_prefs': 'Impossible d’enregistrer les préférences IndexedDB', 'legacy.open_jsonl': 'Ouvrir un fichier JSONL', 'legacy.inspect_differences': 'Examiner les différences de champs et de texte', 'legacy.provider_overview_help': 'Créez et configurez les fournisseurs réutilisables une seule fois, puis sélectionnez-les partout où DerridAI utilise un LLM.', 'legacy.provider_concurrency_help': 'La simultanéité est propre à chaque profil. Ollama démarre normalement à 1 requête simultanée; les profils FreeLLM ou compatibles avec OpenAI utilisent 32 par défaut et peuvent être réglés de 1 à 64.', 'legacy.provider_profiles_help': 'Points de terminaison, modèle et paramètres de génération réutilisables pour tous les flux de travail LLM. Les profils compatibles avec OpenAI interrogent GET /models lorsque le point de terminaison le permet. Les profils Ollama qui partagent un point de terminaison utilisent une même limite d’exécution et la plus faible limite de simultanéité configurée pour ce point de terminaison.', 'legacy.merge_tabs_help': 'Les onglets non sélectionnés demeurent inchangés. Les onglets sources sélectionnés sont retirés de l’espace de travail après la création de la fusion; leurs fichiers sources sur disque ne sont pas supprimés.', 'legacy.backup_restore_help': 'Créez une archive compressée portable qui contient l’espace de travail du navigateur, les fiches JSONL chargées, l’historique d’audit, la configuration des fournisseurs et du RAG, le PDF actuel ainsi que chaque collection Chroma et ses vecteurs stockés.', 'legacy.remove_work_help': 'Retirez toutes les fiches de cette œuvre des fichiers JSONL chargés sélectionnés et, au besoin, de la collection Chroma choisie. La suppression dans une collection principale retire également les fiches correspondantes de ses collections linguistiques.', 'legacy.self_grade_help': 'Cette évaluation a utilisé le même modèle que celui qui a généré la réponse; interprétez-la comme une autoévaluation plutôt que comme une évaluation indépendante.', 'legacy.same_model_grade_help': 'Ce fournisseur et ce modèle ont aussi servi à générer la réponse RAG. L’autoévaluation peut être systématiquement biaisée; utilisez un autre modèle pour obtenir une évaluation plus indépendante.', 'legacy.filter_logic_help_prefix': 'Les groupes sont évalués en premier. Au niveau supérieur, ET est prioritaire sur OU. Cela permet des expressions comme', 'legacy.vector_defaults_prefix': 'Les nouvelles collections utilisent par défaut les plongements vectoriels Ollama avec', 'legacy.vector_defaults_suffix': '. Les collections linguistiques Chroma utilisent les étiquettes générales', 'legacy.kind_filter_prefix': 'Le filtre de type restreint selon leur nom les ID de modèles détectés par le point de terminaison. Le routage automatique envoie le modèle', 'legacy.kind_filter_suffix': '; le mode manuel accepte tout ID de modèle compatible.', 'legacy.selected_changes_note': 'sélectionnées · les modifications acceptées sont immédiatement retirées de cette file d’attente', 'legacy.work_metadata_help_prefix': 'uniquement pour les champs qui doivent être modifiés dans toutes les fiches associées. La modification de', 'legacy.work_metadata_help_suffix': 'renomme l’œuvre dans toutes les fiches chargées. Chaque champ modifié est consigné dans l’', 'legacy.history_suffix': 'historique.', 'legacy.cached_faq_suffix': '. Elle est accessible dans la FAQ des réponses.', 'legacy.rag_language_exists_suffix': 'existe, le RAG utilise la collection linguistique correspondante. Les langues demandées qui n’existent pas utilisent la collection source avec un filtre sur'})

# 0.35.0 — dynamic legacy UI localization patterns.
DEFAULT_EN_US.update({'dynamic.record_one': 'record', 'dynamic.work_one': 'work', 'dynamic.model_one': 'model', 'dynamic.models': 'models', 'dynamic.profile_one': 'profile', 'dynamic.profiles': 'profiles', 'dynamic.word_one': 'word', 'dynamic.words': 'words', 'dynamic.character_one': 'character', 'dynamic.characters': 'characters', 'dynamic.change_one': 'change', 'dynamic.changes': 'changes', 'dynamic.annotation_one': 'annotation', 'dynamic.annotations': 'annotations', 'dynamic.cached_response_one': 'cached response', 'dynamic.cached_responses': 'cached responses', 'dynamic.selected_count': '{count} selected', 'dynamic.record_range_count': '{shown} of {total} records', 'dynamic.page_of_pages': 'Page {page} / {pages}', 'dynamic.ready_models': 'Ready · {count} models', 'dynamic.history_latest': "Showing latest {shown} of {total} changes. Full history is preserved in the record's updates field.", 'dynamic.cleared_history_records': 'Cleared updates history from {count} records', 'dynamic.restored_fields': 'Restored original record state · {count} fields changed', 'dynamic.loaded_records': 'Loaded {count} records', 'dynamic.loaded_records_issues': 'Loaded {count} records · {issues} parse issues', 'dynamic.merged_tabs_records': 'Merged and replaced {tabs} tabs · {records} records', 'dynamic.cleaned_records': '{records} records cleaned · {changes} tracked changes', 'dynamic.exported_records': 'Exported {count} records from {collection}'})
DEFAULT_FR_CA.update({'dynamic.record_one': 'fiche', 'dynamic.work_one': 'œuvre', 'dynamic.model_one': 'modèle', 'dynamic.models': 'modèles', 'dynamic.profile_one': 'profil', 'dynamic.profiles': 'profils', 'dynamic.word_one': 'mot', 'dynamic.words': 'mots', 'dynamic.character_one': 'caractère', 'dynamic.characters': 'caractères', 'dynamic.change_one': 'modification', 'dynamic.changes': 'modifications', 'dynamic.annotation_one': 'annotation', 'dynamic.annotations': 'annotations', 'dynamic.cached_response_one': 'réponse mise en cache', 'dynamic.cached_responses': 'réponses mises en cache', 'dynamic.selected_count': '{count} éléments sélectionnés', 'dynamic.record_range_count': '{shown} sur {total} fiches', 'dynamic.page_of_pages': 'Page {page} / {pages}', 'dynamic.ready_models': 'Prêt · {count} modèles', 'dynamic.history_latest': 'Affichage des {shown} plus récentes parmi {total} modifications. L’historique complet est conservé dans le champ updates de la fiche.', 'dynamic.cleared_history_records': 'Historique des modifications effacé pour {count} fiches', 'dynamic.restored_fields': 'État original de la fiche restauré · {count} champs modifiés', 'dynamic.loaded_records': '{count} fiches chargées', 'dynamic.loaded_records_issues': '{count} fiches chargées · {issues} problèmes d’analyse', 'dynamic.merged_tabs_records': '{tabs} onglets fusionnés et remplacés · {records} fiches', 'dynamic.cleaned_records': '{records} fiches nettoyées · {changes} modifications consignées', 'dynamic.exported_records': '{count} fiches exportées depuis {collection}'})


class SystemStore:
    def __init__(self) -> None:
        # 0.36.0: system metadata is durable SQLite state behind a repository
        # boundary. Keep the former JSON path only as a one-time migration source.
        self.repository = system_repository
        self.path = self.repository.path
        self.legacy_path = self.path.with_name("derridai-system.json")
        self._lock = threading.RLock()
        # Prior releases placed derridai-system.json beside AUTH_DB_PATH. Honor
        # that location as well as the new SYSTEM_DB_PATH directory so custom
        # deployments migrate without requiring users to move files manually.
        legacy_candidates = [
            self.legacy_path,
            Path(getattr(settings, "auth_db_path", "/data/.home/derridai-auth.sqlite3")).expanduser().parent / "derridai-system.json",
        ]
        seen: set[Path] = set()
        for candidate in legacy_candidates:
            candidate = candidate.resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            if self.repository.migrate_legacy_json(candidate):
                break
        self._ensure()

    def _default(self) -> dict[str, Any]:
        return {
            "researcher_provider_profiles": [],
            "annotations": [],
            "language_dictionary_revision": "0.36.0.1",
            "languages": {
                "en-US": {"name": "English", "flag": "🇺🇸", "dictionary": DEFAULT_EN_US},
                "fr-CA": {"name": "Français", "flag": "🇨🇦", "dictionary": DEFAULT_FR_CA},
            },
        }

    def _ensure(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._write(self._default())
                return
            data = self._read()
            changed = False
            data.setdefault("researcher_provider_profiles", [])
            data.setdefault("annotations", [])
            languages = data.setdefault("languages", {})
            dictionary_revision = "0.36.0.1"
            refresh_builtins = str(data.get("language_dictionary_revision") or "") != dictionary_revision
            for code, value in self._default()["languages"].items():
                if code not in languages:
                    languages[code] = copy.deepcopy(value)
                    changed = True
                else:
                    if "name" not in languages[code]:
                        languages[code]["name"] = value["name"]
                        changed = True
                    if "flag" not in languages[code]:
                        languages[code]["flag"] = value["flag"]
                        changed = True
                    if code == "en-US" and (languages[code].get("name") != "English" or languages[code].get("flag") != "🇺🇸"):
                        languages[code]["name"] = "English"
                        languages[code]["flag"] = "🇺🇸"
                        changed = True
                    if code == "fr-CA" and (languages[code].get("name") != "Français" or languages[code].get("flag") != "🇨🇦"):
                        languages[code]["name"] = "Français"
                        languages[code]["flag"] = "🇨🇦"
                        changed = True
                    # A built-in dictionary revision is a one-time migration. It
                    # replaces canonical en-US/fr-CA values on upgrade so an
                    # existing installation receives the professional Québec
                    # localization shipped with this release. Once the revision
                    # is current, administrators may edit built-in strings and
                    # those edits are preserved across ordinary restarts.
                    if refresh_builtins:
                        languages[code]["dictionary"] = copy.deepcopy(value["dictionary"])
                        changed = True
                    else:
                        dictionary = languages[code].setdefault("dictionary", {})
                        for key, text in value["dictionary"].items():
                            if key not in dictionary:
                                dictionary[key] = text
                                changed = True
            if refresh_builtins:
                data["language_dictionary_revision"] = dictionary_revision
                changed = True
            # Custom locale dictionaries also inherit newly introduced canonical
            # keys as English fallbacks. This keeps every installed language
            # editable after an application upgrade instead of silently omitting
            # controls added in a newer release; admins can translate the new keys
            # in-place or reinstall/regenerate the locale.
            canonical = languages.get("en-US", {}).get("dictionary", DEFAULT_EN_US)
            for code, language in languages.items():
                if code in {"en-US", "fr-CA"} or not isinstance(language, dict):
                    continue
                dictionary = language.setdefault("dictionary", {})
                for key, text in canonical.items():
                    if key not in dictionary:
                        dictionary[key] = text
                        changed = True
            if changed:
                self._write(data)

    def _read(self) -> dict[str, Any]:
        try:
            return self.repository.load()
        except Exception:
            # Preserve the previous startup behavior: a damaged/temporarily
            # unavailable store does not make localization defaults disappear.
            return self._default()

    def _write(self, data: dict[str, Any]) -> None:
        self.repository.replace(data)

    def storage_info(self) -> dict[str, Any]:
        return self.repository.describe()

    @staticmethod
    def _public_profile(profile: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "id", "name", "type", "base_url", "model", "model_mode", "model_kind",
            "max_concurrent_requests", "num_ctx", "num_predict", "metadata_num_predict",
            "think", "temperature", "top_k", "top_p", "min_p", "repeat_penalty", "seed",
            "mirostat", "mirostat_eta", "mirostat_tau", "keep_alive", "extra_options",
        }
        public = {key: copy.deepcopy(value) for key, value in profile.items() if key in allowed}
        public["has_api_key"] = bool(profile.get("api_key"))
        return public

    def list_annotations(self, *, user_id: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = copy.deepcopy(self.repository.list_annotations())
        if user_id is not None:
            rows = [row for row in rows if int(row.get("user_id") or 0) == int(user_id)]
        return rows

    def add_annotation(self, value: dict[str, Any]) -> dict[str, Any]:
        import uuid
        from datetime import datetime, timezone
        item = copy.deepcopy(value if isinstance(value, dict) else {})
        item["id"] = str(item.get("id") or uuid.uuid4())
        item["created_at"] = str(item.get("created_at") or datetime.now(timezone.utc).isoformat())
        item["tags"] = [str(tag).strip() for tag in item.get("tags") or [] if str(tag).strip()]
        with self._lock:
            self.repository.put_annotation(item)
        return item

    def delete_annotation(self, annotation_id: str, *, user_id: int | None = None, admin: bool = False) -> bool:
        annotation_id = str(annotation_id or "").strip()
        with self._lock:
            return self.repository.delete_annotation(annotation_id, user_id=user_id, admin=admin)

    def researcher_profiles(self, *, include_secrets: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            profiles = copy.deepcopy(self.repository.list_provider_profiles())
        if include_secrets:
            return profiles
        return [self._public_profile(profile) for profile in profiles]

    def set_researcher_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Provider secrets are intentionally write-only in the admin UI. Preserve an
        # existing API key when an edited profile is submitted without a replacement.
        existing = {
            str(profile.get("id")): profile
            for profile in self.researcher_profiles(include_secrets=True)
            if profile.get("id")
        }
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in profiles:
            if not isinstance(raw, dict):
                continue
            profile = copy.deepcopy(raw)
            profile_id = str(profile.get("id") or "").strip()
            if not profile_id or profile_id in seen:
                continue
            if profile.get("type") not in {"ollama", "openai"}:
                continue
            profile["id"] = profile_id
            if not str(profile.get("api_key") or "").strip() and profile_id in existing:
                prior_secret = existing[profile_id].get("api_key")
                if prior_secret:
                    profile["api_key"] = prior_secret
            profile["max_concurrent_requests"] = max(1, min(64, int(profile.get("max_concurrent_requests") or (1 if profile["type"] == "ollama" else 32))))
            normalized.append(profile)
            seen.add(profile_id)
        endpoint_limits: dict[str, int] = {}
        for profile in normalized:
            if profile.get("type") != "ollama":
                continue
            endpoint = str(profile.get("base_url") or "").rstrip("/").lower()
            limit = int(profile.get("max_concurrent_requests") or 1)
            endpoint_limits[endpoint] = min(endpoint_limits.get(endpoint, limit), limit)
        for profile in normalized:
            if profile.get("type") == "ollama":
                endpoint = str(profile.get("base_url") or "").rstrip("/").lower()
                profile["max_concurrent_requests"] = endpoint_limits.get(endpoint, profile["max_concurrent_requests"])
        with self._lock:
            self.repository.replace_provider_profiles(normalized)
        return [self._public_profile(profile) for profile in normalized]

    def researcher_profile(self, profile_id: str) -> dict[str, Any] | None:
        for profile in self.researcher_profiles(include_secrets=True):
            if str(profile.get("id")) == str(profile_id):
                return profile
        return None

    def list_languages(self) -> list[dict[str, str]]:
        with self._lock:
            languages = copy.deepcopy(self.repository.list_languages())
        return [
            {"code": code, "name": str(value.get("name") or code), "flag": str(value.get("flag") or "🌐")}
            for code, value in sorted(languages.items())
        ]

    def get_language(self, code: str) -> dict[str, Any] | None:
        try:
            code = normalize_locale_code(code)
        except ValueError:
            return None
        with self._lock:
            value = copy.deepcopy(self.repository.get_language(code))
        if not value:
            return None
        return {"code": code, **value}

    def put_language(
        self,
        code: str,
        *,
        name: str,
        flag: str,
        dictionary: dict[str, str],
        translation_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        code = normalize_locale_code(code)
        clean = {str(key): str(value) for key, value in dictionary.items() if str(key).strip()}
        with self._lock:
            languages = self.repository.list_languages()
            previous = languages.get(code) if isinstance(languages.get(code), dict) else {}
            report = copy.deepcopy(translation_report if translation_report is not None else previous.get("translation_report"))
            # Keep the durable report useful after an administrator manually fixes
            # fallback strings. A tracked key is resolved once its target no longer
            # equals the canonical English value.
            if isinstance(report, dict) and code != "en-US":
                canonical = (languages.get("en-US") or {}).get("dictionary") or DEFAULT_EN_US
                tracked = [str(key) for key in (report.get("failed_keys") or []) if str(key)]
                unresolved = [key for key in tracked if clean.get(key, "").strip() == str(canonical.get(key, "")).strip()]
                report["failed_keys"] = unresolved
                report["failed_count"] = len(unresolved)
                report["fallback_count"] = len(unresolved)
                if isinstance(report.get("failures"), list):
                    report["failures"] = [item for item in report["failures"] if isinstance(item, dict) and str(item.get("key") or "") in unresolved]
                if not unresolved and report.get("status") == "completed_with_fallbacks":
                    report["status"] = "complete"
            language_value: dict[str, Any] = {"name": name.strip() or code, "flag": flag.strip() or "🌐", "dictionary": clean}
            if isinstance(report, dict):
                language_value["translation_report"] = report
            self.repository.put_language(code, language_value)
            # en-US is the canonical key set. When an administrator introduces a
            # new English key, make it immediately editable in every installed
            # locale as an English fallback instead of waiting for a restart.
            if code == "en-US":
                for locale_code, language in languages.items():
                    if locale_code == "en-US" or not isinstance(language, dict):
                        continue
                    target = language.setdefault("dictionary", {})
                    changed = False
                    for key, value in clean.items():
                        if key not in target:
                            target[key] = value
                            changed = True
                    if changed:
                        self.repository.put_language(locale_code, language)
        return self.get_language(code) or {}

    def delete_language(self, code: str) -> None:
        code = normalize_locale_code(code)
        if code in {"en-US", "fr-CA"}:
            raise ValueError("Built-in languages cannot be removed.")
        with self._lock:
            if not self.repository.delete_language(code):
                raise KeyError(code)

    def snapshot(self) -> dict[str, Any]:
        """Return the complete server-owned configuration for full backups.

        Unlike the public profile API this intentionally includes provider
        secrets, because a full DerridAI backup is already documented as a
        credential-bearing administrative artifact.
        """
        with self._lock:
            return copy.deepcopy(self._read())

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        """Restore server-owned configuration and merge required built-ins.

        Older backups may not contain every current dictionary key.  `_ensure`
        fills those gaps after the snapshot is written without disturbing
        administrator customizations.
        """
        if not isinstance(payload, dict):
            raise ValueError("System configuration backup is invalid.")
        profiles = payload.get("researcher_provider_profiles", [])
        languages = payload.get("languages", {})
        if not isinstance(profiles, list) or not isinstance(languages, dict):
            raise ValueError("System configuration backup is invalid.")
        with self._lock:
            self._write(copy.deepcopy(payload))
            self._ensure()


# 0.30.9 works, compare, record annotation, research, and permission-model strings.
DEFAULT_EN_US.update({
    "works.applying_metadata": "Applying metadata…",
    "works.view_annotations": "Annotations ({count})",
    "annotations.none_record": "No annotations on this record yet",
    "annotations.none_record_help": "Select text or a displayed value above to attach a note or tags.",
    "annotations.record_notes": "Annotations",
    "annotations.record_annotations": "Record annotations",
    "annotations.record_annotations_help": "Notes and tags attached to specific evidence in this record.",
    "compare.paste_guidance_title": "Paste one record on each side",
    "compare.paste_guidance_help": "JSON objects and one-line JSONL records are supported. DerridAI compares parsed fields after both sides are valid.",
    "compare.researcher_source_help": "Records are drawn from the selected corpus database and use the same Compare workspace as administrator accounts. Editing controls appear only where your role permits them.",
    "research.workspace_title": "Evidence-grounded research workspace",
    "research.workspace_help": "Build a question, choose retrieval and generation settings, pin evidence, then run the full provenance-aware pipeline.",
    "research.pipeline_title": "Research pipeline",
    "research.pipeline_help": "Configure the corpus, retrieval, evidence, and generation stages. Advanced controls stay available without competing with the primary question workflow.",
})
DEFAULT_FR_CA.update({
    "works.applying_metadata": "Application des métadonnées…",
    "works.view_annotations": "Annotations ({count})",
    "annotations.none_record": "Aucune annotation pour cette fiche",
    "annotations.none_record_help": "Sélectionnez du texte ou une valeur affichée ci-dessus pour y joindre une note ou des étiquettes.",
    "annotations.record_notes": "Annotations",
    "annotations.record_annotations": "Annotations de la fiche",
    "annotations.record_annotations_help": "Notes et étiquettes rattachées à des éléments précis de cette fiche.",
    "compare.paste_guidance_title": "Collez une fiche de chaque côté",
    "compare.paste_guidance_help": "Les objets JSON et les fiches JSONL sur une seule ligne sont pris en charge. DerridAI compare les champs analysés lorsque les deux côtés sont valides.",
    "compare.researcher_source_help": "Les fiches proviennent de la base de corpus sélectionnée et utilisent le même espace Comparer que les comptes administrateur. Les commandes de modification n’apparaissent que lorsque votre rôle les autorise.",
    "research.workspace_title": "Espace de recherche fondé sur les preuves",
    "research.workspace_help": "Formulez une question, choisissez la récupération et la génération, épinglez des preuves, puis exécutez le pipeline complet avec provenance.",
    "research.pipeline_title": "Pipeline de recherche",
    "research.pipeline_help": "Configurez le corpus, la récupération, les preuves et la génération. Les options avancées restent disponibles sans concurrencer le flux principal de la question.",
})


# 0.30.10 search layouts, blocking upserts, storage, and researcher-provider strings.
DEFAULT_EN_US.update({
    "research.result_layout": "Result layout",
    "research.layout_compact": "Compact table",
    "research.layout_roomy": "Comfortable table",
    "research.layout_cards": "Cards",
    "research.contains": "contains",
    "operations.blocking_sync_help": "This large upsert runs in foreground batches of 500. Other DerridAI actions are paused until it finishes or you cancel.",
    "operations.preparing_sync": "Preparing records…",
    "operations.keep_tab_open": "Keep this DerridAI tab open while the sync is running.",
    "operations.cancelling": "Cancelling…",
    "operations.cancelling_after_batch": "Cancelling the current request…",
    "operations.sync_cancelled": "Sync cancelled. Completed batches remain synced.",
    "operations.refreshing_after_sync": "Refreshing collection state…",
    "vector.change_storage_location_help": "Advanced deployment setting. Existing collections are not moved automatically.",
    "vector.change_location": "Change location",
    "vector.current_container_path": "Current container path",
    "users.assign_existing_profile": "Assign existing LLM profile",
    "users.choose_existing_profile": "Choose a configured provider…",
    "users.use_profile": "Use profile",
    "users.assign_existing_profile_help": "Copies an existing administrator provider into the approved researcher profile set. Secrets remain server-side for researcher accounts.",
    "record.id": "Record",
    "record.open": "Open record",
    "record.text": "Text",
})
DEFAULT_FR_CA.update({
    "research.result_layout": "Disposition des résultats",
    "research.layout_compact": "Tableau compact",
    "research.layout_roomy": "Tableau confortable",
    "research.layout_cards": "Cartes",
    "research.contains": "contient",
    "operations.blocking_sync_help": "Cette synchronisation volumineuse s’exécute au premier plan par lots de 500. Les autres actions DerridAI sont suspendues jusqu’à la fin ou jusqu’à l’annulation.",
    "operations.preparing_sync": "Préparation des fiches…",
    "operations.keep_tab_open": "Gardez cet onglet DerridAI ouvert pendant la synchronisation.",
    "operations.cancelling": "Annulation…",
    "operations.cancelling_after_batch": "Annulation de la requête en cours…",
    "operations.sync_cancelled": "Synchronisation annulée. Les lots terminés restent synchronisés.",
    "operations.refreshing_after_sync": "Actualisation de l’état de la collection…",
    "vector.change_storage_location_help": "Paramètre de déploiement avancé. Les collections existantes ne sont pas déplacées automatiquement.",
    "vector.change_location": "Changer l’emplacement",
    "vector.current_container_path": "Chemin actuel dans le conteneur",
    "users.assign_existing_profile": "Attribuer un profil LLM existant",
    "users.choose_existing_profile": "Choisir un fournisseur configuré…",
    "users.use_profile": "Utiliser le profil",
    "users.assign_existing_profile_help": "Copie un fournisseur administrateur existant dans l’ensemble des profils approuvés pour les chercheurs. Les secrets restent côté serveur pour les comptes chercheurs.",
    "record.id": "Fiche",
    "record.open": "Ouvrir la fiche",
    "record.text": "Texte",
})


# 0.31.3 Research routing and configurable-role strings.
DEFAULT_EN_US.update({
    "research.page_kicker": "Evidence-grounded inquiry",
    "research.page_title": "Research workspace",
    "research.page_subtitle": "Ask the corpus, inspect the evidence, and keep provenance attached to the answer.",
    "research.redirect_database": "Research needs a corpus database. Opening Corpus database so you can create, restore, or select one.",
    "research.redirect_database_denied": "Research needs a corpus database, but your role cannot open Corpus database. Ask an administrator to configure one or grant access.",
    "roles.create": "Create role",
    "roles.created": "Role created.",
    "roles.delete": "Delete role",
    "roles.deleted": "Role deleted.",
    "roles.delete_confirm": "Delete this role? Users must be reassigned first.",
    "roles.superuser": "Superuser",
    "roles.default_role": "Default role",
    "roles.custom_role": "Custom role",
    "roles.non_admin_help": "Researcher is the default non-admin role. Custom roles use the same protected non-admin data boundary, with the permissions you enable below.",
    "roles.create_help": "Start from an existing non-admin role, then adjust its permissions.",
    "roles.name": "Role name",
    "roles.role_description": "Description",
    "roles.template": "Start with permissions from",
    "roles.description": "Create non-admin roles and define exactly which protected pages and features each role can use.",
    "users.create_help": "Researcher is the default non-admin role. Additional roles can be created on Roles & permissions.",
})
DEFAULT_FR_CA.update({
    "research.page_kicker": "Recherche fondée sur les preuves",
    "research.page_title": "Espace de recherche",
    "research.page_subtitle": "Interrogez le corpus, examinez les preuves et conservez la provenance avec la réponse.",
    "research.redirect_database": "La recherche nécessite une base de corpus. Ouverture de la base de corpus afin de pouvoir en créer, restaurer ou sélectionner une.",
    "research.redirect_database_denied": "La recherche nécessite une base de corpus, mais votre rôle ne permet pas d’ouvrir la base de corpus. Demandez à un administrateur de la configurer ou de vous accorder l’accès.",
    "roles.create": "Créer un rôle",
    "roles.created": "Rôle créé.",
    "roles.delete": "Supprimer le rôle",
    "roles.deleted": "Rôle supprimé.",
    "roles.delete_confirm": "Supprimer ce rôle? Les utilisateurs doivent d’abord être réaffectés.",
    "roles.superuser": "Superutilisateur",
    "roles.default_role": "Rôle par défaut",
    "roles.custom_role": "Rôle personnalisé",
    "roles.non_admin_help": "Chercheur est le rôle non administrateur par défaut. Les rôles personnalisés utilisent la même limite de données protégée, avec les autorisations activées ci-dessous.",
    "roles.create_help": "Commencez à partir d’un rôle non administrateur existant, puis ajustez ses autorisations.",
    "roles.name": "Nom du rôle",
    "roles.role_description": "Description",
    "roles.template": "Commencer avec les autorisations de",
    "roles.description": "Créez des rôles non administrateur et définissez précisément les pages et fonctions protégées que chaque rôle peut utiliser.",
    "users.create_help": "Chercheur est le rôle non administrateur par défaut. Des rôles supplémentaires peuvent être créés dans Rôles et autorisations.",
})


# 0.35.0 — complete native UI key parity and professional Canadian French (Québec).
# The fr-CA locale deliberately follows Québec usage and OQLF terminology where
# applicable while preserving accepted technical acronyms and product names.
DEFAULT_EN_US.update({'annotations.removed': 'Record annotation removed',
 'content_filter.warning': 'That language is not permitted for researcher accounts. The flagged term was removed.',
 'dashboard.appearance': 'Appearance',
 'dashboard.appearance_help': 'Choose the interface accent that is easiest for you to read.',
 'dashboard.appearance_saved': 'Appearance updated',
 'dashboard.interface_theme': 'Interface theme',
 'dashboard.more_appearance_settings': 'More appearance settings',
 'dashboard.other_works': 'Other works',
 'dashboard.words': 'words',
 'dashboard.work_record_share': 'Works as percentage of total records',
 'dashboard.work_word_share': 'Works as percentage of total words',
 'language.background_translation': 'Runs in the background',
 'language.background_translation_help': 'You can close this window immediately and continue working.',
 'language.english_short': 'English',
 'language.french_short': 'French',
 'language.removed': 'Language removed.',
 'language.review_after': 'Review after completion',
 'language.review_after_help': 'The installed dictionary will appear here when translation finishes; review and edit '
                               'any field normally.',
 'language.saved': 'Language dictionary saved.',
 'language.start_translation': 'Start translation',
 'language.starting': 'Starting…',
 'language.track_operations': 'Track it in Operations',
 'language.track_operations_help': 'Progress and failures appear with other background jobs.',
 'language.translation_started': 'Translation started in the background. Track progress in Operations; the new '
                                 'language will appear when the job finishes.',
 'nav.roles': 'Roles & permissions',
 'permissions.appearance_denied': 'Appearance controls are disabled for this role.',
 'permissions.evidence_denied': 'Your role cannot change selected evidence.',
 'permissions.no_workspace_shortcuts': 'No additional workspace pages are enabled for this role.',
 'providers.ollama': 'Ollama',
 'providers.openai_compatible': 'OpenAI-compatible',
 'rag.skip_retrieval_short': 'Evidence only',
 'record.clear_search': 'Clear search',
 'record.page_not_recorded': 'Page not recorded',
 'research.active_pipelines': 'Active research pipelines',
 'research.active_profile': 'Active profile',
 'research.advanced_generation': 'Advanced generation parameters',
 'research.advanced_generation_help': 'Context, sampling, token limits, and provider-specific options',
 'research.cancel_run': 'Cancel research run',
 'research.candidate_pool': 'Candidate pool',
 'research.candidate_pool_help': 'Control how broadly DerridAI searches before fusion and reranking.',
 'research.concurrent_requests': 'concurrent requests',
 'research.context_window': 'Context window',
 'research.corpus_retrieval': 'Corpus and retrieval',
 'research.corpus_retrieval_help': 'Language routing, retrieval depth, reranking, citation binding, and grading.',
 'research.cross_encoder': 'Cross-encoder',
 'research.database': 'Database',
 'research.evaluation': 'Evaluation',
 'research.evaluation_help': 'Optionally grade the final response after generation without blocking the main Research '
                             'workspace.',
 'research.evidence_budget': 'Evidence budget',
 'research.evidence_budget_help': 'Set an upper bound for each passage and for the full evidence packet sent to '
                                  'generation.',
 'research.evidence_nav_help': 'Context budget, source binding and grading',
 'research.expert_sections': 'Expert settings sections',
 'research.fetch_k_label': 'MMR candidate pool',
 'research.generation_nav_help': 'Model and per-run inference controls',
 'research.generation_provider': 'Generation provider',
 'research.generation_provider_help': 'Choose the approved provider and model for this run. Fine tuning stays out of '
                                      'the way until needed.',
 'research.inference_parameters': 'Inference parameters',
 'research.inference_parameters_help': 'Per-run model controls. Leave profile defaults unchanged unless the research '
                                       'task requires a reproducible override.',
 'research.k_label': 'Candidates retained',
 'research.keep_alive': 'Keep model loaded',
 'research.lambda_label': 'Relevance balance',
 'research.lexical_fallback': 'Lexical/vector fallback',
 'research.max_output_tokens': 'Maximum output',
 'research.minimum_probability': 'Minimum probability',
 'research.nucleus_sampling': 'Nucleus sampling',
 'research.parallel_runs_help': 'Start another question at any time. Each run continues independently and provider '
                                'concurrency limits determine when queued work executes.',
 'research.pipeline_running_one': 'pipeline in progress',
 'research.pipelines_running_many': 'pipelines in progress',
 'research.provider_options_help': 'Advanced provider-specific options are merged into this run only.',
 'research.ready_to_run': 'Ready to research',
 'research.repeat_penalty': 'Repeat penalty',
 'research.reranking_decomposition': 'Reranking & query decomposition',
 'research.reranking_decomposition_help': 'Refine the fused candidate set and optionally expand the question into '
                                          'multilingual subqueries.',
 'research.reset_section': 'Reset section',
 'research.retrieval_nav_help': 'Routing, candidate depth and reranking',
 'research.retrieval_settings': 'Retrieval & evidence settings',
 'research.routing': 'Routing',
 'research.routing_help': 'Choose which document languages and retrieval strategies participate in candidate '
                          'discovery.',
 'research.rrf_label': 'Fusion smoothing',
 'research.selected_evidence_only': 'Selected evidence only',
 'research.settings_apply_note': 'Changes affect the next Research run; saved provider profiles are not modified.',
 'research.settings_reproducibility_note': 'These values are stored with each run so an analysis can be reproduced '
                                           'later.',
 'research.similarity': 'Similarity',
 'research.source_binding': 'Source binding',
 'research.source_binding_help': 'Keep generated claims auditable against deterministic evidence identifiers and '
                                 'citations.',
 'research.status_cancelled': 'Cancelled',
 'research.status_cancelling': 'Cancelling',
 'research.status_completed': 'Completed',
 'research.status_failed': 'Failed',
 'research.status_queued': 'Queued',
 'research.status_running': 'Running',
 'research.thinking_high': 'High',
 'research.thinking_low': 'Low',
 'research.thinking_medium': 'Medium',
 'research.top_k_sampling': 'Top-k sampling',
 'research.view_all_runs': 'View all runs',
 'research.works_cited_help': 'Add a deterministic bibliography after the answer.',
 'roles.admin_locked_help': 'Administrator access is fixed to full application control so administrative access cannot '
                            'be accidentally removed.',
 'roles.manage': 'Manage permissions',
 'roles.role_list': 'Roles',
 'roles.saved': 'Role permissions saved.',
 'roles.title': 'Roles & permissions',
 'roles.users_link_help': 'Role capabilities are configured centrally and enforced by both navigation and API '
                          'permissions.',
 'theme.blue': 'Blue',
 'theme.green': 'Green',
 'theme.slate': 'Slate',
 'users.created_toast': 'User created.',
 'users.deleted_toast': 'User deleted.',
 'users.disabled_toast': 'User disabled.',
 'users.enabled_toast': 'User enabled.',
 'users.password_saved_toast': 'Password reset.',
 'users.role_saved_toast': 'Role updated.',
 'vector.english_collection': 'English collection',
 'vector.english_collection_help': 'Receives records routed as English.',
 'vector.french_collection': 'French collection',
 'vector.french_collection_help': 'Receives records routed as French.',
 'vector.language_source_help': 'Source collection stays unchanged. Existing target collections are updated according '
                                'to the current routing rules.'})
DEFAULT_FR_CA.update({'annotations.removed': 'Annotation de la fiche supprimée.',
 'app.subtitle': 'Visualiseur de corpus',
 'content_filter.warning': 'Ce langage n’est pas permis dans les comptes chercheurs. Le terme signalé a été supprimé.',
 'dashboard.appearance': 'Apparence',
 'dashboard.appearance_help': 'Choisissez la couleur d’accentuation qui offre la meilleure lisibilité.',
 'dashboard.appearance_saved': 'Apparence mise à jour.',
 'dashboard.interface_theme': 'Thème de l’interface',
 'dashboard.llm_provider_help': 'Configurez le fournisseur utilisé pour les flux de travail assistés par LLM.',
 'dashboard.llm_provider_settings': 'Paramètres des fournisseurs LLM',
 'dashboard.more_appearance_settings': 'Autres paramètres d’apparence',
 'dashboard.other_works': 'Autres œuvres',
 'dashboard.words': 'mots',
 'dashboard.work_record_share': 'Répartition des œuvres selon le nombre total de fiches',
 'dashboard.work_word_share': 'Répartition des œuvres selon le nombre total de mots',
 'language.background_translation': 'S’exécute en arrière-plan',
 'language.background_translation_help': 'Vous pouvez fermer cette fenêtre immédiatement et poursuivre votre travail.',
 'language.english_short': 'Anglais',
 'language.french_ca': 'Français',
 'language.french_short': 'Français',
 'language.page_description': 'Les langues intégrées sont l’anglais des États-Unis et le français canadien du Québec. '
                              'Vous pouvez installer d’autres dictionnaires de langue au moyen d’un profil de '
                              'fournisseur LLM configuré, puis réviser directement chaque chaîne traduite de '
                              'l’interface.',
 'language.removed': 'Langue supprimée.',
 'language.review_after': 'Réviser après l’exécution',
 'language.review_after_help': 'Une fois la traduction terminée, le dictionnaire installé apparaîtra ici; révisez et '
                               'modifiez ensuite chaque champ au besoin.',
 'language.saved': 'Dictionnaire de langue enregistré.',
 'language.start_translation': 'Lancer la traduction',
 'language.starting': 'Démarrage…',
 'language.track_operations': 'Suivre dans Opérations',
 'language.track_operations_help': 'La progression et les erreurs s’affichent avec les autres tâches en arrière-plan.',
 'language.translation_started': 'La traduction a démarré en arrière-plan. Suivez sa progression dans Opérations; la '
                                 'nouvelle langue apparaîtra lorsque la tâche sera terminée.',
 'nav.cache': 'Mémoire cache des réponses',
 'nav.roles': 'Rôles et autorisations',
 'permissions.appearance_denied': 'Les paramètres d’apparence sont désactivés pour ce rôle.',
 'permissions.evidence_denied': 'Votre rôle ne permet pas de modifier les preuves sélectionnées.',
 'permissions.no_workspace_shortcuts': 'Aucune autre page de l’espace de travail n’est activée pour ce rôle.',
 'permissions.rag_denied': 'Votre rôle ne permet pas d’exécuter des pipelines de recherche.',
 'providers.ollama': 'Ollama',
 'providers.openai_compatible': 'Compatible avec OpenAI',
 'rag.skip_retrieval': 'Utiliser uniquement les preuves sélectionnées (sans repérage)',
 'rag.skip_retrieval_short': 'Preuves seulement',
 'record.clear_search': 'Effacer la recherche',
 'record.page_not_recorded': 'Page non indiquée',
 'research.active_pipelines': 'Pipelines de recherche actifs',
 'research.active_profile': 'Profil actif',
 'research.advanced_generation': 'Paramètres avancés de génération',
 'research.advanced_generation_help': 'Contexte, échantillonnage, limites de jetons et options propres au fournisseur',
 'research.auto_grade_help': 'S’exécute comme dernière étape du pipeline en arrière-plan.',
 'research.cancel_run': 'Annuler l’exécution de recherche',
 'research.candidate_pool': 'Bassin de candidats',
 'research.candidate_pool_help': 'Déterminez l’étendue du repérage avant la fusion des classements et le reclassement.',
 'research.concurrent_requests': 'requêtes simultanées',
 'research.context_window': 'Fenêtre de contexte',
 'research.corpus_retrieval': 'Corpus et repérage',
 'research.corpus_retrieval_help': 'Routage linguistique, profondeur du repérage, reclassement, liaison des citations '
                                   'et évaluation.',
 'research.cross_encoder': 'Encodeur croisé',
 'research.database': 'Base de données',
 'research.evaluation': 'Évaluation',
 'research.evaluation_help': 'Évaluez facultativement la réponse finale après la génération, sans bloquer l’espace '
                             'Recherche.',
 'research.evidence_budget': 'Budget de preuves',
 'research.evidence_budget_help': 'Fixez une limite pour chaque passage et pour l’ensemble des preuves transmis au '
                                  'modèle de génération.',
 'research.evidence_nav_help': 'Budget de contexte, liaison aux sources et évaluation',
 'research.expert_sections': 'Sections des paramètres experts',
 'research.fetch_k_label': 'Bassin de candidats MMR',
 'research.generation_nav_help': 'Modèle et paramètres d’inférence propres à l’exécution',
 'research.generation_provider': 'Fournisseur de génération',
 'research.generation_provider_help': 'Choisissez le fournisseur et le modèle autorisés pour cette exécution. Les '
                                      'réglages fins demeurent masqués tant qu’ils ne sont pas nécessaires.',
 'research.inference_parameters': 'Paramètres d’inférence',
 'research.inference_parameters_help': 'Paramètres du modèle propres à cette exécution. Conservez les valeurs du '
                                       'profil à moins qu’une dérogation reproductible soit nécessaire.',
 'research.k_help': 'Candidats conservés par voie de repérage',
 'research.k_label': 'Candidats conservés',
 'research.keep_alive': 'Maintenir le modèle chargé',
 'research.lambda_label': 'Équilibre de pertinence',
 'research.lexical_fallback': 'Solution de rechange lexicale/vectorielle',
 'research.loading_databases': 'Chargement des bases de données du corpus…',
 'research.max_output_tokens': 'Sortie maximale',
 'research.minimum_probability': 'Probabilité minimale',
 'research.no_database': 'Aucune base de données du corpus disponible',
 'research.no_database_admin_help': 'Créez ou restaurez une base de données du corpus pour utiliser la recherche '
                                    'sémantique.',
 'research.no_database_help': 'Un administrateur doit créer ou restaurer une base de données du corpus avant que les '
                              'chercheurs puissent utiliser la recherche et l’espace Recherche.',
 'research.no_selected_evidence_help': 'Ajoutez des fiches depuis Recherche, Œuvres ou la vue Fiche. Le repérage peut '
                                       'toujours trouver des preuves automatiquement.',
 'research.none_selected': 'Aucune base de données sélectionnée',
 'research.nucleus_sampling': 'Échantillonnage top-p',
 'research.parallel_runs_help': 'Vous pouvez lancer une autre question à tout moment. Chaque exécution se poursuit '
                                'indépendamment; les limites de simultanéité du fournisseur déterminent quand les '
                                'tâches en attente s’exécutent.',
 'research.pipeline_help': 'Configurez le corpus, le repérage, les preuves et la génération. Les options avancées '
                           'demeurent disponibles sans détourner l’attention du flux principal de recherche.',
 'research.pipeline_options': 'Repérage, preuves et génération',
 'research.pipeline_running_one': 'pipeline en cours',
 'research.pipelines_running_many': 'pipelines en cours',
 'research.provider_options_help': 'Les options avancées propres au fournisseur sont appliquées uniquement à cette '
                                   'exécution.',
 'research.query_decomposition_help': 'Générer des sous-requêtes et des formulations françaises avant le repérage.',
 'research.ready_to_run': 'Prêt à lancer la recherche',
 'research.redirect_database': 'Recherche nécessite une base de données du corpus. Ouverture de la page des bases de '
                               'données afin que vous puissiez en créer, en restaurer ou en sélectionner une.',
 'research.redirect_database_denied': 'Recherche nécessite une base de données du corpus, mais votre rôle ne permet '
                                      'pas d’ouvrir cette page. Demandez à un administrateur de configurer une base de '
                                      'données ou de vous accorder l’accès.',
 'research.repeat_penalty': 'Pénalité de répétition',
 'research.reranking_decomposition': 'Reclassement et décomposition de la requête',
 'research.reranking_decomposition_help': 'Affinez l’ensemble fusionné des candidats et, au besoin, développez la '
                                          'question en sous-requêtes multilingues.',
 'research.reset_section': 'Réinitialiser la section',
 'research.retrieval': 'Repérage',
 'research.retrieval_diagnostics': 'Diagnostics de repérage',
 'research.retrieval_nav_help': 'Routage, profondeur des candidats et reclassement',
 'research.retrieval_profile': 'Repérage',
 'research.retrieval_ready': 'Repérage prêt',
 'research.retrieval_routes': 'Voies de repérage',
 'research.retrieval_settings': 'Paramètres de repérage et de preuves',
 'research.routing': 'Routage',
 'research.routing_help': 'Choisissez les langues documentaires et les stratégies de repérage utilisées pour trouver '
                          'les candidats.',
 'research.rrf_label': 'Lissage de la fusion',
 'research.selected_database_help': 'Les recherches portent uniquement sur la base de données sélectionnée.',
 'research.selected_evidence_only': 'Preuves sélectionnées seulement',
 'research.semantic_db_search': 'Recherche sémantique dans la BD',
 'research.settings_apply_note': 'Les changements s’appliqueront à la prochaine recherche; les profils de fournisseur '
                                 'enregistrés ne seront pas modifiés.',
 'research.settings_reproducibility_note': 'Ces valeurs sont enregistrées avec chaque exécution afin de permettre la '
                                           'reproduction ultérieure d’une analyse.',
 'research.similarity': 'Similarité',
 'research.source_binding': 'Liaison aux sources',
 'research.source_binding_help': 'Conservez la vérifiabilité des affirmations générées grâce à des identifiants de '
                                 'preuve et à des citations déterministes.',
 'research.status_cancelled': 'Annulé',
 'research.status_cancelling': 'Annulation',
 'research.status_completed': 'Terminé',
 'research.status_failed': 'Échec',
 'research.status_queued': 'En attente',
 'research.status_running': 'En cours',
 'research.thinking_high': 'Élevé',
 'research.thinking_low': 'Faible',
 'research.thinking_medium': 'Moyen',
 'research.top_k_sampling': 'Échantillonnage top-k',
 'research.view_all_runs': 'Voir toutes les exécutions',
 'research.waiting': 'En attente du pipeline…',
 'research.works_cited_help': 'Ajoutez une bibliographie déterministe après la réponse.',
 'research.workspace_help': 'Formulez une question, choisissez les paramètres de repérage et de génération, épinglez '
                            'des preuves, puis exécutez le pipeline complet en conservant la provenance.',
 'roles.admin_locked_help': 'L’accès administrateur demeure fixé au contrôle complet de l’application afin d’éviter sa '
                            'suppression accidentelle.',
 'roles.manage': 'Gérer les autorisations',
 'roles.non_admin_help': 'Chercheur est le rôle non administrateur par défaut. Les rôles personnalisés respectent la '
                         'même frontière de protection des données, selon les autorisations activées ci-dessous.',
 'roles.role_list': 'Rôles',
 'roles.saved': 'Autorisations du rôle enregistrées.',
 'roles.title': 'Rôles et autorisations',
 'roles.users_link_help': 'Les capacités des rôles sont configurées centralement et appliquées à la fois dans la '
                          'navigation et dans les autorisations de l’API.',
 'settings.browser_workspace_note': 'Les préférences de thème sont enregistrées dans cet espace de travail du '
                                    'navigateur.',
 'theme.blue': 'Bleu',
 'theme.green': 'Vert',
 'theme.slate': 'Ardoise',
 'ui.corpus_viewer': 'Visualiseur de corpus',
 'users.create_help': 'Chercheur est le rôle non administrateur par défaut. Vous pouvez créer d’autres rôles dans '
                      'Rôles et autorisations.',
 'users.created_toast': 'Compte créé.',
 'users.deleted_toast': 'Compte supprimé.',
 'users.disabled_toast': 'Compte désactivé.',
 'users.enabled_toast': 'Compte activé.',
 'users.password_saved_toast': 'Mot de passe réinitialisé.',
 'users.role_saved_toast': 'Rôle mis à jour.',
 'vector.english_collection': 'Collection anglaise',
 'vector.english_collection_help': 'Reçoit les fiches acheminées comme étant en anglais.',
 'vector.french_collection': 'Collection française',
 'vector.french_collection_help': 'Reçoit les fiches acheminées comme étant en français.',
 'vector.language_source_help': 'La collection source demeure inchangée. Les collections cibles existantes sont mises '
                                'à jour selon les règles de routage actuelles.'})


# 0.35.0 — compatibility-view and metadata localization completeness.
# Every entry is paired across en-US/fr-CA so legacy UI text can be translated
# without translating corpus text or changing scholarly metadata values.
DEFAULT_EN_US.update({'field.__db_status': 'DB status',
 'field.__file': 'File',
 'field._chroma_id': 'Chroma ID',
 'field.attribution_confidence': 'Attribution confidence',
 'field.canonical_work_id': 'Canonical work ID',
 'field.claim_scope': 'Claim scope',
 'field.concepts': 'Concepts',
 'field.cover_url': 'Cover URL',
 'field.discourse_role': 'Discourse role',
 'field.document_author': 'Document author',
 'field.document_is_translation': 'Document is translation',
 'field.document_language': 'Document language',
 'field.document_title': 'Document title',
 'field.edition': 'Edition',
 'field.extraction_quality': 'Extraction quality',
 'field.full_citation': 'Full citation',
 'field.inline_citation': 'Inline citation',
 'field.is_direct_quote': 'Direct quote',
 'field.isbn': 'ISBN',
 'field.needs_review': 'Needs review',
 'field.original_language': 'Original language',
 'field.original_title': 'Original title',
 'field.page_end': 'Page end',
 'field.page_start': 'Page start',
 'field.pdf_file': 'PDF file',
 'field.pdf_links': 'PDF links',
 'field.pdf_page': 'PDF page',
 'field.pdf_pages': 'PDF pages',
 'field.persons': 'Persons',
 'field.position_holder': 'Position holder',
 'field.primary_text': 'Primary text',
 'field.proposition_status': 'Proposition status',
 'field.publication_place': 'Publication place',
 'field.publication_year': 'Publication year',
 'field.publisher': 'Publisher',
 'field.quotation_chain': 'Quotation chain',
 'field.quoted_addressee': 'Quoted addressee',
 'field.quoted_author': 'Quoted author',
 'field.quoted_position_holder': 'Quoted position holder',
 'field.quoted_referent': 'Quoted referent',
 'field.quoted_speaker': 'Quoted speaker',
 'field.quoted_work': 'Quoted work',
 'field.record_id': 'Record ID',
 'field.region_author': 'Region author',
 'field.region_type': 'Region type',
 'field.review_reason': 'Review reason',
 'field.semantic_classification_confidence': 'Semantic classification confidence',
 'field.semantic_function': 'Semantic function',
 'field.short_title': 'Short title',
 'field.speaker': 'Speaker',
 'field.stance': 'Stance',
 'field.target': 'Target',
 'field.text': 'Extracted text',
 'field.text_length': 'Text length',
 'field.topics': 'Topics',
 'field.translator': 'Translator',
 'field.updates': 'Change history',
 'field.work': 'Work',
 'field.works_referenced': 'Works referenced',
 'field.year': 'Year',
 'language.french_ca': 'Français',
 'language.page_description': 'Built-in locales are U.S. English and Canadian French (Québec). Install additional '
                              'locale dictionaries by BCP 47 language-region code using an LLM, then review every UI '
                              'string directly.',
 'legacy.accepted_fields': 'accepted fields',
 'legacy.accepted_results': 'accepted results',
 'legacy.active_jsonl_tab': 'Active JSONL tab',
 'legacy.active_ollama_rag': 'Active Ollama RAG',
 'legacy.add_column': 'Add column',
 'legacy.additional_instructions': 'Additional instructions',
 'legacy.aggregate_jsonl': 'Aggregate JSONL',
 'legacy.all': 'All',
 'legacy.all_loaded_records': 'All loaded records',
 'legacy.all_works': 'All works',
 'legacy.allowed_fields': 'Allowed fields',
 'legacy.answer': 'Answer',
 'legacy.any': 'Any',
 'legacy.api_key': 'API key',
 'legacy.append_works_cited': 'Append Works Cited',
 'legacy.apply': 'Apply',
 'legacy.attribution': 'Attribution',
 'legacy.attribution_confidence': 'Attribution confidence',
 'legacy.auto_improve_changes': 'Auto-improve changes',
 'legacy.auto_router': 'Auto router',
 'legacy.available_loaded_works': 'Available loaded works',
 'legacy.available_models': 'Available models',
 'legacy.back': '← Back',
 'legacy.background_auto_improve': 'Background Auto-improve',
 'legacy.background_operation': 'Background operation',
 'legacy.background_operations': 'Background operations',
 'legacy.background_review': 'Background review',
 'legacy.backup_restore': 'Backup & restore',
 'legacy.cached_as': 'Cached as',
 'legacy.cached_responses': 'Cached responses',
 'legacy.cancel': 'Cancel',
 'legacy.cancel_operation': 'Cancel operation',
 'legacy.cancel_requested': 'Cancel requested',
 'legacy.cancelling': 'Cancelling…',
 'legacy.case_sensitive': 'Case-sensitive',
 'legacy.change_history': 'Change history',
 'legacy.changed': 'Changed',
 'legacy.changed_files': 'Changed files',
 'legacy.check': 'Check',
 'legacy.checking': 'Checking',
 'legacy.chroma_destination': 'Chroma destination',
 'legacy.chroma_sync': 'Chroma sync',
 'legacy.citation': 'Citation',
 'legacy.citations': 'Citations',
 'legacy.claim_scope': 'Claim scope',
 'legacy.cleaned_page_text': 'Cleaned page text',
 'legacy.clear': 'Clear',
 'legacy.clear_cache': 'Clear cache',
 'legacy.clear_instructions': 'Clear instructions',
 'legacy.clear_past_results': 'Clear past results',
 'legacy.clear_record': 'Clear record',
 'legacy.clear_search': 'Clear search',
 'legacy.clear_selection': 'Clear selection',
 'legacy.close': 'Close',
 'legacy.close_preview': 'Close preview',
 'legacy.collapse_all': 'Collapse all',
 'legacy.collection': 'Collection',
 'legacy.collection_name': 'Collection name',
 'legacy.columns': 'Columns',
 'legacy.condition': 'Condition',
 'legacy.configure_columns': 'Configure columns',
 'legacy.configured_model': 'Configured model',
 'legacy.context': 'Context',
 'legacy.context_num_ctx': 'Context (num_ctx)',
 'legacy.copy_answer': 'Copy answer',
 'legacy.copy_entire_record': 'Copy entire record',
 'legacy.cover_url': 'Cover URL',
 'legacy.create_collection': 'Create collection',
 'legacy.create_download': 'Create & download',
 'legacy.create_subset_tab': 'Create subset tab',
 'legacy.created': 'Created',
 'legacy.cross_encoder': 'Cross-encoder',
 'legacy.cross_encoder_model': 'Cross-encoder model',
 'legacy.current': 'Current',
 'legacy.current_file': 'Current file',
 'legacy.current_page_records': 'Current-page records',
 'legacy.current_pdf': 'current PDF',
 'legacy.default_reranker': 'Default reranker',
 'legacy.default_run_mode': 'Default run mode',
 'legacy.delete': 'Delete',
 'legacy.desktop_notifications': 'Desktop notifications',
 'legacy.details': 'Details',
 'legacy.details_timeline': 'Details / timeline',
 'legacy.differences': 'Differences',
 'legacy.direct_quote': 'Direct quote',
 'legacy.discourse': 'Discourse',
 'legacy.discovered': 'Discovered',
 'legacy.discovered_model': 'Discovered model',
 'legacy.discovered_models': 'Discovered models',
 'legacy.dismiss': 'Dismiss',
 'legacy.document_author': 'Document author',
 'legacy.document_language': 'Document language',
 'legacy.document_languages': 'Document languages',
 'legacy.document_title': 'Document title',
 'legacy.edit_chroma_record': 'Edit Chroma record',
 'legacy.edit_record': 'Edit record',
 'legacy.edit_work_metadata': 'Edit work metadata',
 'legacy.embedding': 'Embedding',
 'legacy.endpoint': 'Endpoint',
 'legacy.english': 'English',
 'legacy.evidence': 'Evidence',
 'legacy.evidence_selected': 'Evidence selected',
 'legacy.expand_all': 'Expand all',
 'legacy.export_jsonl': 'Export JSONL',
 'legacy.expression': 'Expression',
 'legacy.extract_all_text': 'Extract all text',
 'legacy.extract_page_text': 'Extract page text',
 'legacy.extracted_text': 'Extracted text',
 'legacy.extraction_quality': 'Extraction quality',
 'legacy.failed': 'failed',
 'legacy.field': 'Field',
 'legacy.fields_changed': 'fields changed',
 'legacy.fields_compared': 'fields compared',
 'legacy.filter': 'Filter',
 'legacy.filter_models': 'Filter models…',
 'legacy.filter_value': 'Filter value',
 'legacy.finished': 'Finished',
 'legacy.first': 'First',
 'legacy.forward': 'Forward →',
 'legacy.french': 'French',
 'legacy.full_citation': 'Full citation',
 'legacy.full_cite': 'Full cite',
 'legacy.generation': 'Generation',
 'legacy.generation_model': 'Generation model',
 'legacy.graded': 'graded',
 'legacy.grouped_conditions': 'Grouped conditions',
 'legacy.identical_fields': 'identical fields',
 'legacy.inline': 'Inline',
 'legacy.inline_citation': 'Inline citation',
 'legacy.inline_cite': 'Inline cite',
 'legacy.instructions': 'Instructions',
 'legacy.interactive_foreground': 'Interactive foreground',
 'legacy.jsonl_destination': 'JSONL destination',
 'legacy.jsonl_tabs': 'JSONL tabs',
 'legacy.last': 'Last',
 'legacy.lexical_vector_fallback': 'Lexical/vector fallback',
 'legacy.linked_records': 'linked records',
 'legacy.linked_works': 'linked works',
 'legacy.llm_proposals': 'LLM proposals',
 'legacy.llm_providers': 'LLM providers',
 'legacy.llm_providers_2': 'LLM Providers',
 'legacy.loaded_records': 'loaded records',
 'legacy.loading_view': 'Loading view',
 'legacy.make_default': 'Make default',
 'legacy.manual': 'Manual',
 'legacy.manual_model_id': 'Manual model ID',
 'legacy.match_all_and': 'Match ALL (AND)',
 'legacy.match_any_or': 'Match ANY (OR)',
 'legacy.max_output': 'Max output',
 'legacy.max_output_tokens': 'Max output tokens',
 'legacy.merge_jsonl_tabs': 'Merge JSONL tabs',
 'legacy.merged_file_name': 'Merged file name',
 'legacy.metadata': 'Metadata',
 'legacy.metadata_output': 'Metadata output',
 'legacy.mmr_fetch_k': 'MMR fetch_k',
 'legacy.mmr_lambda': 'MMR lambda',
 'legacy.model_kind': 'Model kind',
 'legacy.model_kind_filter': 'Model kind filter',
 'legacy.model_mode': 'Model mode',
 'legacy.model_name': 'Model name',
 'legacy.model_readiness': 'Model readiness',
 'legacy.model_size': 'Model size',
 'legacy.more_text_tools': 'More text tools',
 'legacy.needs_review': 'Needs review',
 'legacy.needs_review_records': 'Needs-review records',
 'legacy.new_value': 'New value',
 'legacy.newer': 'Newer →',
 'legacy.next': 'Next',
 'legacy.next_2': 'Next →',
 'legacy.no': 'No',
 'legacy.no_data': 'No data',
 'legacy.no_database': 'No database',
 'legacy.no_matches': 'No matches',
 'legacy.no_reranking': 'No reranking',
 'legacy.none_reported': 'None reported.',
 'legacy.notice': 'Notice',
 'legacy.ocr_text': 'OCR / text',
 'legacy.offline': 'Offline',
 'legacy.older': '← Older',
 'legacy.ollama_endpoint': 'Ollama endpoint',
 'legacy.on_this_page': 'on this page',
 'legacy.online': 'Online',
 'legacy.open_dashboard': 'Open Dashboard',
 'legacy.open_full_details': 'Open full details',
 'legacy.open_in_faq': 'Open in FAQ',
 'legacy.open_library': 'Open Library',
 'legacy.open_pdf_explorer': 'Open PDF Explorer',
 'legacy.open_result': 'Open result',
 'legacy.openai_compatible_endpoint': 'OpenAI-compatible endpoint',
 'legacy.operation_timeline': 'Operation timeline',
 'legacy.original_language': 'Original language',
 'legacy.original_title': 'Original title',
 'legacy.other_fields': 'Other fields',
 'legacy.page': 'Page',
 'legacy.page_end': 'Page end',
 'legacy.page_start': 'Page start',
 'legacy.page_text': 'Page text',
 'legacy.pages': 'Pages',
 'legacy.pdf_document': 'PDF document',
 'legacy.pdf_explorer': 'PDF Explorer',
 'legacy.pdf_file': 'PDF file',
 'legacy.pdf_links': 'PDF links',
 'legacy.pdf_page': 'PDF page',
 'legacy.pdf_pages': 'PDF pages',
 'legacy.pending': 'Pending',
 'legacy.pipeline_timings': 'Pipeline timings',
 'legacy.precomputed_vectors': 'Precomputed vectors',
 'legacy.preview_record': 'Preview record',
 'legacy.previous': 'Previous',
 'legacy.previous_2': '← Previous',
 'legacy.primary_text': 'Primary text',
 'legacy.profiles': 'profiles',
 'legacy.progress': 'Progress',
 'legacy.proposed': 'Proposed',
 'legacy.proposed_change': 'proposed change',
 'legacy.provider_model': 'Provider / model',
 'legacy.provider_profile': 'Provider profile',
 'legacy.provider_profiles': 'Provider profiles',
 'legacy.publication_place': 'Publication place',
 'legacy.publication_year': 'Publication year',
 'legacy.publisher': 'Publisher',
 'legacy.quantization': 'Quantization',
 'legacy.query_decomposition': 'Query decomposition',
 'legacy.question': 'Question',
 'legacy.question_prompt': 'Question / prompt',
 'legacy.queued': 'Queued',
 'legacy.quotation_chain': 'Quotation chain',
 'legacy.quotation_provenance': 'Quotation provenance',
 'legacy.quoted_addressee': 'Quoted addressee',
 'legacy.quoted_author': 'Quoted author',
 'legacy.quoted_referent': 'Quoted referent',
 'legacy.quoted_work': 'Quoted work',
 'legacy.rag_pipeline': 'RAG pipeline',
 'legacy.rag_result': 'RAG result',
 'legacy.rationale': 'Rationale',
 'legacy.ready': 'Ready',
 'legacy.reasoning': 'Reasoning',
 'legacy.record': 'Record',
 'legacy.record_actions': 'Record actions',
 'legacy.record_annotation': 'Record annotation',
 'legacy.record_comparison': 'Record Comparison',
 'legacy.record_history': 'Record history',
 'legacy.record_preview': 'Record preview',
 'legacy.records': 'records',
 'legacy.records_to_sync': 'Records to sync',
 'legacy.region_author': 'Region author',
 'legacy.region_type': 'Region type',
 'legacy.reject_selected': 'Reject selected',
 'legacy.rejected_fields': 'rejected fields',
 'legacy.rejected_results': 'rejected results',
 'legacy.remove': 'Remove',
 'legacy.remove_condition': 'Remove condition',
 'legacy.remove_evidence': 'Remove evidence',
 'legacy.remove_filter': 'Remove filter',
 'legacy.remove_from_queue': 'Remove from queue',
 'legacy.remove_group': 'Remove group',
 'legacy.remove_work': 'Remove work',
 'legacy.request_configuration': 'Request configuration',
 'legacy.rerank_top_n': 'Rerank top N',
 'legacy.reranker': 'Reranker',
 'legacy.researcher_access': 'Researcher access',
 'legacy.reset_defaults': 'Reset defaults',
 'legacy.response_faq': 'Response FAQ',
 'legacy.response_language': 'Response language',
 'legacy.responses': 'responses',
 'legacy.restore_original': 'Restore original',
 'legacy.result_summary': 'Result summary',
 'legacy.retrieval_diagnostics': 'Retrieval diagnostics',
 'legacy.retrieval_k': 'Retrieval k',
 'legacy.retrieval_routes': 'Retrieval routes',
 'legacy.review': 'Review',
 'legacy.review_behavior': 'Review behavior',
 'legacy.review_failed': 'Review failed',
 'legacy.review_preset': 'Review preset',
 'legacy.review_reason': 'Review reason',
 'legacy.review_results': 'Review results',
 'legacy.review_status': 'Review status',
 'legacy.reviewed': 'Reviewed',
 'legacy.reviewing': 'Reviewing',
 'legacy.rotate_left_90': 'Rotate left 90°',
 'legacy.rotate_right_90': 'Rotate right 90°',
 'legacy.run_in_background': 'Run in background',
 'legacy.run_in_foreground': 'Run in foreground',
 'legacy.run_review': 'Run review',
 'legacy.running': 'Running…',
 'legacy.save_columns': 'Save columns',
 'legacy.search_page_text': 'Search page text',
 'legacy.secondary_text': 'Secondary text',
 'legacy.select_all': 'Select all',
 'legacy.select_metadata': 'Select metadata',
 'legacy.select_none': 'Select none',
 'legacy.selected_evidence': 'selected evidence',
 'legacy.selected_records': 'Selected records',
 'legacy.selected_value': 'Selected value',
 'legacy.selection_mode': 'Selection mode',
 'legacy.semantic_classification_confidence': 'Semantic classification confidence',
 'legacy.semantic_function': 'Semantic function',
 'legacy.semantics': 'Semantics',
 'legacy.short_title': 'Short title',
 'legacy.source': 'Source',
 'legacy.source_collection': 'Source collection',
 'legacy.start_operation': 'Start operation',
 'legacy.started': 'Started',
 'legacy.started_by': 'Started by',
 'legacy.status': 'Status',
 'legacy.status_error': 'Status error',
 'legacy.summary': 'Summary',
 'legacy.target_records': 'Target records',
 'legacy.temperature': 'Temperature',
 'legacy.text': 'Text',
 'legacy.text_length': 'Text length',
 'legacy.this_version': 'This version',
 'legacy.traditional_search': 'Traditional search',
 'legacy.translation': 'Translation',
 'legacy.translator': 'Translator',
 'legacy.unavailable': 'Unavailable',
 'legacy.unknown': 'Unknown',
 'legacy.untitled_question': 'Untitled question',
 'legacy.use_model': 'Use model',
 'legacy.value': 'Value',
 'legacy.values': 'Values',
 'legacy.verify_carefully': 'verify carefully',
 'legacy.viewer_configuration': 'Viewer configuration',
 'legacy.waiting_in_queue': 'Waiting in queue.',
 'legacy.warm': 'Warm',
 'legacy.warming': 'Warming',
 'legacy.warmup_failed': 'Warmup failed',
 'legacy.words': 'words',
 'legacy.works': 'works',
 'legacy.works_and_records': 'Works and records',
 'legacy.works_cited': 'Works Cited',
 'legacy.works_referenced': 'Works referenced',
 'legacy.yes': 'Yes'})
DEFAULT_FR_CA.update({'field.__db_status': 'État de la BD',
 'field.__file': 'Fichier',
 'field._chroma_id': 'Identifiant Chroma',
 'field.attribution_confidence': 'Fiabilité de l’attribution',
 'field.canonical_work_id': 'Identifiant canonique de l’œuvre',
 'field.claim_scope': 'Portée de l’énoncé',
 'field.concepts': 'Concepts',
 'field.cover_url': 'URL de la couverture',
 'field.discourse_role': 'Rôle discursif',
 'field.document_author': 'Auteur du document',
 'field.document_is_translation': 'Document traduit',
 'field.document_language': 'Langue du document',
 'field.document_title': 'Titre du document',
 'field.edition': 'Édition',
 'field.extraction_quality': 'Qualité de l’extraction',
 'field.full_citation': 'Citation complète',
 'field.inline_citation': 'Citation dans le texte',
 'field.is_direct_quote': 'Citation directe',
 'field.isbn': 'ISBN',
 'field.needs_review': 'À réviser',
 'field.original_language': 'Langue originale',
 'field.original_title': 'Titre original',
 'field.page_end': 'Dernière page',
 'field.page_start': 'Première page',
 'field.pdf_file': 'Fichier PDF',
 'field.pdf_links': 'Liens PDF',
 'field.pdf_page': 'Page PDF',
 'field.pdf_pages': 'Pages PDF',
 'field.persons': 'Personnes',
 'field.position_holder': 'Détenteur de la position',
 'field.primary_text': 'Texte principal',
 'field.proposition_status': 'Statut de la proposition',
 'field.publication_place': 'Lieu de publication',
 'field.publication_year': 'Année de publication',
 'field.publisher': 'Maison d’édition',
 'field.quotation_chain': 'Chaîne de citations',
 'field.quoted_addressee': 'Destinataire cité',
 'field.quoted_author': 'Auteur cité',
 'field.quoted_position_holder': 'Détenteur de la position citée',
 'field.quoted_referent': 'Référent cité',
 'field.quoted_speaker': 'Locuteur cité',
 'field.quoted_work': 'Œuvre citée',
 'field.record_id': 'Identifiant de fiche',
 'field.region_author': 'Auteur de la région',
 'field.region_type': 'Type de région',
 'field.review_reason': 'Motif de révision',
 'field.semantic_classification_confidence': 'Fiabilité de la classification sémantique',
 'field.semantic_function': 'Fonction sémantique',
 'field.short_title': 'Titre abrégé',
 'field.speaker': 'Locuteur',
 'field.stance': 'Prise de position',
 'field.target': 'Cible',
 'field.text': 'Texte extrait',
 'field.text_length': 'Longueur du texte',
 'field.topics': 'Sujets',
 'field.translator': 'Traducteur',
 'field.updates': 'Historique des modifications',
 'field.work': 'Œuvre',
 'field.works_referenced': 'Œuvres citées',
 'field.year': 'Année',
 'language.concurrent_requests': 'nombre maximal de requêtes simultanées',
 'language.french_ca': 'Français',
 'language.locale_code': 'Code de langue et de région',
 'language.locale_code_help': 'Identifiant BCP 47 de langue et de région, par exemple de-DE ou es-MX.',
 'language.locale_pending': 'Code de langue et de région requis',
 'language.page_description': 'Les langues intégrées sont l’anglais des États-Unis et le français canadien du Québec. '
                              'Vous pouvez installer d’autres dictionnaires au moyen d’un code BCP 47 de langue et de '
                              'région, puis réviser directement chaque chaîne de l’interface.',
 'legacy.accepted_fields': 'champs acceptés',
 'legacy.accepted_results': 'résultats acceptés',
 'legacy.active_jsonl_tab': 'Onglet JSONL actif',
 'legacy.active_ollama_rag': 'RAG Ollama actif',
 'legacy.add_column': 'Ajouter une colonne',
 'legacy.additional_instructions': 'Instructions supplémentaires',
 'legacy.aggregate_jsonl': 'Agréger le JSONL',
 'legacy.all': 'Tout',
 'legacy.all_loaded_records': 'Toutes les fiches chargées',
 'legacy.all_works': 'Toutes les œuvres',
 'legacy.allowed_fields': 'Champs autorisés',
 'legacy.answer': 'Réponse',
 'legacy.any': 'N’importe lequel',
 'legacy.api_key': 'Clé API',
 'legacy.append_works_cited': 'Ajouter les ouvrages cités',
 'legacy.apply': 'Appliquer',
 'legacy.attribution': 'Attribution',
 'legacy.attribution_confidence': 'Fiabilité de l’attribution',
 'legacy.auto_improve_changes': 'Modifications d’amélioration automatique',
 'legacy.auto_router': 'Routage automatique',
 'legacy.available_loaded_works': 'Œuvres chargées disponibles',
 'legacy.available_models': 'Modèles disponibles',
 'legacy.back': '← Retour',
 'legacy.background_auto_improve': 'Amélioration automatique en arrière-plan',
 'legacy.background_operation': 'Opération en arrière-plan',
 'legacy.background_operations': 'Opérations en arrière-plan',
 'legacy.background_review': 'Révision en arrière-plan',
 'legacy.backup_restore': 'Sauvegarde et restauration',
 'legacy.cached_as': 'Mis en cache sous',
 'legacy.cached_responses': 'Réponses en mémoire cache',
 'legacy.cancel': 'Annuler',
 'legacy.cancel_operation': 'Annuler l’opération',
 'legacy.cancel_requested': 'Annulation demandée',
 'legacy.cancelling': 'Annulation…',
 'legacy.case_sensitive': 'Sensible à la casse',
 'legacy.change_history': 'Historique des modifications',
 'legacy.changed': 'Modifié',
 'legacy.changed_files': 'Fichiers modifiés',
 'legacy.check': 'Vérifier',
 'legacy.checking': 'Vérification…',
 'legacy.chroma_destination': 'Destination Chroma',
 'legacy.chroma_sync': 'Synchronisation Chroma',
 'legacy.citation': 'Citation',
 'legacy.citations': 'Citations',
 'legacy.claim_scope': 'Portée de l’énoncé',
 'legacy.cleaned_page_text': 'Texte de page nettoyé',
 'legacy.clear': 'Effacer',
 'legacy.clear_cache': 'Vider la mémoire cache',
 'legacy.clear_instructions': 'Effacer les instructions',
 'legacy.clear_past_results': 'Effacer les résultats précédents',
 'legacy.clear_record': 'Effacer la fiche',
 'legacy.clear_search': 'Effacer la recherche',
 'legacy.clear_selection': 'Effacer la sélection',
 'legacy.close': 'Fermer',
 'legacy.close_preview': 'Fermer l’aperçu',
 'legacy.collapse_all': 'Tout réduire',
 'legacy.collection': 'Collection',
 'legacy.collection_name': 'Nom de la collection',
 'legacy.columns': 'Colonnes',
 'legacy.condition': 'Condition',
 'legacy.configure_columns': 'Configurer les colonnes',
 'legacy.configured_model': 'Modèle configuré',
 'legacy.context': 'Contexte',
 'legacy.context_num_ctx': 'Contexte (num_ctx)',
 'legacy.copy_answer': 'Copier la réponse',
 'legacy.copy_entire_record': 'Copier toute la fiche',
 'legacy.cover_url': 'URL de la couverture',
 'legacy.create_collection': 'Créer une collection',
 'legacy.create_download': 'Créer et télécharger',
 'legacy.create_subset_tab': 'Créer un onglet de sous-ensemble',
 'legacy.created': 'Créé',
 'legacy.cross_encoder': 'Encodeur croisé',
 'legacy.cross_encoder_model': 'Modèle d’encodeur croisé',
 'legacy.current': 'Actuel',
 'legacy.current_file': 'Fichier actuel',
 'legacy.current_page_records': 'Fiches de la page actuelle',
 'legacy.current_pdf': 'PDF actuel',
 'legacy.default_reranker': 'Reclasseur par défaut',
 'legacy.default_run_mode': 'Mode d’exécution par défaut',
 'legacy.delete': 'Supprimer',
 'legacy.desktop_notifications': 'Notifications du bureau',
 'legacy.details': 'Détails',
 'legacy.details_timeline': 'Détails / chronologie',
 'legacy.differences': 'Différences',
 'legacy.direct_quote': 'Citation directe',
 'legacy.discourse': 'Discours',
 'legacy.discovered': 'Découvert',
 'legacy.discovered_model': 'Modèle découvert',
 'legacy.discovered_models': 'Modèles découverts',
 'legacy.dismiss': 'Fermer',
 'legacy.document_author': 'Auteur du document',
 'legacy.document_language': 'Langue du document',
 'legacy.document_languages': 'Langues des documents',
 'legacy.document_title': 'Titre du document',
 'legacy.edit_chroma_record': 'Modifier la fiche Chroma',
 'legacy.edit_record': 'Modifier la fiche',
 'legacy.edit_work_metadata': 'Modifier les métadonnées de l’œuvre',
 'legacy.embedding': 'Plongement vectoriel',
 'legacy.endpoint': 'Point de terminaison',
 'legacy.english': 'Anglais',
 'legacy.evidence': 'Preuves',
 'legacy.evidence_selected': 'Preuve sélectionnée',
 'legacy.expand_all': 'Tout développer',
 'legacy.export_jsonl': 'Exporter en JSONL',
 'legacy.expression': 'Expression',
 'legacy.extract_all_text': 'Extraire tout le texte',
 'legacy.extract_page_text': 'Extraire le texte de la page',
 'legacy.extracted_text': 'Texte extrait',
 'legacy.extraction_quality': 'Qualité de l’extraction',
 'legacy.failed': 'échec',
 'legacy.field': 'Champ',
 'legacy.fields_changed': 'champs modifiés',
 'legacy.fields_compared': 'champs comparés',
 'legacy.filter': 'Filtrer',
 'legacy.filter_models': 'Filtrer les modèles…',
 'legacy.filter_value': 'Valeur du filtre',
 'legacy.finished': 'Terminé',
 'legacy.first': 'Premier',
 'legacy.forward': 'Suivant →',
 'legacy.french': 'Français',
 'legacy.full_citation': 'Citation complète',
 'legacy.full_cite': 'Citation complète',
 'legacy.generation': 'Génération',
 'legacy.generation_model': 'Modèle de génération',
 'legacy.graded': 'évalué',
 'legacy.grouped_conditions': 'Conditions groupées',
 'legacy.identical_fields': 'champs identiques',
 'legacy.inline': 'Dans le texte',
 'legacy.inline_citation': 'Citation dans le texte',
 'legacy.inline_cite': 'Citation dans le texte',
 'legacy.instructions': 'Instructions',
 'legacy.interactive_foreground': 'Premier plan interactif',
 'legacy.jsonl_destination': 'Destination JSONL',
 'legacy.jsonl_tabs': 'Onglets JSONL',
 'legacy.last': 'Dernier',
 'legacy.lexical_vector_fallback': 'Solution de rechange lexicale/vectorielle',
 'legacy.linked_records': 'fiches liées',
 'legacy.linked_works': 'œuvres liées',
 'legacy.llm_proposals': 'Propositions du LLM',
 'legacy.llm_providers': 'Fournisseurs LLM',
 'legacy.llm_providers_2': 'Fournisseurs LLM',
 'legacy.loaded_records': 'fiches chargées',
 'legacy.loading_view': 'Chargement de la vue',
 'legacy.make_default': 'Définir par défaut',
 'legacy.manual': 'Manuel',
 'legacy.manual_model_id': 'Identifiant manuel du modèle',
 'legacy.match_all_and': 'Correspondre à TOUTES (ET)',
 'legacy.match_any_or': 'Correspondre à AU MOINS UNE (OU)',
 'legacy.max_output': 'Sortie maximale',
 'legacy.max_output_tokens': 'Nombre maximal de jetons de sortie',
 'legacy.merge_jsonl_tabs': 'Fusionner les onglets JSONL',
 'legacy.merged_file_name': 'Nom du fichier fusionné',
 'legacy.metadata': 'Métadonnées',
 'legacy.metadata_output': 'Sortie des métadonnées',
 'legacy.mmr_fetch_k': 'Bassin MMR (fetch_k)',
 'legacy.mmr_lambda': 'Lambda MMR',
 'legacy.model_kind': 'Type de modèle',
 'legacy.model_kind_filter': 'Filtre du type de modèle',
 'legacy.model_mode': 'Mode du modèle',
 'legacy.model_name': 'Nom du modèle',
 'legacy.model_readiness': 'État de préparation du modèle',
 'legacy.model_size': 'Taille du modèle',
 'legacy.more_text_tools': 'Autres outils de texte',
 'legacy.needs_review': 'À réviser',
 'legacy.needs_review_records': 'Fiches à réviser',
 'legacy.new_value': 'Nouvelle valeur',
 'legacy.newer': 'Plus récent →',
 'legacy.next': 'Suivant',
 'legacy.next_2': 'Suivant →',
 'legacy.no': 'Non',
 'legacy.no_data': 'Aucune donnée',
 'legacy.no_database': 'Aucune base de données',
 'legacy.no_matches': 'Aucune correspondance',
 'legacy.no_reranking': 'Aucun reclassement',
 'legacy.none_reported': 'Aucun élément signalé.',
 'legacy.notice': 'Avis',
 'legacy.ocr_text': 'ROC / texte',
 'legacy.offline': 'Hors ligne',
 'legacy.older': '← Plus ancien',
 'legacy.ollama_endpoint': 'Point de terminaison Ollama',
 'legacy.on_this_page': 'sur cette page',
 'legacy.online': 'En ligne',
 'legacy.open_dashboard': 'Ouvrir l’accueil',
 'legacy.open_full_details': 'Ouvrir tous les détails',
 'legacy.open_in_faq': 'Ouvrir dans la FAQ',
 'legacy.open_library': 'Ouvrir la bibliothèque',
 'legacy.open_pdf_explorer': 'Ouvrir l’explorateur PDF',
 'legacy.open_result': 'Ouvrir le résultat',
 'legacy.openai_compatible_endpoint': 'Point de terminaison compatible avec OpenAI',
 'legacy.operation_timeline': 'Chronologie de l’opération',
 'legacy.original_language': 'Langue originale',
 'legacy.original_title': 'Titre original',
 'legacy.other_fields': 'Autres champs',
 'legacy.page': 'Page',
 'legacy.page_end': 'Dernière page',
 'legacy.page_start': 'Première page',
 'legacy.page_text': 'Texte de la page',
 'legacy.pages': 'Pages',
 'legacy.pdf_document': 'Document PDF',
 'legacy.pdf_explorer': 'Explorateur PDF',
 'legacy.pdf_file': 'Fichier PDF',
 'legacy.pdf_links': 'Liens PDF',
 'legacy.pdf_page': 'Page PDF',
 'legacy.pdf_pages': 'Pages PDF',
 'legacy.pending': 'En attente',
 'legacy.pipeline_timings': 'Durées du pipeline',
 'legacy.precomputed_vectors': 'Vecteurs précalculés',
 'legacy.preview_record': 'Aperçu de la fiche',
 'legacy.previous': 'Précédent',
 'legacy.previous_2': '← Précédent',
 'legacy.primary_text': 'Texte principal',
 'legacy.profiles': 'profils',
 'legacy.progress': 'Progression',
 'legacy.proposed': 'Proposé',
 'legacy.proposed_change': 'modification proposée',
 'legacy.provider_model': 'Fournisseur / modèle',
 'legacy.provider_profile': 'Profil fournisseur',
 'legacy.provider_profiles': 'Profils fournisseurs',
 'legacy.publication_place': 'Lieu de publication',
 'legacy.publication_year': 'Année de publication',
 'legacy.publisher': 'Maison d’édition',
 'legacy.quantization': 'Quantification',
 'legacy.query_decomposition': 'Décomposition de la requête',
 'legacy.question': 'Question',
 'legacy.question_prompt': 'Question / invite',
 'legacy.queued': 'En attente',
 'legacy.quotation_chain': 'Chaîne de citations',
 'legacy.quotation_provenance': 'Provenance des citations',
 'legacy.quoted_addressee': 'Destinataire cité',
 'legacy.quoted_author': 'Auteur cité',
 'legacy.quoted_referent': 'Référent cité',
 'legacy.quoted_work': 'Œuvre citée',
 'legacy.rag_pipeline': 'Pipeline RAG',
 'legacy.rag_result': 'Résultat RAG',
 'legacy.rationale': 'Justification',
 'legacy.ready': 'Prêt',
 'legacy.reasoning': 'Raisonnement',
 'legacy.record': 'Fiche',
 'legacy.record_actions': 'Actions sur la fiche',
 'legacy.record_annotation': 'Annotation de fiche',
 'legacy.record_comparison': 'Comparaison de fiches',
 'legacy.record_history': 'Historique de la fiche',
 'legacy.record_preview': 'Aperçu de la fiche',
 'legacy.records': 'fiches',
 'legacy.records_to_sync': 'Fiches à synchroniser',
 'legacy.region_author': 'Auteur de la région',
 'legacy.region_type': 'Type de région',
 'legacy.reject_selected': 'Rejeter la sélection',
 'legacy.rejected_fields': 'champs rejetés',
 'legacy.rejected_results': 'résultats rejetés',
 'legacy.remove': 'Supprimer',
 'legacy.remove_condition': 'Supprimer la condition',
 'legacy.remove_evidence': 'Retirer la preuve',
 'legacy.remove_filter': 'Supprimer le filtre',
 'legacy.remove_from_queue': 'Retirer de la file',
 'legacy.remove_group': 'Supprimer le groupe',
 'legacy.remove_work': 'Retirer l’œuvre',
 'legacy.request_configuration': 'Configuration de la requête',
 'legacy.rerank_top_n': 'Reclasser les N premiers',
 'legacy.reranker': 'Reclasseur',
 'legacy.researcher_access': 'Accès des chercheurs',
 'legacy.reset_defaults': 'Rétablir les valeurs par défaut',
 'legacy.response_faq': 'FAQ des réponses',
 'legacy.response_language': 'Langue de la réponse',
 'legacy.responses': 'réponses',
 'legacy.restore_original': 'Rétablir l’original',
 'legacy.result_summary': 'Résumé du résultat',
 'legacy.retrieval_diagnostics': 'Diagnostics de repérage',
 'legacy.retrieval_k': 'k de repérage',
 'legacy.retrieval_routes': 'Voies de repérage',
 'legacy.review': 'Réviser',
 'legacy.review_behavior': 'Comportement de révision',
 'legacy.review_failed': 'Échec de la révision',
 'legacy.review_preset': 'Préréglage de révision',
 'legacy.review_reason': 'Motif de révision',
 'legacy.review_results': 'Résultats de la révision',
 'legacy.review_status': 'État de la révision',
 'legacy.reviewed': 'Révisé',
 'legacy.reviewing': 'Révision',
 'legacy.rotate_left_90': 'Rotation de 90° à gauche',
 'legacy.rotate_right_90': 'Rotation de 90° à droite',
 'legacy.run_in_background': 'Exécuter en arrière-plan',
 'legacy.run_in_foreground': 'Exécuter au premier plan',
 'legacy.run_review': 'Lancer la révision',
 'legacy.running': 'En cours…',
 'legacy.save_columns': 'Enregistrer les colonnes',
 'legacy.search_page_text': 'Rechercher dans le texte de la page',
 'legacy.secondary_text': 'Texte secondaire',
 'legacy.select_all': 'Tout sélectionner',
 'legacy.select_metadata': 'Sélectionner les métadonnées',
 'legacy.select_none': 'Tout désélectionner',
 'legacy.selected_evidence': 'preuves sélectionnées',
 'legacy.selected_records': 'Fiches sélectionnées',
 'legacy.selected_value': 'Valeur sélectionnée',
 'legacy.selection_mode': 'Mode de sélection',
 'legacy.semantic_classification_confidence': 'Fiabilité de la classification sémantique',
 'legacy.semantic_function': 'Fonction sémantique',
 'legacy.semantics': 'Sémantique',
 'legacy.short_title': 'Titre abrégé',
 'legacy.source': 'Source',
 'legacy.source_collection': 'Collection source',
 'legacy.start_operation': 'Lancer l’opération',
 'legacy.started': 'Démarré',
 'legacy.started_by': 'Lancé par',
 'legacy.status': 'État',
 'legacy.status_error': 'Erreur d’état',
 'legacy.summary': 'Résumé',
 'legacy.target_records': 'Fiches ciblées',
 'legacy.temperature': 'Température',
 'legacy.text': 'Texte',
 'legacy.text_length': 'Longueur du texte',
 'legacy.this_version': 'Cette version',
 'legacy.traditional_search': 'Recherche traditionnelle',
 'legacy.translation': 'Traduction',
 'legacy.translator': 'Traducteur',
 'legacy.unavailable': 'Indisponible',
 'legacy.unknown': 'Inconnu',
 'legacy.untitled_question': 'Question sans titre',
 'legacy.use_model': 'Utiliser le modèle',
 'legacy.value': 'Valeur',
 'legacy.values': 'Valeurs',
 'legacy.verify_carefully': 'vérifier attentivement',
 'legacy.viewer_configuration': 'Configuration du visualiseur',
 'legacy.waiting_in_queue': 'En attente dans la file.',
 'legacy.warm': 'Préchauffé',
 'legacy.warming': 'Préchauffage',
 'legacy.warmup_failed': 'Échec du préchauffage',
 'legacy.words': 'mots',
 'legacy.works': 'œuvres',
 'legacy.works_and_records': 'Œuvres et fiches',
 'legacy.works_cited': 'Ouvrages cités',
 'legacy.works_referenced': 'Œuvres citées',
 'legacy.yes': 'Oui',
 'operations.clear_finished': 'Effacer les opérations terminées',
 'operations.large_sync_foreground_help': '{count} fiches seront synchronisées par lots au premier plan afin que le '
                                          'navigateur demeure réactif. Gardez cet onglet DerridAI ouvert jusqu’à la '
                                          'fin.',
 'record.full_citation': 'Citation complète',
 'record.inline_citation': 'Citation dans le texte',
 'research.evidence_citations_help': 'Contrôlez la taille du paquet de preuves et la liaison déterministe aux sources.',
 'research.generation_override_help': 'Dérogations facultatives pour cette exécution; le profil fournisseur enregistré '
                                      'demeure inchangé.',
 'research.lambda_help': 'Équilibre entre pertinence et diversité',
 'research.lexical_fallback': 'Solution de rechange lexicale/vectorielle',
 'research.no_evidence_text': 'Aucun passage n’a été conservé pour cet élément de preuve.',
 'research.no_selected_evidence': 'Aucune preuve épinglée',
 'research.nucleus_sampling': 'Échantillonnage top-p',
 'research.page_kicker': 'Recherche fondée sur les preuves',
 'research.pipeline_running_one': 'pipeline en cours',
 'research.pipelines_running_many': 'pipelines en cours',
 'research.position_holder': 'Détenteur de la position',
 'research.provider_options_help': 'Les options avancées propres au fournisseur s’appliquent uniquement à cette '
                                   'exécution.',
 'research.retrieval_nav_help': 'Routage, profondeur du bassin de candidats et reclassement',
 'research.settings_reproducibility_note': 'Ces valeurs sont enregistrées avec chaque exécution afin que l’analyse '
                                           'puisse être reproduite ultérieurement.',
 'research.source_binding_help': 'Assurez la traçabilité des affirmations générées au moyen d’identifiants de preuve '
                                 'et de citations déterministes.',
 'research.top_k_sampling': 'Échantillonnage top-k'})


# 0.35.0 — complete translation coverage for long compatibility-view help text.
DEFAULT_EN_US.update({'legacy.help.a_full_backup_can_contain_provider_api_keys_store_backup_zip_files_securely_installed_ollama_mo': 'A '
                                                                                                                'full '
                                                                                                                'backup '
                                                                                                                'can '
                                                                                                                'contain '
                                                                                                                'provider '
                                                                                                                'API '
                                                                                                                'keys. '
                                                                                                                'Store '
                                                                                                                'backup '
                                                                                                                'ZIP '
                                                                                                                'files '
                                                                                                                'securely. '
                                                                                                                'Installed '
                                                                                                                'Ollama '
                                                                                                                'model '
                                                                                                                'files '
                                                                                                                'and '
                                                                                                                'Docker '
                                                                                                                'images '
                                                                                                                'are '
                                                                                                                'not '
                                                                                                                'copied.',
 'legacy.help.add_at_least_one_condition': 'Add at least one condition.',
 'legacy.help.additional_options_json': 'Additional options JSON',
 'legacy.help.advanced_ollama_options_json': 'Advanced Ollama options JSON',
 'legacy.help.advanced_openai_compatible_options_json': 'Advanced OpenAI-compatible options JSON',
 'legacy.help.advanced_options_json': 'Advanced options JSON',
 'legacy.help.advanced_provider_options': 'Advanced provider options',
 'legacy.help.all_cached_responses_were_processed': 'All cached responses were processed.',
 'legacy.help.all_files_separately': 'All files separately',
 'legacy.help.all_loaded_jsonl_files': 'All loaded JSONL files',
 'legacy.help.allow_researcher_accounts_to_use_this_profile_for_research_without_exposing_credentials_or_prov': 'Allow '
                                                                                                                'researcher '
                                                                                                                'accounts '
                                                                                                                'to '
                                                                                                                'use '
                                                                                                                'this '
                                                                                                                'profile '
                                                                                                                'for '
                                                                                                                'Research '
                                                                                                                'without '
                                                                                                                'exposing '
                                                                                                                'credentials '
                                                                                                                'or '
                                                                                                                'provider '
                                                                                                                'administration.',
 'legacy.help.also_remove_from_chroma': 'Also remove from Chroma',
 'legacy.help.an_administrator_must_create_or_restore_a_corpus_vector_database_before_researcher_search_and_r': 'An '
                                                                                                                'administrator '
                                                                                                                'must '
                                                                                                                'create '
                                                                                                                'or '
                                                                                                                'restore '
                                                                                                                'a '
                                                                                                                'corpus '
                                                                                                                'vector '
                                                                                                                'database '
                                                                                                                'before '
                                                                                                                'researcher '
                                                                                                                'search '
                                                                                                                'and '
                                                                                                                'RAG '
                                                                                                                'can '
                                                                                                                'be '
                                                                                                                'used.',
 'legacy.help.api_keys_are_intentionally_omitted': 'API keys are intentionally omitted.',
 'legacy.help.apply_one_field_value_consistently_across_a_selected_record_set_every_actual_change_is_audited': 'Apply '
                                                                                                               'one '
                                                                                                               'field '
                                                                                                               'value '
                                                                                                               'consistently '
                                                                                                               'across '
                                                                                                               'a '
                                                                                                               'selected '
                                                                                                               'record '
                                                                                                               'set. '
                                                                                                               'Every '
                                                                                                               'actual '
                                                                                                               'change '
                                                                                                               'is '
                                                                                                               'audited.',
 'legacy.help.ask_a_research_question_about_derrida': 'Ask a research question about Derrida…',
 'legacy.help.ask_an_administrator_to_create_or_populate_a_corpus_vector_database': 'Ask an administrator to create or '
                                                                                    'populate a corpus vector '
                                                                                    'database.',
 'legacy.help.auto_grade_final_response_as_the_last_pipeline_step': 'Auto-grade final response as the last pipeline '
                                                                    'step',
 'legacy.help.auto_grade_provider_profile': 'Auto-grade provider profile',
 'legacy.help.auto_grade_the_final_rag_response_after_caching': 'Auto-grade the final RAG response after caching',
 'legacy.help.auto_improve_pass_in_progress': 'Auto-improve pass in progress',
 'legacy.help.autocomplete_searches_record_ids_works_authors_and_source_files_without_rendering_an_enormous_s': 'Autocomplete '
                                                                                                                'searches '
                                                                                                                'record '
                                                                                                                'IDs, '
                                                                                                                'works, '
                                                                                                                'authors, '
                                                                                                                'and '
                                                                                                                'source '
                                                                                                                'files '
                                                                                                                'without '
                                                                                                                'rendering '
                                                                                                                'an '
                                                                                                                'enormous '
                                                                                                                'select '
                                                                                                                'menu.',
 'legacy.help.automatic_pipeline_grade': 'Automatic pipeline grade',
 'legacy.help.browse_summarized_records': 'Browse summarized records',
 'legacy.help.browser_permission_is_required_notifications_are_local_browser_notifications': 'Browser permission is '
                                                                                             'required. Notifications '
                                                                                             'are local browser '
                                                                                             'notifications.',
 'legacy.help.build_explicit_boolean_groups_such_as_a_and_b_and_c_or_d_or_e_and_f': 'Build explicit boolean groups '
                                                                                    'such as A AND B AND (C OR D OR E) '
                                                                                    'AND F.',
 'legacy.help.bulk_edit_one_field': 'Bulk edit one field',
 'legacy.help.cached_rag_responses': 'cached RAG responses',
 'legacy.help.changed_aggregate': 'Changed + aggregate',
 'legacy.help.changes_stay_local_until_you_export_or_upsert_them': 'Changes stay local until you export or upsert '
                                                                   'them.',
 'legacy.help.checking_configured_llm_provider': 'Checking configured LLM provider…',
 'legacy.help.choose_any_subset_the_selected_source_tabs_will_be_replaced_in_the_workspace_by_the_merged_tab': 'Choose '
                                                                                                               'any '
                                                                                                               'subset. '
                                                                                                               'The '
                                                                                                               'selected '
                                                                                                               'source '
                                                                                                               'tabs '
                                                                                                               'will '
                                                                                                               'be '
                                                                                                               'replaced '
                                                                                                               'in the '
                                                                                                               'workspace '
                                                                                                               'by the '
                                                                                                               'merged '
                                                                                                               'tab.',
 'legacy.help.choose_discovered_model': 'Choose discovered model',
 'legacy.help.choose_the_grading_provider_model_in_the_rag_runner': 'Choose the grading provider/model in the RAG '
                                                                    'runner.',
 'legacy.help.clean_current_page_text': 'Clean current page text',
 'legacy.help.clear_column_filters': 'Clear column filters',
 'legacy.help.clear_remembered_questions': 'Clear remembered questions',
 'legacy.help.completed_rag_runs_will_be_cached_automatically_and_appear_here': 'Completed RAG runs will be cached '
                                                                                'automatically and appear here.',
 'legacy.help.conservative_ligature_zero_width_character_and_broken_line_hyphen_cleanup_no_paraphrasing': 'Conservative '
                                                                                                          'ligature, '
                                                                                                          'zero-width '
                                                                                                          'character, '
                                                                                                          'and broken '
                                                                                                          'line-hyphen '
                                                                                                          'cleanup. No '
                                                                                                          'paraphrasing.',
 'legacy.help.copy_entire_record_json': 'Copy entire record JSON',
 'legacy.help.corpus_chroma_collections': 'corpus Chroma collections',
 'legacy.help.could_not_load_response_faq': 'Could not load Response FAQ.',
 'legacy.help.could_not_read_response_cache': 'Could not read response cache.',
 'legacy.help.could_not_render_this_item': 'Could not render this item.',
 'legacy.help.create_draft_record': 'Create draft record',
 'legacy.help.create_jsonl_subset': 'Create JSONL subset',
 'legacy.help.create_or_restore_a_corpus_vector_database_before_upserting_pdf_drafts': 'Create or restore a corpus '
                                                                                       'vector database before '
                                                                                       'upserting PDF drafts.',
 'legacy.help.current_chroma_path': 'Current Chroma path',
 'legacy.help.decomposition_max_tokens': 'Decomposition max tokens',
 'legacy.help.default_embedding_model': 'Default embedding model',
 'legacy.help.default_embedding_provider': 'Default embedding provider',
 'legacy.help.default_provider_profile': 'Default provider profile',
 'legacy.help.default_review_preset': 'Default review preset',
 'legacy.help.delete_audit_history': 'Delete audit history…',
 'legacy.help.deletes_all_loaded_browser_jsonl_workspace_data_and_every_collection_in_the_current_chroma_pers': 'Deletes '
                                                                                                                'all '
                                                                                                                'loaded '
                                                                                                                'browser '
                                                                                                                'JSONL '
                                                                                                                'workspace '
                                                                                                                'data '
                                                                                                                'and '
                                                                                                                'every '
                                                                                                                'collection '
                                                                                                                'in '
                                                                                                                'the '
                                                                                                                'current '
                                                                                                                'Chroma '
                                                                                                                'persistence '
                                                                                                                'database. '
                                                                                                                'Installed '
                                                                                                                'model '
                                                                                                                'files '
                                                                                                                'are '
                                                                                                                'not '
                                                                                                                'deleted.',
 'legacy.help.do_not_add_to_jsonl': 'Do not add to JSONL',
 'legacy.help.download_merged_jsonl_immediately': 'Download merged JSONL immediately',
 'legacy.help.draft_record_from_pdf_page': 'Draft record from PDF page',
 'legacy.help.drafts_persist_across_navigation_and_browser_refresh_the_40_most_recent_submitted_question_inst': 'Drafts '
                                                                                                                'persist '
                                                                                                                'across '
                                                                                                                'navigation '
                                                                                                                'and '
                                                                                                                'browser '
                                                                                                                'refresh. '
                                                                                                                'The '
                                                                                                                '40 '
                                                                                                                'most '
                                                                                                                'recent '
                                                                                                                'submitted '
                                                                                                                'question/instruction '
                                                                                                                'pairs '
                                                                                                                'are '
                                                                                                                'retained '
                                                                                                                'locally.',
 'legacy.help.drop_one_or_more_jsonl_files_anywhere_on_this_page_or_choose_files_manually_each_file_stays_in_': 'Drop '
                                                                                                                'one '
                                                                                                                'or '
                                                                                                                'more '
                                                                                                                'JSONL '
                                                                                                                'files '
                                                                                                                'anywhere '
                                                                                                                'on '
                                                                                                                'this '
                                                                                                                'page, '
                                                                                                                'or '
                                                                                                                'choose '
                                                                                                                'files '
                                                                                                                'manually. '
                                                                                                                'Each '
                                                                                                                'file '
                                                                                                                'stays '
                                                                                                                'in '
                                                                                                                'its '
                                                                                                                'own '
                                                                                                                'tab '
                                                                                                                'and '
                                                                                                                'can '
                                                                                                                'be '
                                                                                                                'edited, '
                                                                                                                'compared, '
                                                                                                                'searched, '
                                                                                                                'exported, '
                                                                                                                'or '
                                                                                                                'sent '
                                                                                                                'to '
                                                                                                                'ChromaDB.',
 'legacy.help.each_action_lets_you_choose_provider_model_parameters_and_run_mode': 'Each action lets you choose '
                                                                                   'provider, model, parameters, and '
                                                                                   'run mode.',
 'legacy.help.each_cache_record_stores_the_original_rag_query_instructions_run_parameters_answer_evidence_ret': 'Each '
                                                                                                                'cache '
                                                                                                                'record '
                                                                                                                'stores '
                                                                                                                'the '
                                                                                                                'original '
                                                                                                                'RAG '
                                                                                                                'query, '
                                                                                                                'instructions, '
                                                                                                                'run '
                                                                                                                'parameters, '
                                                                                                                'answer, '
                                                                                                                'evidence, '
                                                                                                                'retrieval '
                                                                                                                'diagnostics, '
                                                                                                                'timings, '
                                                                                                                'and '
                                                                                                                'all '
                                                                                                                'saved '
                                                                                                                'LLM '
                                                                                                                'grading '
                                                                                                                'runs.',
 'legacy.help.enter_the_new_value_arrays_objects_use_json_enter_null_for_null': 'Enter the new value. Arrays/objects '
                                                                                'use JSON. Enter __NULL__ for null.',
 'legacy.help.evidence_retrieval_and_pipeline_details': 'Evidence, retrieval, and pipeline details',
 'legacy.help.expand_all_ui_panels': 'Expand all UI panels',
 'legacy.help.expand_navigation_sidebar': 'Expand navigation sidebar',
 'legacy.help.filter_linked_records': 'Filter linked records',
 'legacy.help.five_most_recent_runs': 'Five most recent runs',
 'legacy.help.freellm_openai_model_selection': 'FreeLLM / OpenAI model selection',
 'legacy.help.generation_defaults_advanced_parameters': 'Generation defaults & advanced parameters',
 'legacy.help.latest_100_response_cache_entries_use_response_faq_for_full_answer_evidence_browsing_and_re_run': 'Latest '
                                                                                                                '100 '
                                                                                                                'response-cache '
                                                                                                                'entries. '
                                                                                                                'Use '
                                                                                                                'Response '
                                                                                                                'FAQ '
                                                                                                                'for '
                                                                                                                'full '
                                                                                                                'answer/evidence '
                                                                                                                'browsing '
                                                                                                                'and '
                                                                                                                're-runs.',
 'legacy.help.llm_query_decomposition_french_query_formulation': 'LLM query decomposition + French query formulation',
 'legacy.help.llm_review_workspace': 'LLM Review Workspace',
 'legacy.help.load_this_pdf_in_pdf_explorer_first': 'Load this PDF in PDF Explorer first',
 'legacy.help.local_record_changed_since_job_started': 'local record changed since job started',
 'legacy.help.match_link_page_to_record': 'Match & link page to record',
 'legacy.help.max_chars_evidence_record': 'Max chars / evidence record',
 'legacy.help.merge_and_replace_selected_tabs': 'Merge and replace selected tabs',
 'legacy.help.mixed_across_records': 'mixed across records',
 'legacy.help.model_selection_mode': 'Model selection mode',
 'legacy.help.new_jsonl_tab_name': 'New JSONL tab name',
 'legacy.help.no_answer_returned': 'No answer returned.',
 'legacy.help.no_audit_history_recorded': 'No audit history recorded.',
 'legacy.help.no_background_operations_yet': 'No background operations yet.',
 'legacy.help.no_cached_responses_yet': 'No cached responses yet.',
 'legacy.help.no_changes_proposed': 'No changes proposed.',
 'legacy.help.no_corpus_chroma_collections': 'No corpus Chroma collections',
 'legacy.help.no_events_recorded': 'No events recorded.',
 'legacy.help.no_evidence_returned': 'No evidence returned.',
 'legacy.help.no_evidence_selected_yet_use_add_to_evidence_on_record_search_rows': 'No evidence selected yet. Use “Add '
                                                                                   'to evidence” on record/search '
                                                                                   'rows.',
 'legacy.help.no_full_evidence_retained': 'No full evidence retained.',
 'legacy.help.no_linked_records_match_this_filter': 'No linked records match this filter.',
 'legacy.help.no_llm_provider_profiles_configured': 'No LLM provider profiles configured.',
 'legacy.help.no_matching_records': 'No matching records',
 'legacy.help.no_matching_records_2': 'No matching records.',
 'legacy.help.no_models_match_this_filter': 'No models match this filter.',
 'legacy.help.no_pdf_pages_linked_to_this_record': 'No PDF pages linked to this record.',
 'legacy.help.no_rag_jobs_yet_start_one_below': 'No RAG jobs yet. Start one below.',
 'legacy.help.no_rag_pipeline_runs_recorded_yet': 'No RAG pipeline runs recorded yet.',
 'legacy.help.no_record_selected': 'No record selected.',
 'legacy.help.no_records_linked_to_this_page_yet': 'No records linked to this page yet.',
 'legacy.help.no_records_match_the_current_filters': 'No records match the current filters.',
 'legacy.help.no_records_match_this_work': 'No records match this work.',
 'legacy.help.no_visible_columns': 'No visible columns.',
 'legacy.help.nuke_derridai_workspace': 'NUKE DerridAI workspace',
 'legacy.help.ocr_text_cleanup': 'OCR / text cleanup',
 'legacy.help.on_when_background_operations_finish': 'On when background operations finish',
 'legacy.help.only_modify_records_whose_value_actually_differs': 'Only modify records whose value actually differs',
 'legacy.help.open_a_corpus_workspace': 'Open a corpus workspace',
 'legacy.help.open_a_pdf_to_render_pages_read_its_embedded_title_metadata_extract_text_and_move_directly_betw': 'Open '
                                                                                                                'a PDF '
                                                                                                                'to '
                                                                                                                'render '
                                                                                                                'pages, '
                                                                                                                'read '
                                                                                                                'its '
                                                                                                                'embedded '
                                                                                                                'title '
                                                                                                                'metadata, '
                                                                                                                'extract '
                                                                                                                'text, '
                                                                                                                'and '
                                                                                                                'move '
                                                                                                                'directly '
                                                                                                                'between '
                                                                                                                'linked '
                                                                                                                'PDF '
                                                                                                                'pages '
                                                                                                                'and '
                                                                                                                'corpus '
                                                                                                                'records.',
 'legacy.help.open_a_source_pdf': 'Open a source PDF',
 'legacy.help.openai_compatible_freellm': 'OpenAI-compatible / FreeLLM',
 'legacy.help.optional_constraints_on_the_answer_kept_separate_from_the_research_question': 'Optional constraints on '
                                                                                            'the answer; kept separate '
                                                                                            'from the research '
                                                                                            'question.',
 'legacy.help.optional_instructions_applied_to_every_record_in_this_batch': 'Optional instructions applied to every '
                                                                            'record in this batch.',
 'legacy.help.parentheses_evaluate_this_block_as_one_boolean_value': 'Parentheses: evaluate this block as one boolean '
                                                                     'value',
 'legacy.help.pipeline_query_metadata': 'Pipeline query metadata',
 'legacy.help.preview_this_version': 'Preview this version',
 'legacy.help.proposals_are_intentionally_hidden_until_every_queued_record_has_been_processed': 'Proposals are '
                                                                                                'intentionally hidden '
                                                                                                'until every queued '
                                                                                                'record has been '
                                                                                                'processed.',
 'legacy.help.proposed_changes_for_this_record': 'Proposed changes for this record',
 'legacy.help.provider_choice_default_review_preset_and_whether_llm_review_opens_interactively_or_runs_as_a_b': 'Provider '
                                                                                                                'choice, '
                                                                                                                'default '
                                                                                                                'review '
                                                                                                                'preset, '
                                                                                                                'and '
                                                                                                                'whether '
                                                                                                                'LLM '
                                                                                                                'review '
                                                                                                                'opens '
                                                                                                                'interactively '
                                                                                                                'or '
                                                                                                                'runs '
                                                                                                                'as a '
                                                                                                                'background '
                                                                                                                'job.',
 'legacy.help.provider_endpoints_credentials_models_concurrency_limits_generation_defaults_readiness_and_inde': 'Provider '
                                                                                                                'endpoints, '
                                                                                                                'credentials, '
                                                                                                                'models, '
                                                                                                                'concurrency '
                                                                                                                'limits, '
                                                                                                                'generation '
                                                                                                                'defaults, '
                                                                                                                'readiness, '
                                                                                                                'and '
                                                                                                                'independent '
                                                                                                                'warmups '
                                                                                                                'are '
                                                                                                                'configured '
                                                                                                                'on '
                                                                                                                'the '
                                                                                                                'dedicated '
                                                                                                                'Providers '
                                                                                                                'page.',
 'legacy.help.query_decomposition_max_tokens': 'Query-decomposition max tokens',
 'legacy.help.question_instructions': 'Question & instructions',
 'legacy.help.rag_pipeline_activity': 'RAG pipeline activity',
 'legacy.help.rag_pipeline_defaults': 'RAG pipeline defaults',
 'legacy.help.rag_response_cache': 'RAG response cache',
 'legacy.help.rag_response_grade': 'RAG response grade',
 'legacy.help.raw_evidence_tagged_answer': 'Raw evidence-tagged answer',
 'legacy.help.recall_a_previous_question': 'Recall a previous question…',
 'legacy.help.recent_audit_history': 'Recent audit history',
 'legacy.help.recent_cached_responses': 'Recent cached responses',
 'legacy.help.recent_rag_pipelines': 'Recent RAG pipelines',
 'legacy.help.record_a_json_jsonl': 'Record A JSON / JSONL',
 'legacy.help.record_b_json_jsonl': 'Record B JSON / JSONL',
 'legacy.help.records_linked_anywhere_in_this_pdf': 'Records linked anywhere in this PDF',
 'legacy.help.records_selected_across_corpus_tables_are_pinned_into_this_run_you_can_also_bypass_retrieval_en': 'Records '
                                                                                                                'selected '
                                                                                                                'across '
                                                                                                                'corpus '
                                                                                                                'tables '
                                                                                                                'are '
                                                                                                                'pinned '
                                                                                                                'into '
                                                                                                                'this '
                                                                                                                'run. '
                                                                                                                'You '
                                                                                                                'can '
                                                                                                                'also '
                                                                                                                'bypass '
                                                                                                                'retrieval '
                                                                                                                'entirely '
                                                                                                                'and '
                                                                                                                'answer '
                                                                                                                'only '
                                                                                                                'from '
                                                                                                                'this '
                                                                                                                'evidence '
                                                                                                                'packet.',
 'legacy.help.remove_all_pdf_links': 'Remove all PDF links',
 'legacy.help.render_pages_extract_text_connect_pages_to_records_and_run_llm_assisted_source_workflows': 'Render '
                                                                                                         'pages, '
                                                                                                         'extract '
                                                                                                         'text, '
                                                                                                         'connect '
                                                                                                         'pages to '
                                                                                                         'records, and '
                                                                                                         'run '
                                                                                                         'LLM-assisted '
                                                                                                         'source '
                                                                                                         'workflows.',
 'legacy.help.request_notification_permission': 'Request notification permission',
 'legacy.help.research_question_prompt': 'Research question / prompt',
 'legacy.help.research_run_context': 'Research run context',
 'legacy.help.reset_table_columns': 'Reset table columns',
 'legacy.help.reset_ui_choices_or_remove_audit_history_without_deleting_records': 'Reset UI choices or remove audit '
                                                                                  'history without deleting records.',
 'legacy.help.restore_removed_upsert_queue_items': 'Restore removed upsert-queue items',
 'legacy.help.restore_this_version': 'Restore this version',
 'legacy.help.retrieval_fusion_reranking_evidence_budget_and_query_decomposition_defaults_per_run_generation_': 'Retrieval, '
                                                                                                                'fusion, '
                                                                                                                'reranking, '
                                                                                                                'evidence-budget, '
                                                                                                                'and '
                                                                                                                'query-decomposition '
                                                                                                                'defaults. '
                                                                                                                'Per-run '
                                                                                                                'generation '
                                                                                                                'parameters '
                                                                                                                'are '
                                                                                                                'also '
                                                                                                                'exposed '
                                                                                                                'on '
                                                                                                                'Research.',
 'legacy.help.review_add_draft': 'Review / add draft',
 'legacy.help.review_link_page': 'Review & link page',
 'legacy.help.same_model_grading_warning': 'Same-model grading warning.',
 'legacy.help.saved_to_response_faq_when_caching_succeeds': 'Saved to Response FAQ when caching succeeds.',
 'legacy.help.saved_with_the_cached_rag_query_when_a_response_cache_record_is_available': 'Saved with the cached RAG '
                                                                                          'query when a response-cache '
                                                                                          'record is available.',
 'legacy.help.saving_updates_this_record_in_place_under_the_same_chroma_id_and_regenerates_its_embedding_when': 'Saving '
                                                                                                                'updates '
                                                                                                                'this '
                                                                                                                'record '
                                                                                                                'in '
                                                                                                                'place '
                                                                                                                'under '
                                                                                                                'the '
                                                                                                                'same '
                                                                                                                'Chroma '
                                                                                                                'ID '
                                                                                                                'and '
                                                                                                                'regenerates '
                                                                                                                'its '
                                                                                                                'embedding '
                                                                                                                'when '
                                                                                                                'the '
                                                                                                                'configured '
                                                                                                                'embedding '
                                                                                                                'provider '
                                                                                                                'allows '
                                                                                                                'it.',
 'legacy.help.search_cached_questions': 'Search cached questions',
 'legacy.help.search_text_in_this_file': 'Search text in this file',
 'legacy.help.select_all_changes': 'Select all changes',
 'legacy.help.select_all_results': 'Select all results',
 'legacy.help.select_or_create_a_corpus_vector_database_first': 'Select or create a corpus vector database first.',
 'legacy.help.select_or_paste_two_records_to_compare_them': 'Select or paste two records to compare them.',
 'legacy.help.select_record_changes': 'Select record changes',
 'legacy.help.select_two_records': 'Select two records',
 'legacy.help.select_visible_records': 'Select visible records',
 'legacy.help.selected_evidence_only_retrieval_disabled': 'Selected evidence only · retrieval disabled',
 'legacy.help.start_from_scratch': 'Start from scratch',
 'legacy.help.start_typing_to_search_loaded_records': 'Start typing to search loaded records.',
 'legacy.help.stop_after_current': 'Stop after current',
 'legacy.help.switch_freely_between_interactive_review_background_review_and_aggregate_auto_improve_before_st': 'Switch '
                                                                                                                'freely '
                                                                                                                'between '
                                                                                                                'interactive '
                                                                                                                'review, '
                                                                                                                'background '
                                                                                                                'review, '
                                                                                                                'and '
                                                                                                                'aggregate '
                                                                                                                'Auto-improve '
                                                                                                                'before '
                                                                                                                'starting '
                                                                                                                'the '
                                                                                                                'run.',
 'legacy.help.system_cache_only_this_collection_is_intentionally_excluded_from_corpus_vector_stores_corpus_db': 'System '
                                                                                                                'cache '
                                                                                                                'only. '
                                                                                                                'This '
                                                                                                                'collection '
                                                                                                                'is '
                                                                                                                'intentionally '
                                                                                                                'excluded '
                                                                                                                'from '
                                                                                                                'corpus '
                                                                                                                'Vector '
                                                                                                                'Stores, '
                                                                                                                'corpus '
                                                                                                                'DB '
                                                                                                                'counts, '
                                                                                                                'language '
                                                                                                                'mirroring, '
                                                                                                                'and '
                                                                                                                'RAG '
                                                                                                                'source '
                                                                                                                'selection.',
 'legacy.help.text_review_runs_separately_so_output_stays_bounded': 'Text review runs separately so output stays '
                                                                    'bounded.',
 'legacy.help.these_records_are_identical_across_all_compared_fields': 'These records are identical across all '
                                                                       'compared fields.',
 'legacy.help.this_cannot_be_undone_unless_you_have_exported_backed_up_your_jsonl_and_chroma_data': 'This cannot be '
                                                                                                    'undone unless you '
                                                                                                    'have '
                                                                                                    'exported/backed '
                                                                                                    'up your JSONL and '
                                                                                                    'Chroma data.',
 'legacy.help.this_is_a_draft_generated_by_an_llm_review_attribution_page_metadata_quotation_provenance_and_t': 'This '
                                                                                                                'is a '
                                                                                                                'draft '
                                                                                                                'generated '
                                                                                                                'by an '
                                                                                                                'LLM. '
                                                                                                                'Review '
                                                                                                                'attribution, '
                                                                                                                'page '
                                                                                                                'metadata, '
                                                                                                                'quotation '
                                                                                                                'provenance, '
                                                                                                                'and '
                                                                                                                'text '
                                                                                                                'before '
                                                                                                                'saving.',
 'legacy.help.this_is_the_reconstructed_original_state_before_tracked_updates': 'This is the reconstructed original '
                                                                                'state before tracked updates.',
 'legacy.help.this_local_record_changed_after_the_llm_job_started_current_values_below_may_differ_from_the_va': 'This '
                                                                                                                'local '
                                                                                                                'record '
                                                                                                                'changed '
                                                                                                                'after '
                                                                                                                'the '
                                                                                                                'LLM '
                                                                                                                'job '
                                                                                                                'started. '
                                                                                                                'Current '
                                                                                                                'values '
                                                                                                                'below '
                                                                                                                'may '
                                                                                                                'differ '
                                                                                                                'from '
                                                                                                                'the '
                                                                                                                'values '
                                                                                                                'originally '
                                                                                                                'reviewed.',
 'legacy.help.this_setting_is_fixed_by_the_administrator_approved_researcher_profile': 'This setting is fixed by the '
                                                                                       'administrator-approved '
                                                                                       'researcher profile.',
 'legacy.help.top_level_and_or_plus_explicit_nested_groups': 'Top-level AND/OR plus explicit nested groups',
 'legacy.help.type_nuke_to_enable': 'Type NUKE to enable',
 'legacy.help.unlink_record_from_pdf': 'Unlink record from PDF',
 'legacy.help.use_as_current_page_text': 'Use as current page text',
 'legacy.help.use_extract_current_page_or_extract_all_text_if_both_pdf_js_and_pymupdf_find_no_text_the_page_l': 'Use '
                                                                                                                '“Extract '
                                                                                                                'current '
                                                                                                                'page” '
                                                                                                                'or '
                                                                                                                '“Extract '
                                                                                                                'all '
                                                                                                                'text.” '
                                                                                                                'If '
                                                                                                                'both '
                                                                                                                'PDF.js '
                                                                                                                'and '
                                                                                                                'PyMuPDF '
                                                                                                                'find '
                                                                                                                'no '
                                                                                                                'text, '
                                                                                                                'the '
                                                                                                                'page '
                                                                                                                'likely '
                                                                                                                'requires '
                                                                                                                'OCR.',
 'legacy.help.vector_database_defaults': 'Vector database defaults',
 'legacy.help.vector_database_or_selected_evidence_required': 'Vector database or selected evidence required',
 'legacy.help.waiting_for_model': 'Waiting for model…',
 'legacy.help.when_more_than_one_provider_profile_is_configured_derridai_defaults_grading_to_a_profile_differ': 'When '
                                                                                                                'more '
                                                                                                                'than '
                                                                                                                'one '
                                                                                                                'provider '
                                                                                                                'profile '
                                                                                                                'is '
                                                                                                                'configured, '
                                                                                                                'DerridAI '
                                                                                                                'defaults '
                                                                                                                'grading '
                                                                                                                'to a '
                                                                                                                'profile '
                                                                                                                'different '
                                                                                                                'from '
                                                                                                                'answer '
                                                                                                                'generation.'})
DEFAULT_FR_CA.update({'legacy.help.a_full_backup_can_contain_provider_api_keys_store_backup_zip_files_securely_installed_ollama_mo': 'Une '
                                                                                                                'sauvegarde '
                                                                                                                'complète '
                                                                                                                'peut '
                                                                                                                'contenir '
                                                                                                                'des '
                                                                                                                'clés '
                                                                                                                'API '
                                                                                                                'de '
                                                                                                                'fournisseurs. '
                                                                                                                'Conservez '
                                                                                                                'les '
                                                                                                                'fichiers '
                                                                                                                'ZIP '
                                                                                                                'de '
                                                                                                                'sauvegarde '
                                                                                                                'de '
                                                                                                                'façon '
                                                                                                                'sécuritaire. '
                                                                                                                'Les '
                                                                                                                'modèles '
                                                                                                                'Ollama '
                                                                                                                'installés '
                                                                                                                'et '
                                                                                                                'les '
                                                                                                                'images '
                                                                                                                'Docker '
                                                                                                                'ne '
                                                                                                                'sont '
                                                                                                                'pas '
                                                                                                                'copiés.',
 'legacy.help.add_at_least_one_condition': 'Ajoutez au moins une condition.',
 'legacy.help.additional_options_json': 'Options JSON supplémentaires',
 'legacy.help.advanced_ollama_options_json': 'Options JSON avancées d’Ollama',
 'legacy.help.advanced_openai_compatible_options_json': 'Options JSON avancées du fournisseur compatible avec OpenAI',
 'legacy.help.advanced_options_json': 'Options JSON avancées',
 'legacy.help.advanced_provider_options': 'Options avancées du fournisseur',
 'legacy.help.all_cached_responses_were_processed': 'Toutes les réponses en mémoire cache ont été traitées.',
 'legacy.help.all_files_separately': 'Tous les fichiers séparément',
 'legacy.help.all_loaded_jsonl_files': 'Tous les fichiers JSONL chargés',
 'legacy.help.allow_researcher_accounts_to_use_this_profile_for_research_without_exposing_credentials_or_prov': 'Permettre '
                                                                                                                'aux '
                                                                                                                'comptes '
                                                                                                                'chercheurs '
                                                                                                                'd’utiliser '
                                                                                                                'ce '
                                                                                                                'profil '
                                                                                                                'dans '
                                                                                                                'Recherche '
                                                                                                                'sans '
                                                                                                                'exposer '
                                                                                                                'les '
                                                                                                                'identifiants '
                                                                                                                'ni '
                                                                                                                'l’administration '
                                                                                                                'du '
                                                                                                                'fournisseur.',
 'legacy.help.also_remove_from_chroma': 'Retirer également de Chroma',
 'legacy.help.an_administrator_must_create_or_restore_a_corpus_vector_database_before_researcher_search_and_r': 'Un '
                                                                                                                'administrateur '
                                                                                                                'doit '
                                                                                                                'créer '
                                                                                                                'ou '
                                                                                                                'restaurer '
                                                                                                                'une '
                                                                                                                'base '
                                                                                                                'de '
                                                                                                                'données '
                                                                                                                'vectorielle '
                                                                                                                'du '
                                                                                                                'corpus '
                                                                                                                'avant '
                                                                                                                'que '
                                                                                                                'les '
                                                                                                                'chercheurs '
                                                                                                                'puissent '
                                                                                                                'utiliser '
                                                                                                                'la '
                                                                                                                'recherche '
                                                                                                                'et le '
                                                                                                                'RAG.',
 'legacy.help.api_keys_are_intentionally_omitted': 'Les clés API sont volontairement omises.',
 'legacy.help.apply_one_field_value_consistently_across_a_selected_record_set_every_actual_change_is_audited': 'Appliquez '
                                                                                                               'une '
                                                                                                               'même '
                                                                                                               'valeur '
                                                                                                               'de '
                                                                                                               'champ '
                                                                                                               'à un '
                                                                                                               'ensemble '
                                                                                                               'de '
                                                                                                               'fiches '
                                                                                                               'sélectionnées. '
                                                                                                               'Chaque '
                                                                                                               'modification '
                                                                                                               'réelle '
                                                                                                               'est '
                                                                                                               'consignée.',
 'legacy.help.ask_a_research_question_about_derrida': 'Posez une question de recherche sur Derrida…',
 'legacy.help.ask_an_administrator_to_create_or_populate_a_corpus_vector_database': 'Demandez à un administrateur de '
                                                                                    'créer ou d’alimenter une base de '
                                                                                    'données vectorielle du corpus.',
 'legacy.help.auto_grade_final_response_as_the_last_pipeline_step': 'Évaluer automatiquement la réponse finale comme '
                                                                    'dernière étape du pipeline',
 'legacy.help.auto_grade_provider_profile': 'Profil fournisseur pour l’évaluation automatique',
 'legacy.help.auto_grade_the_final_rag_response_after_caching': 'Évaluer automatiquement la réponse RAG finale après '
                                                                'la mise en cache',
 'legacy.help.auto_improve_pass_in_progress': 'Passe d’amélioration automatique en cours',
 'legacy.help.autocomplete_searches_record_ids_works_authors_and_source_files_without_rendering_an_enormous_s': 'La '
                                                                                                                'saisie '
                                                                                                                'semi-automatique '
                                                                                                                'recherche '
                                                                                                                'les '
                                                                                                                'identifiants '
                                                                                                                'de '
                                                                                                                'fiche, '
                                                                                                                'les '
                                                                                                                'œuvres, '
                                                                                                                'les '
                                                                                                                'auteurs '
                                                                                                                'et '
                                                                                                                'les '
                                                                                                                'fichiers '
                                                                                                                'sources '
                                                                                                                'sans '
                                                                                                                'afficher '
                                                                                                                'une '
                                                                                                                'liste '
                                                                                                                'démesurée.',
 'legacy.help.automatic_pipeline_grade': 'Évaluation automatique du pipeline',
 'legacy.help.browse_summarized_records': 'Parcourir les fiches résumées',
 'legacy.help.browser_permission_is_required_notifications_are_local_browser_notifications': 'L’autorisation du '
                                                                                             'navigateur est requise. '
                                                                                             'Les notifications sont '
                                                                                             'envoyées localement par '
                                                                                             'le navigateur.',
 'legacy.help.build_explicit_boolean_groups_such_as_a_and_b_and_c_or_d_or_e_and_f': 'Créez des groupes booléens '
                                                                                    'explicites, par exemple A ET B ET '
                                                                                    '(C OU D OU E) ET F.',
 'legacy.help.bulk_edit_one_field': 'Modifier un champ en lot',
 'legacy.help.cached_rag_responses': 'réponses RAG en mémoire cache',
 'legacy.help.changed_aggregate': 'Modifiés + agrégés',
 'legacy.help.changes_stay_local_until_you_export_or_upsert_them': 'Les modifications demeurent locales jusqu’à leur '
                                                                   'exportation ou leur synchronisation.',
 'legacy.help.checking_configured_llm_provider': 'Vérification du fournisseur LLM configuré…',
 'legacy.help.choose_any_subset_the_selected_source_tabs_will_be_replaced_in_the_workspace_by_the_merged_tab': 'Choisissez '
                                                                                                               'n’importe '
                                                                                                               'quel '
                                                                                                               'sous-ensemble. '
                                                                                                               'Les '
                                                                                                               'onglets '
                                                                                                               'sources '
                                                                                                               'sélectionnés '
                                                                                                               'seront '
                                                                                                               'remplacés '
                                                                                                               'dans '
                                                                                                               'l’espace '
                                                                                                               'de '
                                                                                                               'travail '
                                                                                                               'par '
                                                                                                               'l’onglet '
                                                                                                               'fusionné.',
 'legacy.help.choose_discovered_model': 'Choisir un modèle découvert',
 'legacy.help.choose_the_grading_provider_model_in_the_rag_runner': 'Choisissez le fournisseur et le modèle '
                                                                    'd’évaluation dans l’outil d’exécution RAG.',
 'legacy.help.clean_current_page_text': 'Nettoyer le texte de la page actuelle',
 'legacy.help.clear_column_filters': 'Effacer les filtres de colonnes',
 'legacy.help.clear_remembered_questions': 'Effacer les questions mémorisées',
 'legacy.help.completed_rag_runs_will_be_cached_automatically_and_appear_here': 'Les exécutions RAG terminées seront '
                                                                                'automatiquement mises en cache et '
                                                                                'apparaîtront ici.',
 'legacy.help.conservative_ligature_zero_width_character_and_broken_line_hyphen_cleanup_no_paraphrasing': 'Nettoyage '
                                                                                                          'prudent des '
                                                                                                          'ligatures, '
                                                                                                          'des '
                                                                                                          'caractères '
                                                                                                          'de largeur '
                                                                                                          'nulle et '
                                                                                                          'des césures '
                                                                                                          'de fin de '
                                                                                                          'ligne. '
                                                                                                          'Aucune '
                                                                                                          'paraphrase.',
 'legacy.help.copy_entire_record_json': 'Copier tout le JSON de la fiche',
 'legacy.help.corpus_chroma_collections': 'collections Chroma du corpus',
 'legacy.help.could_not_load_response_faq': 'Impossible de charger la FAQ des réponses.',
 'legacy.help.could_not_read_response_cache': 'Impossible de lire la mémoire cache des réponses.',
 'legacy.help.could_not_render_this_item': 'Impossible d’afficher cet élément.',
 'legacy.help.create_draft_record': 'Créer une fiche provisoire',
 'legacy.help.create_jsonl_subset': 'Créer un sous-ensemble JSONL',
 'legacy.help.create_or_restore_a_corpus_vector_database_before_upserting_pdf_drafts': 'Créez ou restaurez une base de '
                                                                                       'données vectorielle du corpus '
                                                                                       'avant de synchroniser les '
                                                                                       'brouillons issus de PDF.',
 'legacy.help.current_chroma_path': 'Chemin Chroma actuel',
 'legacy.help.decomposition_max_tokens': 'Nombre maximal de jetons pour la décomposition',
 'legacy.help.default_embedding_model': 'Modèle de plongement vectoriel par défaut',
 'legacy.help.default_embedding_provider': 'Fournisseur de plongements vectoriels par défaut',
 'legacy.help.default_provider_profile': 'Profil fournisseur par défaut',
 'legacy.help.default_review_preset': 'Préréglage de révision par défaut',
 'legacy.help.delete_audit_history': 'Supprimer l’historique d’audit…',
 'legacy.help.deletes_all_loaded_browser_jsonl_workspace_data_and_every_collection_in_the_current_chroma_pers': 'Supprime '
                                                                                                                'toutes '
                                                                                                                'les '
                                                                                                                'données '
                                                                                                                'JSONL '
                                                                                                                'chargées '
                                                                                                                'dans '
                                                                                                                'l’espace '
                                                                                                                'de '
                                                                                                                'travail '
                                                                                                                'du '
                                                                                                                'navigateur '
                                                                                                                'et '
                                                                                                                'toutes '
                                                                                                                'les '
                                                                                                                'collections '
                                                                                                                'de la '
                                                                                                                'base '
                                                                                                                'Chroma '
                                                                                                                'actuelle. '
                                                                                                                'Les '
                                                                                                                'fichiers '
                                                                                                                'des '
                                                                                                                'modèles '
                                                                                                                'installés '
                                                                                                                'ne '
                                                                                                                'sont '
                                                                                                                'pas '
                                                                                                                'supprimés.',
 'legacy.help.do_not_add_to_jsonl': 'Ne pas ajouter au JSONL',
 'legacy.help.download_merged_jsonl_immediately': 'Télécharger immédiatement le JSONL fusionné',
 'legacy.help.draft_record_from_pdf_page': 'Créer une fiche provisoire à partir de la page PDF',
 'legacy.help.drafts_persist_across_navigation_and_browser_refresh_the_40_most_recent_submitted_question_inst': 'Les '
                                                                                                                'brouillons '
                                                                                                                'persistent '
                                                                                                                'pendant '
                                                                                                                'la '
                                                                                                                'navigation '
                                                                                                                'et '
                                                                                                                'après '
                                                                                                                'l’actualisation '
                                                                                                                'du '
                                                                                                                'navigateur. '
                                                                                                                'Les '
                                                                                                                '40 '
                                                                                                                'paires '
                                                                                                                'question-instructions '
                                                                                                                'les '
                                                                                                                'plus '
                                                                                                                'récentes '
                                                                                                                'sont '
                                                                                                                'conservées '
                                                                                                                'localement.',
 'legacy.help.drop_one_or_more_jsonl_files_anywhere_on_this_page_or_choose_files_manually_each_file_stays_in_': 'Déposez '
                                                                                                                'un ou '
                                                                                                                'plusieurs '
                                                                                                                'fichiers '
                                                                                                                'JSONL '
                                                                                                                'n’importe '
                                                                                                                'où '
                                                                                                                'sur '
                                                                                                                'cette '
                                                                                                                'page, '
                                                                                                                'ou '
                                                                                                                'choisissez-les '
                                                                                                                'manuellement. '
                                                                                                                'Chaque '
                                                                                                                'fichier '
                                                                                                                'reste '
                                                                                                                'dans '
                                                                                                                'son '
                                                                                                                'propre '
                                                                                                                'onglet '
                                                                                                                'et '
                                                                                                                'peut '
                                                                                                                'être '
                                                                                                                'modifié, '
                                                                                                                'comparé, '
                                                                                                                'recherché, '
                                                                                                                'exporté '
                                                                                                                'ou '
                                                                                                                'envoyé '
                                                                                                                'à '
                                                                                                                'ChromaDB.',
 'legacy.help.each_action_lets_you_choose_provider_model_parameters_and_run_mode': 'Chaque action permet de choisir le '
                                                                                   'fournisseur, le modèle, les '
                                                                                   'paramètres et le mode d’exécution.',
 'legacy.help.each_cache_record_stores_the_original_rag_query_instructions_run_parameters_answer_evidence_ret': 'Chaque '
                                                                                                                'entrée '
                                                                                                                'de '
                                                                                                                'cache '
                                                                                                                'conserve '
                                                                                                                'la '
                                                                                                                'requête '
                                                                                                                'RAG '
                                                                                                                'originale, '
                                                                                                                'les '
                                                                                                                'instructions, '
                                                                                                                'les '
                                                                                                                'paramètres '
                                                                                                                'd’exécution, '
                                                                                                                'la '
                                                                                                                'réponse, '
                                                                                                                'les '
                                                                                                                'preuves, '
                                                                                                                'les '
                                                                                                                'diagnostics '
                                                                                                                'de '
                                                                                                                'repérage, '
                                                                                                                'les '
                                                                                                                'durées '
                                                                                                                'et '
                                                                                                                'toutes '
                                                                                                                'les '
                                                                                                                'évaluations '
                                                                                                                'LLM '
                                                                                                                'enregistrées.',
 'legacy.help.enter_the_new_value_arrays_objects_use_json_enter_null_for_null': 'Saisissez la nouvelle valeur. Les '
                                                                                'tableaux et objets utilisent JSON. '
                                                                                'Saisissez __NULL__ pour une valeur '
                                                                                'nulle.',
 'legacy.help.evidence_retrieval_and_pipeline_details': 'Détails des preuves, du repérage et du pipeline',
 'legacy.help.expand_all_ui_panels': 'Développer tous les panneaux de l’interface',
 'legacy.help.expand_navigation_sidebar': 'Développer le volet de navigation',
 'legacy.help.filter_linked_records': 'Filtrer les fiches liées',
 'legacy.help.five_most_recent_runs': 'Cinq exécutions les plus récentes',
 'legacy.help.freellm_openai_model_selection': 'Sélection du modèle FreeLLM / OpenAI',
 'legacy.help.generation_defaults_advanced_parameters': 'Valeurs de génération par défaut et paramètres avancés',
 'legacy.help.latest_100_response_cache_entries_use_response_faq_for_full_answer_evidence_browsing_and_re_run': 'Les '
                                                                                                                '100 '
                                                                                                                'entrées '
                                                                                                                'les '
                                                                                                                'plus '
                                                                                                                'récentes '
                                                                                                                'de la '
                                                                                                                'mémoire '
                                                                                                                'cache '
                                                                                                                'des '
                                                                                                                'réponses. '
                                                                                                                'Utilisez '
                                                                                                                'la '
                                                                                                                'FAQ '
                                                                                                                'des '
                                                                                                                'réponses '
                                                                                                                'pour '
                                                                                                                'consulter '
                                                                                                                'les '
                                                                                                                'réponses, '
                                                                                                                'les '
                                                                                                                'preuves '
                                                                                                                'et '
                                                                                                                'relancer '
                                                                                                                'des '
                                                                                                                'recherches.',
 'legacy.help.llm_query_decomposition_french_query_formulation': 'Décomposition de la requête par LLM + formulation de '
                                                                 'requêtes en français',
 'legacy.help.llm_review_workspace': 'Espace de révision LLM',
 'legacy.help.load_this_pdf_in_pdf_explorer_first': 'Chargez d’abord ce PDF dans l’explorateur PDF',
 'legacy.help.local_record_changed_since_job_started': 'la fiche locale a été modifiée depuis le début de la tâche',
 'legacy.help.match_link_page_to_record': 'Faire correspondre et lier la page à une fiche',
 'legacy.help.max_chars_evidence_record': 'Nombre maximal de caractères / preuve',
 'legacy.help.merge_and_replace_selected_tabs': 'Fusionner et remplacer les onglets sélectionnés',
 'legacy.help.mixed_across_records': 'valeurs variables selon les fiches',
 'legacy.help.model_selection_mode': 'Mode de sélection du modèle',
 'legacy.help.new_jsonl_tab_name': 'Nom du nouvel onglet JSONL',
 'legacy.help.no_answer_returned': 'Aucune réponse reçue.',
 'legacy.help.no_audit_history_recorded': 'Aucun historique d’audit enregistré.',
 'legacy.help.no_background_operations_yet': 'Aucune opération en arrière-plan pour le moment.',
 'legacy.help.no_cached_responses_yet': 'Aucune réponse en mémoire cache pour le moment.',
 'legacy.help.no_changes_proposed': 'Aucune modification proposée.',
 'legacy.help.no_corpus_chroma_collections': 'Aucune collection Chroma du corpus',
 'legacy.help.no_events_recorded': 'Aucun évènement enregistré.',
 'legacy.help.no_evidence_returned': 'Aucune preuve reçue.',
 'legacy.help.no_evidence_selected_yet_use_add_to_evidence_on_record_search_rows': 'Aucune preuve sélectionnée. '
                                                                                   'Utilisez « Ajouter aux preuves » '
                                                                                   'dans une fiche ou un résultat de '
                                                                                   'recherche.',
 'legacy.help.no_full_evidence_retained': 'Aucune preuve intégrale conservée.',
 'legacy.help.no_linked_records_match_this_filter': 'Aucune fiche liée ne correspond à ce filtre.',
 'legacy.help.no_llm_provider_profiles_configured': 'Aucun profil fournisseur LLM n’est configuré.',
 'legacy.help.no_matching_records': 'Aucune fiche correspondante',
 'legacy.help.no_matching_records_2': 'Aucune fiche correspondante.',
 'legacy.help.no_models_match_this_filter': 'Aucun modèle ne correspond à ce filtre.',
 'legacy.help.no_pdf_pages_linked_to_this_record': 'Aucune page PDF n’est liée à cette fiche.',
 'legacy.help.no_rag_jobs_yet_start_one_below': 'Aucune tâche RAG pour le moment. Lancez-en une ci-dessous.',
 'legacy.help.no_rag_pipeline_runs_recorded_yet': 'Aucune exécution de pipeline RAG enregistrée pour le moment.',
 'legacy.help.no_record_selected': 'Aucune fiche sélectionnée.',
 'legacy.help.no_records_linked_to_this_page_yet': 'Aucune fiche n’est encore liée à cette page.',
 'legacy.help.no_records_match_the_current_filters': 'Aucune fiche ne correspond aux filtres actuels.',
 'legacy.help.no_records_match_this_work': 'Aucune fiche ne correspond à cette œuvre.',
 'legacy.help.no_visible_columns': 'Aucune colonne visible.',
 'legacy.help.nuke_derridai_workspace': 'EFFACER l’espace de travail DerridAI',
 'legacy.help.ocr_text_cleanup': 'ROC / nettoyage du texte',
 'legacy.help.on_when_background_operations_finish': 'Activer à la fin des opérations en arrière-plan',
 'legacy.help.only_modify_records_whose_value_actually_differs': 'Modifier uniquement les fiches dont la valeur '
                                                                 'diffère réellement',
 'legacy.help.open_a_corpus_workspace': 'Ouvrir un espace de travail du corpus',
 'legacy.help.open_a_pdf_to_render_pages_read_its_embedded_title_metadata_extract_text_and_move_directly_betw': 'Ouvrez '
                                                                                                                'un '
                                                                                                                'PDF '
                                                                                                                'pour '
                                                                                                                'afficher '
                                                                                                                'ses '
                                                                                                                'pages, '
                                                                                                                'lire '
                                                                                                                'les '
                                                                                                                'métadonnées '
                                                                                                                'de '
                                                                                                                'titre '
                                                                                                                'intégrées, '
                                                                                                                'extraire '
                                                                                                                'le '
                                                                                                                'texte '
                                                                                                                'et '
                                                                                                                'passer '
                                                                                                                'directement '
                                                                                                                'des '
                                                                                                                'pages '
                                                                                                                'PDF '
                                                                                                                'liées '
                                                                                                                'aux '
                                                                                                                'fiches '
                                                                                                                'du '
                                                                                                                'corpus.',
 'legacy.help.open_a_source_pdf': 'Ouvrir un PDF source',
 'legacy.help.openai_compatible_freellm': 'Compatible avec OpenAI / FreeLLM',
 'legacy.help.optional_constraints_on_the_answer_kept_separate_from_the_research_question': 'Contraintes facultatives '
                                                                                            'sur la réponse, '
                                                                                            'conservées séparément de '
                                                                                            'la question de recherche.',
 'legacy.help.optional_instructions_applied_to_every_record_in_this_batch': 'Instructions facultatives appliquées à '
                                                                            'chaque fiche de ce lot.',
 'legacy.help.parentheses_evaluate_this_block_as_one_boolean_value': 'Parenthèses : évaluer ce bloc comme une seule '
                                                                     'valeur booléenne',
 'legacy.help.pipeline_query_metadata': 'Métadonnées de la requête du pipeline',
 'legacy.help.preview_this_version': 'Aperçu de cette version',
 'legacy.help.proposals_are_intentionally_hidden_until_every_queued_record_has_been_processed': 'Les propositions '
                                                                                                'restent '
                                                                                                'volontairement '
                                                                                                'masquées jusqu’à ce '
                                                                                                'que toutes les fiches '
                                                                                                'en file aient été '
                                                                                                'traitées.',
 'legacy.help.proposed_changes_for_this_record': 'Modifications proposées pour cette fiche',
 'legacy.help.provider_choice_default_review_preset_and_whether_llm_review_opens_interactively_or_runs_as_a_b': 'Choix '
                                                                                                                'du '
                                                                                                                'fournisseur, '
                                                                                                                'préréglage '
                                                                                                                'de '
                                                                                                                'révision '
                                                                                                                'par '
                                                                                                                'défaut '
                                                                                                                'et '
                                                                                                                'mode '
                                                                                                                'interactif '
                                                                                                                'ou en '
                                                                                                                'arrière-plan '
                                                                                                                'de la '
                                                                                                                'révision '
                                                                                                                'LLM.',
 'legacy.help.provider_endpoints_credentials_models_concurrency_limits_generation_defaults_readiness_and_inde': 'Les '
                                                                                                                'points '
                                                                                                                'de '
                                                                                                                'terminaison, '
                                                                                                                'identifiants, '
                                                                                                                'modèles, '
                                                                                                                'limites '
                                                                                                                'de '
                                                                                                                'simultanéité, '
                                                                                                                'valeurs '
                                                                                                                'de '
                                                                                                                'génération '
                                                                                                                'par '
                                                                                                                'défaut, '
                                                                                                                'état '
                                                                                                                'de '
                                                                                                                'préparation '
                                                                                                                'et '
                                                                                                                'préchauffages '
                                                                                                                'indépendants '
                                                                                                                'se '
                                                                                                                'configurent '
                                                                                                                'dans '
                                                                                                                'la '
                                                                                                                'page '
                                                                                                                'Fournisseurs.',
 'legacy.help.query_decomposition_max_tokens': 'Nombre maximal de jetons pour la décomposition de la requête',
 'legacy.help.question_instructions': 'Question et instructions',
 'legacy.help.rag_pipeline_activity': 'Activité du pipeline RAG',
 'legacy.help.rag_pipeline_defaults': 'Valeurs par défaut du pipeline RAG',
 'legacy.help.rag_response_cache': 'Mémoire cache des réponses RAG',
 'legacy.help.rag_response_grade': 'Évaluation de la réponse RAG',
 'legacy.help.raw_evidence_tagged_answer': 'Réponse brute balisée par preuve',
 'legacy.help.recall_a_previous_question': 'Retrouver une question précédente…',
 'legacy.help.recent_audit_history': 'Historique d’audit récent',
 'legacy.help.recent_cached_responses': 'Réponses récentes en mémoire cache',
 'legacy.help.recent_rag_pipelines': 'Pipelines RAG récents',
 'legacy.help.record_a_json_jsonl': 'Fiche A — JSON / JSONL',
 'legacy.help.record_b_json_jsonl': 'Fiche B — JSON / JSONL',
 'legacy.help.records_linked_anywhere_in_this_pdf': 'Fiches liées à une page de ce PDF',
 'legacy.help.records_selected_across_corpus_tables_are_pinned_into_this_run_you_can_also_bypass_retrieval_en': 'Les '
                                                                                                                'fiches '
                                                                                                                'sélectionnées '
                                                                                                                'dans '
                                                                                                                'les '
                                                                                                                'tableaux '
                                                                                                                'du '
                                                                                                                'corpus '
                                                                                                                'sont '
                                                                                                                'épinglées '
                                                                                                                'à '
                                                                                                                'cette '
                                                                                                                'exécution. '
                                                                                                                'Vous '
                                                                                                                'pouvez '
                                                                                                                'aussi '
                                                                                                                'contourner '
                                                                                                                'entièrement '
                                                                                                                'le '
                                                                                                                'repérage '
                                                                                                                'et '
                                                                                                                'répondre '
                                                                                                                'uniquement '
                                                                                                                'à '
                                                                                                                'partir '
                                                                                                                'de ce '
                                                                                                                'paquet '
                                                                                                                'de '
                                                                                                                'preuves.',
 'legacy.help.remove_all_pdf_links': 'Supprimer tous les liens PDF',
 'legacy.help.render_pages_extract_text_connect_pages_to_records_and_run_llm_assisted_source_workflows': 'Affichez les '
                                                                                                         'pages, '
                                                                                                         'extrayez le '
                                                                                                         'texte, '
                                                                                                         'reliez les '
                                                                                                         'pages aux '
                                                                                                         'fiches et '
                                                                                                         'exécutez des '
                                                                                                         'flux de '
                                                                                                         'travail '
                                                                                                         'assistés par '
                                                                                                         'LLM.',
 'legacy.help.request_notification_permission': 'Demander l’autorisation d’envoyer des notifications',
 'legacy.help.research_question_prompt': 'Question de recherche / invite',
 'legacy.help.research_run_context': 'Contexte de l’exécution de recherche',
 'legacy.help.reset_table_columns': 'Réinitialiser les colonnes du tableau',
 'legacy.help.reset_ui_choices_or_remove_audit_history_without_deleting_records': 'Réinitialisez les choix de '
                                                                                  'l’interface ou supprimez '
                                                                                  'l’historique d’audit sans supprimer '
                                                                                  'les fiches.',
 'legacy.help.restore_removed_upsert_queue_items': 'Rétablir les éléments retirés de la file de synchronisation',
 'legacy.help.restore_this_version': 'Rétablir cette version',
 'legacy.help.retrieval_fusion_reranking_evidence_budget_and_query_decomposition_defaults_per_run_generation_': 'Valeurs '
                                                                                                                'par '
                                                                                                                'défaut '
                                                                                                                'du '
                                                                                                                'repérage, '
                                                                                                                'de la '
                                                                                                                'fusion, '
                                                                                                                'du '
                                                                                                                'reclassement, '
                                                                                                                'du '
                                                                                                                'budget '
                                                                                                                'de '
                                                                                                                'preuves '
                                                                                                                'et de '
                                                                                                                'la '
                                                                                                                'décomposition '
                                                                                                                'des '
                                                                                                                'requêtes. '
                                                                                                                'Les '
                                                                                                                'paramètres '
                                                                                                                'de '
                                                                                                                'génération '
                                                                                                                'propres '
                                                                                                                'à '
                                                                                                                'chaque '
                                                                                                                'exécution '
                                                                                                                'sont '
                                                                                                                'aussi '
                                                                                                                'accessibles '
                                                                                                                'dans '
                                                                                                                'Recherche.',
 'legacy.help.review_add_draft': 'Réviser / ajouter le brouillon',
 'legacy.help.review_link_page': 'Réviser et lier la page',
 'legacy.help.same_model_grading_warning': 'Avertissement : même modèle pour l’évaluation.',
 'legacy.help.saved_to_response_faq_when_caching_succeeds': 'Enregistré dans la FAQ des réponses lorsque la mise en '
                                                            'cache réussit.',
 'legacy.help.saved_with_the_cached_rag_query_when_a_response_cache_record_is_available': 'Enregistré avec la requête '
                                                                                          'RAG mise en cache '
                                                                                          'lorsqu’une entrée '
                                                                                          'correspondante est '
                                                                                          'disponible.',
 'legacy.help.saving_updates_this_record_in_place_under_the_same_chroma_id_and_regenerates_its_embedding_when': 'L’enregistrement '
                                                                                                                'met '
                                                                                                                'cette '
                                                                                                                'fiche '
                                                                                                                'à '
                                                                                                                'jour '
                                                                                                                'sous '
                                                                                                                'le '
                                                                                                                'même '
                                                                                                                'identifiant '
                                                                                                                'Chroma '
                                                                                                                'et '
                                                                                                                'régénère '
                                                                                                                'son '
                                                                                                                'plongement '
                                                                                                                'vectoriel '
                                                                                                                'lorsque '
                                                                                                                'le '
                                                                                                                'fournisseur '
                                                                                                                'configuré '
                                                                                                                'le '
                                                                                                                'permet.',
 'legacy.help.search_cached_questions': 'Rechercher dans les questions en mémoire cache',
 'legacy.help.search_text_in_this_file': 'Rechercher du texte dans ce fichier',
 'legacy.help.select_all_changes': 'Sélectionner toutes les modifications',
 'legacy.help.select_all_results': 'Sélectionner tous les résultats',
 'legacy.help.select_or_create_a_corpus_vector_database_first': 'Sélectionnez ou créez d’abord une base de données '
                                                                'vectorielle du corpus.',
 'legacy.help.select_or_paste_two_records_to_compare_them': 'Sélectionnez ou collez deux fiches pour les comparer.',
 'legacy.help.select_record_changes': 'Sélectionner les modifications de fiches',
 'legacy.help.select_two_records': 'Sélectionner deux fiches',
 'legacy.help.select_visible_records': 'Sélectionner les fiches visibles',
 'legacy.help.selected_evidence_only_retrieval_disabled': 'Preuves sélectionnées seulement · repérage désactivé',
 'legacy.help.start_from_scratch': 'Recommencer à zéro',
 'legacy.help.start_typing_to_search_loaded_records': 'Commencez à taper pour rechercher dans les fiches chargées.',
 'legacy.help.stop_after_current': 'Arrêter après l’élément en cours',
 'legacy.help.switch_freely_between_interactive_review_background_review_and_aggregate_auto_improve_before_st': 'Avant '
                                                                                                                'l’exécution, '
                                                                                                                'passez '
                                                                                                                'librement '
                                                                                                                'de la '
                                                                                                                'révision '
                                                                                                                'interactive '
                                                                                                                'à la '
                                                                                                                'révision '
                                                                                                                'en '
                                                                                                                'arrière-plan '
                                                                                                                'ou à '
                                                                                                                'l’amélioration '
                                                                                                                'automatique '
                                                                                                                'agrégée.',
 'legacy.help.system_cache_only_this_collection_is_intentionally_excluded_from_corpus_vector_stores_corpus_db': 'Mémoire '
                                                                                                                'cache '
                                                                                                                'système '
                                                                                                                'seulement. '
                                                                                                                'Cette '
                                                                                                                'collection '
                                                                                                                'est '
                                                                                                                'volontairement '
                                                                                                                'exclue '
                                                                                                                'des '
                                                                                                                'bases '
                                                                                                                'vectorielles '
                                                                                                                'du '
                                                                                                                'corpus, '
                                                                                                                'des '
                                                                                                                'décomptes '
                                                                                                                'de '
                                                                                                                'bases, '
                                                                                                                'de la '
                                                                                                                'réplication '
                                                                                                                'linguistique '
                                                                                                                'et de '
                                                                                                                'la '
                                                                                                                'sélection '
                                                                                                                'des '
                                                                                                                'sources '
                                                                                                                'RAG.',
 'legacy.help.text_review_runs_separately_so_output_stays_bounded': 'La révision du texte s’exécute séparément afin de '
                                                                    'limiter la taille de la sortie.',
 'legacy.help.these_records_are_identical_across_all_compared_fields': 'Ces fiches sont identiques pour tous les '
                                                                       'champs comparés.',
 'legacy.help.this_cannot_be_undone_unless_you_have_exported_backed_up_your_jsonl_and_chroma_data': 'Cette action est '
                                                                                                    'irréversible, '
                                                                                                    'sauf si vous avez '
                                                                                                    'exporté ou '
                                                                                                    'sauvegardé vos '
                                                                                                    'données JSONL et '
                                                                                                    'Chroma.',
 'legacy.help.this_is_a_draft_generated_by_an_llm_review_attribution_page_metadata_quotation_provenance_and_t': 'Il '
                                                                                                                's’agit '
                                                                                                                'd’un '
                                                                                                                'brouillon '
                                                                                                                'généré '
                                                                                                                'par '
                                                                                                                'un '
                                                                                                                'LLM. '
                                                                                                                'Vérifiez '
                                                                                                                'l’attribution, '
                                                                                                                'les '
                                                                                                                'métadonnées '
                                                                                                                'de '
                                                                                                                'page, '
                                                                                                                'la '
                                                                                                                'provenance '
                                                                                                                'des '
                                                                                                                'citations '
                                                                                                                'et le '
                                                                                                                'texte '
                                                                                                                'avant '
                                                                                                                'de '
                                                                                                                'l’enregistrer.',
 'legacy.help.this_is_the_reconstructed_original_state_before_tracked_updates': 'Il s’agit de l’état d’origine '
                                                                                'reconstitué avant les modifications '
                                                                                'consignées.',
 'legacy.help.this_local_record_changed_after_the_llm_job_started_current_values_below_may_differ_from_the_va': 'Cette '
                                                                                                                'fiche '
                                                                                                                'locale '
                                                                                                                'a été '
                                                                                                                'modifiée '
                                                                                                                'après '
                                                                                                                'le '
                                                                                                                'démarrage '
                                                                                                                'de la '
                                                                                                                'tâche '
                                                                                                                'LLM. '
                                                                                                                'Les '
                                                                                                                'valeurs '
                                                                                                                'actuelles '
                                                                                                                'ci-dessous '
                                                                                                                'peuvent '
                                                                                                                'différer '
                                                                                                                'de '
                                                                                                                'celles '
                                                                                                                'examinées '
                                                                                                                'initialement.',
 'legacy.help.this_setting_is_fixed_by_the_administrator_approved_researcher_profile': 'Ce paramètre est fixé par le '
                                                                                       'profil chercheur approuvé par '
                                                                                       'l’administrateur.',
 'legacy.help.top_level_and_or_plus_explicit_nested_groups': 'ET/OU au niveau supérieur avec groupes imbriqués '
                                                             'explicites',
 'legacy.help.type_nuke_to_enable': 'Tapez NUKE pour activer',
 'legacy.help.unlink_record_from_pdf': 'Dissocier la fiche du PDF',
 'legacy.help.use_as_current_page_text': 'Utiliser comme texte de la page actuelle',
 'legacy.help.use_extract_current_page_or_extract_all_text_if_both_pdf_js_and_pymupdf_find_no_text_the_page_l': 'Utilisez '
                                                                                                                '« '
                                                                                                                'Extraire '
                                                                                                                'la '
                                                                                                                'page '
                                                                                                                'actuelle '
                                                                                                                '» ou '
                                                                                                                '« '
                                                                                                                'Extraire '
                                                                                                                'tout '
                                                                                                                'le '
                                                                                                                'texte '
                                                                                                                '». Si '
                                                                                                                'PDF.js '
                                                                                                                'et '
                                                                                                                'PyMuPDF '
                                                                                                                'ne '
                                                                                                                'trouvent '
                                                                                                                'aucun '
                                                                                                                'texte, '
                                                                                                                'la '
                                                                                                                'page '
                                                                                                                'nécessite '
                                                                                                                'probablement '
                                                                                                                'une '
                                                                                                                'ROC.',
 'legacy.help.vector_database_defaults': 'Valeurs par défaut des bases de données vectorielles',
 'legacy.help.vector_database_or_selected_evidence_required': 'Base de données vectorielle ou preuves sélectionnées '
                                                              'requises',
 'legacy.help.waiting_for_model': 'En attente du modèle…',
 'legacy.help.when_more_than_one_provider_profile_is_configured_derridai_defaults_grading_to_a_profile_differ': 'Lorsque '
                                                                                                                'plusieurs '
                                                                                                                'profils '
                                                                                                                'fournisseurs '
                                                                                                                'sont '
                                                                                                                'configurés, '
                                                                                                                'DerridAI '
                                                                                                                'utilise '
                                                                                                                'par '
                                                                                                                'défaut '
                                                                                                                'un '
                                                                                                                'profil '
                                                                                                                'd’évaluation '
                                                                                                                'différent '
                                                                                                                'de '
                                                                                                                'celui '
                                                                                                                'qui '
                                                                                                                'génère '
                                                                                                                'la '
                                                                                                                'réponse.'})


DEFAULT_EN_US.update({
    "works.cover_of": "Cover of {title}",
    "operations.syncing_records": "Syncing records…",
})
DEFAULT_FR_CA.update({
    "works.cover_of": "Couverture de {title}",
    "operations.syncing_records": "Synchronisation des fiches…",
})


# 0.35.0 — final compatibility fragments (kept after legacy alias updates).
DEFAULT_EN_US.update({
    "legacy.fragment_and": "and",
    "legacy.fragment_or": "or",
    "legacy.fragment_tags_period": "tags.",
    "legacy.fragment_field_period": "field.",
    "legacy.changed_lower": "changed",
})
DEFAULT_FR_CA.update({
    "legacy.fragment_and": "et",
    "legacy.fragment_or": "ou",
    "legacy.fragment_tags_period": "étiquettes.",
    "legacy.fragment_field_period": "champ.",
    "legacy.changed_lower": "modifié",
})

DEFAULT_EN_US.update({'research.stage_queued': 'Waiting for an execution slot', 'research.stage_starting': 'Starting the Research pipeline', 'research.stage_query_metadata': 'Interpreting the question', 'research.stage_retrieval': 'Retrieving candidate evidence', 'research.stage_deduplicate': 'Deduplicating evidence', 'research.stage_rerank': 'Reranking candidate evidence', 'research.stage_context': 'Packaging evidence context', 'research.stage_generation': 'Generating the answer', 'research.stage_bind_sources': 'Binding claims to sources', 'research.stage_response_cache': 'Writing the response cache', 'research.stage_auto_grade': 'Evaluating the answer', 'research.stage_completed': 'Research complete', 'research.stage_cancelled': 'Research cancelled', 'research.stage_failed': 'Research failed'})
DEFAULT_FR_CA.update({'research.stage_queued': 'En attente d’une place d’exécution', 'research.stage_starting': 'Démarrage du pipeline de recherche', 'research.stage_query_metadata': 'Interprétation de la question', 'research.stage_retrieval': 'Repérage des preuves candidates', 'research.stage_deduplicate': 'Déduplication des preuves', 'research.stage_rerank': 'Reclassement des preuves candidates', 'research.stage_context': 'Préparation du contexte de preuves', 'research.stage_generation': 'Génération de la réponse', 'research.stage_bind_sources': 'Liaison des affirmations aux sources', 'research.stage_response_cache': 'Écriture dans la mémoire cache des réponses', 'research.stage_auto_grade': 'Évaluation de la réponse', 'research.stage_completed': 'Recherche terminée', 'research.stage_cancelled': 'Recherche annulée', 'research.stage_failed': 'Échec de la recherche'})


# 0.35.0 — Québec French consistency pass.  Keep this last so the canonical
# built-in dictionary uses one vocabulary across old and new surfaces.
DEFAULT_FR_CA.update({
    "vector.embedding_setup_help": "Choisissez comment les nouvelles fiches de cette collection recevront leurs vecteurs.",
    "vector.provider_precomputed_help": "Les fiches doivent déjà contenir des vecteurs; la recherche sémantique par requête n’est pas disponible.",
    "vector.embedding_model_help": "Ce paramètre est verrouillé dès que la collection contient des fiches.",
    "vector.create_large_sync_help": "Comme cette sélection contient {count} fiches, DerridAI la synchronisera par lots au premier plan après la création. Gardez cet onglet ouvert jusqu’à la fin.",
    "vector.unsynced_changes_help": "Il s’agit des fiches de l’espace de travail modifiées depuis leur dernière synchronisation confirmée, ainsi que de celles dont DerridAI a confirmé l’absence dans la collection sélectionnée. Retirer un élément ne masque que sa version actuelle; une modification ultérieure le remettra dans la file.",
    "vector.no_unsynced_changes_help": "DerridAI n’a trouvé aucune fiche chargée modifiée depuis sa dernière synchronisation ni confirmée absente de cette collection.",
    "vector.embedding_locked_help": "Les paramètres de vectorisation sont verrouillés après l’ajout de fiches. Créez une nouvelle collection vide pour les modifier.",
    "vector.import_export": "Importer et exporter des fiches",
    "vector.import_export_help": "Synchronisez les fiches JSONL chargées vers cette collection, ou exportez les fiches de la collection vers un JSONL propre. L’export ne modifie pas la collection.",
    "vector.page_export_help": "Ouvrez uniquement les fiches visibles sur cette page paginée dans un onglet JSONL temporaire. Il ne s’agit pas d’un export complet de la collection.",
    "vector.semantic_search_help": "Trouvez des fiches par leur sens à l’aide du fournisseur de vectorisation configuré pour cette collection.",
    "vector.language_derive_help": "Créez des collections anglaise et française séparées en acheminant les fiches selon les métadonnées document_language.",
    "vector.select_collection_help": "Choisissez une collection dans la liste pour gérer ses paramètres, synchroniser des fiches, effectuer des recherches ou parcourir son contenu.",
    "research.all_records": "Toutes les fiches",
    "vector.browse_works_help": "Ouvrez une œuvre pour ne parcourir que ses fiches dans cette collection.",
    "vector.open_work_records": "Ouvrir les fiches",
    "research.redirect_database": "L’espace Recherche nécessite une base de données du corpus. Ouverture de la page des bases de données afin que vous puissiez en créer, en restaurer ou en sélectionner une.",
    "legacy.reranker": "Module de reclassement",
    "legacy.default_reranker": "Module de reclassement par défaut",
    "research.stage_starting": "Démarrage du processus de recherche",
})


# 0.35.0 — localized operational status text used by the compatibility UI.
DEFAULT_EN_US.update({
    "operations.waiting_to_start": "Waiting to start",
    "operations.cancelled_provider_wait": "Cancelled while waiting for provider slot",
    "operations.cancelled_ollama_wait": "Cancelled while waiting for Ollama slot",
    "operations.cancelled_queue": "Cancelled while queued",
    "operations.rag_cancelled": "RAG pipeline cancelled",
    "operations.rag_complete_grade_failed": "RAG pipeline complete; auto-grade failed",
    "operations.rag_complete_cache_failed": "RAG pipeline complete; response-cache write failed",
    "operations.rag_complete_grade": "RAG pipeline and auto-grade complete",
    "operations.rag_complete": "RAG pipeline complete",
    "operations.rag_job_cancelled": "RAG job cancelled",
    "dynamic.grading_progress": "Grading {current} of {total} · {question}",
    "dynamic.translating_interface": "Translating {count} interface strings to {locale}",
    "dynamic.running_operation": "Running {label}",
    "dynamic.completed_grading": "Completed · {graded} graded, {failed} failed",
    "dynamic.completed_works": "Completed · {works} works, {failed} failed",
    "dynamic.waiting_provider_active": "Waiting for provider slot: {active} active / {allowed} allowed",
    "dynamic.waiting_provider_active_paren": "Waiting for provider slot ({active}/{allowed} active)",
    "dynamic.waiting_ollama_active": "Waiting for Ollama slot: {active} active / {allowed} allowed",
})
DEFAULT_FR_CA.update({
    "operations.waiting_to_start": "En attente de démarrage",
    "operations.cancelled_provider_wait": "Annulé pendant l’attente d’une place chez le fournisseur",
    "operations.cancelled_ollama_wait": "Annulé pendant l’attente d’une place Ollama",
    "operations.cancelled_queue": "Annulé pendant l’attente dans la file",
    "operations.rag_cancelled": "Processus RAG annulé",
    "operations.rag_complete_grade_failed": "Processus RAG terminé; échec de l’évaluation automatique",
    "operations.rag_complete_cache_failed": "Processus RAG terminé; échec de l’écriture dans la mémoire cache des réponses",
    "operations.rag_complete_grade": "Processus RAG et évaluation automatique terminés",
    "operations.rag_complete": "Processus RAG terminé",
    "operations.rag_job_cancelled": "Tâche RAG annulée",
    "dynamic.grading_progress": "Évaluation {current} sur {total} · {question}",
    "dynamic.translating_interface": "Traduction de {count} chaînes d’interface vers {locale}",
    "dynamic.running_operation": "Exécution : {label}",
    "dynamic.completed_grading": "Terminé · {graded} évaluations réussies, {failed} échecs",
    "dynamic.completed_works": "Terminé · {works} œuvres traitées, {failed} échecs",
    "dynamic.waiting_provider_active": "En attente d’une place chez le fournisseur : {active} actives / {allowed} permises",
    "dynamic.waiting_provider_active_paren": "En attente d’une place chez le fournisseur ({active}/{allowed} actives)",
    "dynamic.waiting_ollama_active": "En attente d’une place Ollama : {active} actives / {allowed} permises",
})


# 0.35.5 — unified Research result and Response FAQ presentation.
DEFAULT_EN_US.update({
    "faq.page_kicker": "Research archive",
    "faq.page_subtitle": "Revisit cached answers with the same source-bound evidence experience used in Research.",
    "faq.new_research": "New research",
    "faq.browse_controls": "Response FAQ controls",
    "faq.search_label": "Search saved questions",
    "faq.search_placeholder": "Search question text…",
    "faq.cached_responses": "cached responses",
    "faq.matches": "matches",
    "faq.loading": "Loading cached research responses…",
    "faq.no_matches": "No saved questions match this search",
    "faq.no_matches_help": "Try broader wording or clear the search.",
    "faq.empty_title": "No cached research responses yet",
    "faq.empty_help": "Completed cached Research runs will appear here with their evidence bindings.",
    "faq.saved_responses": "Saved responses",
    "faq.results": "results",
    "faq.untitled_question": "Untitled question",
    "faq.saved_grade": "Saved grade",
    "faq.page_of": "Page {page} of {pages}",
    "faq.cached_result": "Cached result",
    "faq.run_provenance": "Run provenance & saved evaluation",
    "faq.run_provenance_help": "Inspect retrieval diagnostics, query metadata, and retained grades without obscuring the answer.",
    "faq.saved_grades": "Saved LLM grades",
    "research.retrieval_diagnostics": "Retrieval diagnostics",
    "research.query_metadata": "Query metadata",
    "research.result_unavailable": "This Research run has no result identifier.",
    "permissions.research_result_denied": "Your role cannot open Research results.",
    "permissions.faq_denied": "Your role cannot open Response FAQ.",
})
DEFAULT_FR_CA.update({
    "faq.page_kicker": "Archives de recherche",
    "faq.page_subtitle": "Revenez aux réponses mises en cache avec la même présentation des preuves liées aux sources que dans l’espace Recherche.",
    "faq.new_research": "Nouvelle recherche",
    "faq.browse_controls": "Commandes de la FAQ des réponses",
    "faq.search_label": "Rechercher dans les questions enregistrées",
    "faq.search_placeholder": "Rechercher dans le texte des questions…",
    "faq.cached_responses": "réponses mises en cache",
    "faq.matches": "résultats correspondants",
    "faq.loading": "Chargement des réponses de recherche mises en cache…",
    "faq.no_matches": "Aucune question enregistrée ne correspond à cette recherche",
    "faq.no_matches_help": "Essayez des termes plus généraux ou effacez la recherche.",
    "faq.empty_title": "Aucune réponse de recherche mise en cache",
    "faq.empty_help": "Les recherches terminées et mises en cache apparaîtront ici avec leurs liaisons aux preuves.",
    "faq.saved_responses": "Réponses enregistrées",
    "faq.results": "résultats",
    "faq.untitled_question": "Question sans titre",
    "faq.saved_grade": "Évaluation enregistrée",
    "faq.page_of": "Page {page} sur {pages}",
    "faq.cached_result": "Résultat mis en cache",
    "faq.run_provenance": "Provenance de l’exécution et évaluation enregistrée",
    "faq.run_provenance_help": "Consultez le diagnostic de repérage, les métadonnées de la requête et les évaluations conservées sans masquer la réponse.",
    "faq.saved_grades": "Évaluations LLM enregistrées",
    "research.retrieval_diagnostics": "Diagnostic de repérage",
    "research.provider": "Fournisseur",
    "research.query_metadata": "Métadonnées de la requête",
    "research.result_unavailable": "Cette exécution de recherche ne possède aucun identifiant de résultat.",
    "permissions.research_result_denied": "Votre rôle ne permet pas d’ouvrir les résultats de recherche.",
    "permissions.faq_denied": "Votre rôle ne permet pas d’ouvrir la FAQ des réponses.",
})


# 0.35.10 — Record Player: Vue-native record workspace.
DEFAULT_EN_US.update({
    "record.workspace_kicker": "Corpus record",
    "record.navigation": "Record navigation",
    "record.previous": "Previous record",
    "record.next": "Next record",
    "record.position_of": "{current} of {total}",
    "record.untitled": "Untitled record",
    "record.more_actions": "More record actions",
    "record.add_evidence": "Add evidence",
    "record.evidence_selected": "Evidence selected",
    "record.edit": "Edit record",
    "record.copy_inline": "Copy inline citation",
    "record.copy_full": "Copy full citation",
    "record.copy_json": "Copy record JSON",
    "record.add_selection": "Add to selection",
    "record.remove_selection": "Remove from selection",
    "record.review_llm": "Review with LLM",
    "record.upsert": "Upsert record",
    "record.clean_ocr": "Clean OCR artifacts",
    "record.history_undo": "History & undo",
    "record.pdf_explorer": "PDF Explorer",
    "record.extracted_text": "Extracted text",
    "record.researcher_summary": "Researcher summary",
    "record.words": "words",
    "record.characters": "characters",
    "record.matches": "matches",
    "record.find_text": "Find in record text",
    "record.clear_find": "Clear find query",
    "record.focus_mode": "Focus mode",
    "record.exit_focus": "Exit focus",
    "record.text": "Record text",
    "record.selection_actions": "Selected text actions",
    "record.provenance_kicker": "Attribution structure",
    "record.provenance": "Provenance",
    "record.provenance_empty": "No structured attribution fields are recorded for this passage.",
    "record.add_term": "Add {label}",
    "record.remove_term": "Remove {value}",
    "record.source_documents": "Source documents",
    "record.pdf_links": "PDF links",
    "record.pdf_page": "Page {page}",
    "record.open_page": "Open page",
    "record.no_pdf_links": "No PDF pages are linked to this record.",
    "record.link_current_pdf": "Link current PDF page",
    "record.remove_all_pdf": "Remove all PDF links",
    "record.audit_trail": "Audit trail",
    "record.change_history": "Change history",
    "record.no_history": "No tracked record changes yet.",
    "record.open_history": "Open history & undo",
    "record.edit_kicker": "Record metadata",
    "record.unsaved_fields": "{count} unsaved fields",
    "record.no_unsaved_changes": "No unsaved changes",
    "record.comma_separated": "Separate multiple values with commas.",
    "record.sparse_save_help": "Only changed fields will be saved and added to the audit trail.",
    "record.group_source": "Source",
    "record.group_discourse": "Discourse",
    "record.group_quotation": "Quotation provenance",
    "record.group_indexing": "Indexing",
    "record.group_quality": "Quality & review",
    "record.group_language": "Language & translation",
    "record.group_citation": "Citation",
    "record.group_text": "Text",
    "record.group_other": "Other fields",
    "record.inspector": "Record inspector",
    "record.inspector_sections": "Record inspector sections",
    "record.tab_overview": "Overview",
    "record.tab_provenance": "Provenance",
    "record.tab_indexing": "Indexing",
    "record.tab_pdf": "PDFs",
    "record.tab_annotations": "Annotations",
    "record.tab_history": "History",
    "record.record_context": "Record context",
    "record.overview": "Overview",
    "record.quotation_provenance": "Quotation provenance",
    "record.citations": "Citations",
    "record.inline_citation": "Inline citation",
    "record.full_citation": "Full citation",
    "record.indexing_kicker": "Research index",
    "record.indexing": "Indexing",
    "record.loading": "Loading record…",
    "record.load_failed": "Could not load record",
    "record.no_record_selected": "No record selected",
    "record.no_record_help": "Choose a record from Search, Works, or Records.",
    "record.primary_text": "Primary text",
    "record.secondary_text": "Secondary text",
    "record.translation": "Translation",
    "record.needs_review": "Needs review",
    "record.database_record": "Database record",
    "record.collection": "Collection",
    "record.show_inspector": "Show inspector",
    "record.hide_inspector": "Hide inspector",
    "record.inline_citation_copied": "Inline citation copied",
    "record.full_citation_copied": "Full citation copied",
    "record.copy_failed": "Could not copy citation",
    "record.record_json": "record",
    "record.saved": "Record changes saved",
    "record.no_changes": "No record fields changed",
    "record.open_pdf_first": "Open {file} in PDF Explorer to jump to the linked page.",
    "annotations.empty": "Add a quotation, note, or tag first.",
    "permissions.record_edit_denied": "Your role cannot edit local records.",
    "permissions.annotations_denied": "Your role cannot create annotations.",
    "permissions.corpus_denied": "Your role cannot manage corpus databases.",
    "permissions.pdf_denied": "Your role cannot open PDF Explorer.",
    "ui.add": "Add",
    "ui.copy": "Copy",
    "ui.reset": "Reset",
    "ui.retry": "Retry",
    "annotations.add_note": "Add note",
    "record.resize_inspector": "Resize record inspector",
    "ui.not_set": "Not set",
})
DEFAULT_FR_CA.update({
    "record.workspace_kicker": "Fiche du corpus",
    "record.navigation": "Navigation entre les fiches",
    "record.previous": "Fiche précédente",
    "record.next": "Fiche suivante",
    "record.position_of": "{current} sur {total}",
    "record.untitled": "Fiche sans titre",
    "record.more_actions": "Autres actions sur la fiche",
    "record.add_evidence": "Ajouter aux preuves",
    "record.evidence_selected": "Preuve sélectionnée",
    "record.edit": "Modifier la fiche",
    "record.copy_inline": "Copier la citation dans le texte",
    "record.copy_full": "Copier la référence complète",
    "record.copy_json": "Copier la fiche en JSON",
    "record.add_selection": "Ajouter à la sélection",
    "record.remove_selection": "Retirer de la sélection",
    "record.review_llm": "Réviser avec un LLM",
    "record.upsert": "Synchroniser la fiche",
    "record.clean_ocr": "Nettoyer les artéfacts de ROC",
    "record.history_undo": "Historique et annulation",
    "record.pdf_explorer": "Explorateur PDF",
    "record.extracted_text": "Texte extrait",
    "record.researcher_summary": "Résumé pour la recherche",
    "record.words": "mots",
    "record.characters": "caractères",
    "record.matches": "correspondances",
    "record.find_text": "Rechercher dans le texte de la fiche",
    "record.clear_find": "Effacer la recherche dans la fiche",
    "record.focus_mode": "Mode concentration",
    "record.exit_focus": "Quitter le mode concentration",
    "record.text": "Texte de la fiche",
    "record.selection_actions": "Actions sur le texte sélectionné",
    "record.provenance_kicker": "Structure d’attribution",
    "record.provenance": "Provenance",
    "record.provenance_empty": "Aucun champ d’attribution structurée n’est consigné pour ce passage.",
    "record.add_term": "Ajouter : {label}",
    "record.remove_term": "Retirer {value}",
    "record.source_documents": "Documents sources",
    "record.pdf_links": "Liens PDF",
    "record.pdf_page": "Page {page}",
    "record.open_page": "Ouvrir la page",
    "record.no_pdf_links": "Aucune page PDF n’est liée à cette fiche.",
    "record.link_current_pdf": "Lier la page PDF actuelle",
    "record.remove_all_pdf": "Retirer tous les liens PDF",
    "record.audit_trail": "Piste d’audit",
    "record.change_history": "Historique des modifications",
    "record.no_history": "Aucune modification suivie pour cette fiche.",
    "record.open_history": "Ouvrir l’historique et les options d’annulation",
    "record.edit_kicker": "Métadonnées de la fiche",
    "record.unsaved_fields": "{count} champs non enregistrés",
    "record.no_unsaved_changes": "Aucune modification non enregistrée",
    "record.comma_separated": "Séparez les valeurs multiples par des virgules.",
    "record.sparse_save_help": "Seuls les champs modifiés seront enregistrés et ajoutés à la piste d’audit.",
    "record.group_source": "Source",
    "record.group_discourse": "Discours",
    "record.group_quotation": "Provenance de la citation",
    "record.group_indexing": "Indexation",
    "record.group_quality": "Qualité et révision",
    "record.group_language": "Langue et traduction",
    "record.group_citation": "Référence",
    "record.group_text": "Texte",
    "record.group_other": "Autres champs",
    "record.inspector": "Volet d’inspection de la fiche",
    "record.inspector_sections": "Sections du volet d’inspection de la fiche",
    "record.tab_overview": "Aperçu",
    "record.tab_provenance": "Provenance",
    "record.tab_indexing": "Indexation",
    "record.tab_pdf": "PDF",
    "record.tab_annotations": "Annotations",
    "record.tab_history": "Historique",
    "record.record_context": "Contexte de la fiche",
    "record.overview": "Aperçu",
    "record.quotation_provenance": "Provenance de la citation",
    "record.citations": "Références",
    "record.inline_citation": "Citation dans le texte",
    "record.full_citation": "Référence complète",
    "record.indexing_kicker": "Index de recherche",
    "record.indexing": "Indexation",
    "record.loading": "Chargement de la fiche…",
    "record.load_failed": "Impossible de charger la fiche",
    "record.no_record_selected": "Aucune fiche sélectionnée",
    "record.no_record_help": "Choisissez une fiche depuis Recherche globale, Œuvres ou Fiches.",
    "record.primary_text": "Texte principal",
    "record.secondary_text": "Texte secondaire",
    "record.translation": "Traduction",
    "record.needs_review": "À réviser",
    "record.database_record": "Fiche de la base de données",
    "record.collection": "Collection",
    "record.show_inspector": "Afficher le volet d’inspection",
    "record.hide_inspector": "Masquer le volet d’inspection",
    "record.inline_citation_copied": "Citation dans le texte copiée",
    "record.full_citation_copied": "Référence complète copiée",
    "record.copy_failed": "Impossible de copier la référence",
    "record.record_json": "fiche",
    "record.saved": "Modifications de la fiche enregistrées",
    "record.no_changes": "Aucun champ de la fiche n’a été modifié",
    "record.open_pdf_first": "Ouvrez {file} dans l’Explorateur PDF pour accéder à la page liée.",
    "annotations.empty": "Ajoutez d’abord une citation, une note ou une étiquette.",
    "permissions.record_edit_denied": "Votre rôle ne permet pas de modifier les fiches locales.",
    "permissions.annotations_denied": "Votre rôle ne permet pas de créer des annotations.",
    "permissions.corpus_denied": "Votre rôle ne permet pas de gérer les bases de données du corpus.",
    "permissions.pdf_denied": "Votre rôle ne permet pas d’ouvrir l’Explorateur PDF.",
    "ui.add": "Ajouter",
    "ui.copy": "Copier",
    "ui.reset": "Réinitialiser",
    "ui.retry": "Réessayer",
    "annotations.add_note": "Ajouter une note",
    "record.resize_inspector": "Redimensionner le volet d’inspection",
    "ui.not_set": "Non défini",
})


# 0.35.10 maintenance — polished Response FAQ archive and run-detail labels.
DEFAULT_EN_US.update({
    "faq.library_kicker": "Library",
    "faq.library_title": "Saved questions",
    "faq.library_help": "Scan saved questions first, then reopen an answer with its evidence bindings.",
    "faq.saved_on": "Saved",
    "faq.evidence_bound": "Evidence bound",
    "faq.elapsed": "Elapsed",
    "faq.retrieved": "Retrieved",
    "faq.deduplicated": "After deduplication",
    "faq.reranked": "After reranking",
    "faq.run_summary": "Run summary",
    "faq.run_summary_help": "A compact view of what happened before the answer was generated.",
    "faq.retrieval_help": "The retrieval settings and counts retained with this cached answer.",
    "faq.query_help": "How the question was interpreted and routed for this run.",
    "faq.saved_grades_help": "Evaluations retained with this cached response.",
    "faq.technical_metadata": "Technical metadata",
    "faq.select_response": "Choose a saved response",
    "faq.select_response_help": "Select a question from the library to reopen its answer and evidence bindings.",
    "faq.meta_search_types": "Search routes",
    "faq.meta_k": "Candidates retained",
    "faq.meta_fetch_k": "Candidate pool",
    "faq.meta_lambda_mult": "MMR relevance balance",
    "faq.meta_rrf_k": "Rank-fusion smoothing",
    "faq.meta_reranker": "Reranker",
    "faq.meta_rerank_top_n": "Rerank top N",
    "faq.meta_effective_rerank_top_n": "Evidence after reranking",
    "faq.meta_query_decomposition": "Query decomposition",
    "faq.meta_query_decomposition_num_predict": "Decomposition token limit",
    "faq.meta_skip_retrieval": "Selected-evidence-only run",
    "faq.meta_selected_evidence_count": "Pinned evidence",
    "faq.meta_response_language": "Response language",
    "faq.meta_evidence_record_char_limit": "Characters per evidence record",
    "faq.meta_evidence_total_char_limit": "Total evidence characters",
    "faq.meta_raw_count": "Retrieved candidates",
    "faq.meta_deduplicated_count": "After deduplication",
    "faq.meta_reranked_count": "After reranking",
    "faq.meta_prompt_query": "Retrieval query",
    "faq.meta_prompt_query_fr": "French retrieval query",
    "faq.meta_prompt_instructions": "Prompt instructions",
    "faq.meta_limit_retrieval": "Retrieval limit",
    "faq.meta_limit_reranking": "Reranking limit",
    "faq.meta_document_languages": "Document languages",
})
DEFAULT_FR_CA.update({
    "faq.library_kicker": "Bibliothèque",
    "faq.library_title": "Questions enregistrées",
    "faq.library_help": "Parcourez d’abord les questions enregistrées, puis rouvrez une réponse avec ses liaisons aux preuves.",
    "faq.saved_on": "Enregistré le",
    "faq.evidence_bound": "Preuves liées",
    "faq.elapsed": "Durée",
    "faq.retrieved": "Repérées",
    "faq.deduplicated": "Après déduplication",
    "faq.reranked": "Après reclassement",
    "faq.run_summary": "Résumé de l’exécution",
    "faq.run_summary_help": "Vue concise de ce qui s’est produit avant la génération de la réponse.",
    "faq.retrieval_help": "Paramètres et dénombrements de repérage conservés avec cette réponse mise en cache.",
    "faq.query_help": "Façon dont la question a été interprétée et acheminée pour cette exécution.",
    "faq.saved_grades_help": "Évaluations conservées avec cette réponse mise en cache.",
    "faq.technical_metadata": "Métadonnées techniques",
    "faq.select_response": "Choisissez une réponse enregistrée",
    "faq.select_response_help": "Sélectionnez une question dans la bibliothèque pour rouvrir sa réponse et ses liaisons aux preuves.",
    "faq.meta_search_types": "Voies de recherche",
    "faq.meta_k": "Candidats conservés",
    "faq.meta_fetch_k": "Ensemble de candidats",
    "faq.meta_lambda_mult": "Équilibre de pertinence MMR",
    "faq.meta_rrf_k": "Lissage de la fusion des rangs",
    "faq.meta_reranker": "Module de reclassement",
    "faq.meta_rerank_top_n": "Nombre à reclasser",
    "faq.meta_effective_rerank_top_n": "Preuves après reclassement",
    "faq.meta_query_decomposition": "Décomposition de la requête",
    "faq.meta_query_decomposition_num_predict": "Limite de jetons pour la décomposition",
    "faq.meta_skip_retrieval": "Exécution avec preuves sélectionnées seulement",
    "faq.meta_selected_evidence_count": "Preuves épinglées",
    "faq.meta_response_language": "Langue de la réponse",
    "faq.meta_evidence_record_char_limit": "Caractères par fiche de preuve",
    "faq.meta_evidence_total_char_limit": "Nombre total de caractères de preuve",
    "faq.meta_raw_count": "Candidats repérés",
    "faq.meta_deduplicated_count": "Après déduplication",
    "faq.meta_reranked_count": "Après reclassement",
    "faq.meta_prompt_query": "Requête de repérage",
    "faq.meta_prompt_query_fr": "Requête de repérage en français",
    "faq.meta_prompt_instructions": "Consignes de l’invite",
    "faq.meta_limit_retrieval": "Limite de repérage",
    "faq.meta_limit_reranking": "Limite de reclassement",
    "faq.meta_document_languages": "Langues des documents",
})


# 0.35.10 maintenance — Record inspector refinement and Response FAQ archive drawer.
DEFAULT_EN_US.update({
    "record.provenance_help": "A structured attribution view showing who speaks, whose position is represented, the stance taken, and its target.",
    "record.attribution_path": "Attribution path",
    "record.provenance_fields": "{count} attribution fields",
    "record.status": "Record status",
    "faq.archive_help": "Scan or search saved questions, then open one to revisit its answer and evidence.",
    "faq.browse_archive": "Browse saved research",
    "faq.find_question": "Find a question",
    "faq.find_another_question": "Find another question",
    "faq.current_question": "Current question",
    "faq.questions_label": "Questions",
    "faq.questions_help": "Select a question to open its saved answer.",
    "faq.saved_questions": "saved questions",
    "faq.question_matches": "matching questions",
    "faq.evidence_short": "evidence",
    "faq.current_response": "Current saved response",
})
DEFAULT_FR_CA.update({
    "record.provenance_help": "Vue structurée de l’attribution indiquant qui parle, quelle position est représentée, la posture adoptée et sa cible.",
    "record.attribution_path": "Parcours d’attribution",
    "record.provenance_fields": "{count} champs d’attribution",
    "record.status": "État de la fiche",
    "faq.archive_help": "Parcourez ou recherchez les questions enregistrées, puis ouvrez-en une pour revoir sa réponse et ses preuves.",
    "faq.browse_archive": "Parcourir les recherches enregistrées",
    "faq.find_question": "Rechercher une question",
    "faq.find_another_question": "Rechercher une autre question",
    "faq.current_question": "Question actuelle",
    "faq.questions_label": "Questions",
    "faq.questions_help": "Sélectionnez une question pour ouvrir sa réponse enregistrée.",
    "faq.saved_questions": "questions enregistrées",
    "faq.question_matches": "questions correspondantes",
    "faq.evidence_short": "preuves",
    "faq.current_response": "Réponse enregistrée affichée",
})


# 0.35.12 — Tongue Twister: localization studio, validated installs, and flag library.
DEFAULT_EN_US.update({
    "language.workspace_kicker": "Localization studio",
    "language.page_description_modern": "Manage interface locales from one bilingual translation workspace. English is the canonical source; installed locales stay editable and auditable.",
    "language.locales": "Locales",
    "language.source_strings": "English strings",
    "language.localization_summary": "Localization summary",
    "language.locale_library": "Locale library",
    "language.search_locales": "Search locales",
    "language.no_locale_matches": "No installed locales match this search.",
    "language.built_in": "Built-in",
    "language.custom": "Custom",
    "language.canonical_source": "Canonical source",
    "language.translation_target": "Translation target",
    "language.interface_strings": "interface strings",
    "language.coverage": "Coverage",
    "language.matches_english": "Matches English",
    "language.missing": "Missing",
    "language.unsaved_changes": "Unsaved changes",
    "language.locale_identity": "Locale identity",
    "language.locale_icon": "Locale icon",
    "language.flag_library_help": "Choose from the country flag library or use the neutral globe for languages without a country-specific locale.",
    "language.source_language": "Source language",
    "language.source_language_help": "All installed translations are keyed to the canonical English interface set.",
    "language.search_strings": "Search keys, English source, or translation…",
    "language.translation_filters": "Translation filters",
    "language.filled": "Filled",
    "language.localized": "Localized",
    "language.translation_editor": "Translation editor",
    "language.key_context": "Key & context",
    "language.english_source": "English source",
    "language.english_value": "English value",
    "language.english_fallback_note": "Currently matches the English source",
    "language.no_string_matches": "No interface strings match these filters.",
    "language.add_source_key": "Add canonical English key",
    "language.add_source_key_help": "English defines the canonical key set. New keys become visible as English fallbacks in installed locales until translated.",
    "language.description_record": "Record workspace text",
    "language.install_dictionary_modern": "Translate & install locale",
    "language.install_help_modern": "DerridAI translates the complete canonical English interface set first, validates every key and placeholder, then installs the locale only if translation succeeds.",
    "language.english_source_set": "Source: English",
    "language.source_key_count": "{count} interface strings will be translated.",
    "language.canonical": "Canonical",
    "language.identity_section_help_modern": "Use a BCP 47 locale code. Script-aware locales such as zh-Hant-TW are supported.",
    "language.locale_code_help_modern": "Examples: de-DE, pt-BR, zh-Hant-TW.",
    "language.translation_section_help_modern": "DerridAI checks the provider before starting. Translation runs in bounded batches so smaller local models do not receive the entire dictionary at once.",
    "language.atomic_install": "Validated before installation",
    "language.atomic_install_help": "Missing keys, damaged placeholders, truncated JSON, or an effectively untranslated response stop the install and produce a clear error.",
    "language.background_translation_help_modern": "Progress remains visible here and in Operations. The locale appears only after the complete translation passes validation.",
    "language.translate_install": "Translate & install",
    "language.checking_provider": "Checking provider…",
    "language.translation_started_modern": "Translation started. DerridAI is translating the complete English interface set before installing the locale.",
    "language.translating_install": "Translating before installation",
    "language.translation_in_progress": "Translating the canonical English dictionary…",
    "language.translation_complete": "Language translated and installed.",
    "language.translation_failed": "Translation failed.",
    "language.translation_failed_detail": "The selected model/provider could not install this language: {message}",
    "language.provider_unavailable": "The selected provider cannot be reached: {message}",
    "language.provider_unavailable_short": "provider unavailable",
    "language.locale_already_installed": "That locale is already installed. Select it from the locale list to edit it.",
    "language.leave_install_title": "Leave language installation?",
    "language.leave_install_help": "Manage provider profiles opens another page. Values entered in this installation form will be discarded.",
    "language.leave_manage_providers": "Leave and manage providers",
    "language.unsaved_title": "Save changes before switching locale?",
    "language.unsaved_help": "This locale has unsaved dictionary or identity changes.",
    "language.discard_switch": "Discard & switch",
    "language.save_switch": "Save & switch",
    "language.choose_flag": "Choose a country flag",
    "language.flag_library": "Country flag library",
    "language.search_flags": "Search countries…",
    "language.no_country_flag": "No country flag",
    "language.use_locale_region": "Use locale region",
    "language.no_flag_matches": "No countries match this search.",
    "ui.all": "All",
    "ui.stay": "Stay here",
})
DEFAULT_FR_CA.update({
    "language.workspace_kicker": "Studio de localisation",
    "language.page_description_modern": "Gérez les paramètres régionaux de l’interface dans un même espace de traduction bilingue. L’anglais constitue la source canonique; les paramètres régionaux installés demeurent modifiables et vérifiables.",
    "language.locales": "Paramètres régionaux",
    "language.source_strings": "Chaînes anglaises",
    "language.localization_summary": "Résumé de la localisation",
    "language.locale_library": "Bibliothèque de paramètres régionaux",
    "language.search_locales": "Rechercher des paramètres régionaux",
    "language.no_locale_matches": "Aucun paramètre régional installé ne correspond à cette recherche.",
    "language.built_in": "Intégré",
    "language.custom": "Personnalisé",
    "language.canonical_source": "Source canonique",
    "language.translation_target": "Cible de traduction",
    "language.interface_strings": "chaînes d’interface",
    "language.coverage": "Couverture",
    "language.matches_english": "Identique à l’anglais",
    "language.missing": "Manquantes",
    "language.unsaved_changes": "Modifications non enregistrées",
    "language.locale_identity": "Identité du paramètre régional",
    "language.locale_icon": "Icône du paramètre régional",
    "language.flag_library_help": "Choisissez un drapeau dans la bibliothèque ou utilisez le globe neutre pour les langues sans paramètre régional propre à un pays.",
    "language.source_language": "Langue source",
    "language.source_language_help": "Toutes les traductions installées sont rattachées à l’ensemble canonique de l’interface anglaise.",
    "language.search_strings": "Rechercher des clés, la source anglaise ou la traduction…",
    "language.translation_filters": "Filtres de traduction",
    "language.filled": "Renseignées",
    "language.localized": "Localisées",
    "language.translation_editor": "Éditeur de traduction",
    "language.key_context": "Clé et contexte",
    "language.english_source": "Source anglaise",
    "language.english_value": "Valeur anglaise",
    "language.english_fallback_note": "Correspond actuellement à la source anglaise",
    "language.no_string_matches": "Aucune chaîne d’interface ne correspond à ces filtres.",
    "language.add_source_key": "Ajouter une clé anglaise canonique",
    "language.add_source_key_help": "L’anglais définit l’ensemble canonique des clés. Les nouvelles clés apparaissent comme valeurs anglaises de repli dans les paramètres régionaux installés jusqu’à leur traduction.",
    "language.description_record": "Texte de l’espace de fiche",
    "language.install_dictionary_modern": "Traduire et installer le paramètre régional",
    "language.install_help_modern": "DerridAI traduit d’abord l’ensemble complet de l’interface anglaise canonique, valide chaque clé et chaque variable, puis n’installe le paramètre régional que si la traduction réussit.",
    "language.english_source_set": "Source : anglais (États-Unis)",
    "language.source_key_count": "{count} chaînes d’interface seront traduites.",
    "language.canonical": "Canonique",
    "language.identity_section_help_modern": "Utilisez une balise de langue BCP 47. Les paramètres régionaux avec écriture explicite, comme zh-Hant-TW, sont pris en charge.",
    "language.locale_code_help_modern": "Exemples : de-DE, pt-BR, zh-Hant-TW.",
    "language.translation_section_help_modern": "DerridAI vérifie le fournisseur avant de démarrer. La traduction s’effectue par lots bornés afin que les petits modèles locaux ne reçoivent pas tout le dictionnaire en une seule fois.",
    "language.atomic_install": "Validation avant installation",
    "language.atomic_install_help": "Une clé manquante, une variable endommagée, un JSON tronqué ou une réponse pratiquement non traduite interrompt l’installation et produit une erreur claire.",
    "language.background_translation_help_modern": "La progression reste visible ici et dans Opérations. Le paramètre régional n’apparaît qu’une fois la traduction complète validée.",
    "language.translate_install": "Traduire et installer",
    "language.checking_provider": "Vérification du fournisseur…",
    "language.translation_started_modern": "La traduction a démarré. DerridAI traduit l’ensemble complet de l’interface anglaise avant d’installer le paramètre régional.",
    "language.translating_install": "Traduction avant installation",
    "language.translation_in_progress": "Traduction du dictionnaire anglais canonique…",
    "language.translation_complete": "Langue traduite et installée.",
    "language.translation_failed": "Échec de la traduction.",
    "language.translation_failed_detail": "Le modèle ou fournisseur sélectionné n’a pas pu installer cette langue : {message}",
    "language.provider_unavailable": "Le fournisseur sélectionné est inaccessible : {message}",
    "language.provider_unavailable_short": "fournisseur inaccessible",
    "language.locale_already_installed": "Ce paramètre régional est déjà installé. Sélectionnez-le dans la liste pour le modifier.",
    "language.leave_install_title": "Quitter l’installation de la langue?",
    "language.leave_install_help": "La gestion des profils fournisseur ouvre une autre page. Les valeurs saisies dans ce formulaire d’installation seront perdues.",
    "language.leave_manage_providers": "Quitter et gérer les fournisseurs",
    "language.unsaved_title": "Enregistrer les modifications avant de changer de paramètre régional?",
    "language.unsaved_help": "Ce paramètre régional comporte des modifications non enregistrées au dictionnaire ou à son identité.",
    "language.discard_switch": "Ignorer et changer",
    "language.save_switch": "Enregistrer et changer",
    "language.choose_flag": "Choisir un drapeau de pays",
    "language.flag_library": "Bibliothèque de drapeaux de pays",
    "language.search_flags": "Rechercher des pays…",
    "language.no_country_flag": "Aucun drapeau de pays",
    "language.use_locale_region": "Utiliser la région du paramètre régional",
    "language.no_flag_matches": "Aucun pays ne correspond à cette recherche.",
    "ui.all": "Tout",
    "ui.stay": "Rester ici",
})


# 0.35.16 — Tongue Tied Again: resumable translations, model cautions, and research recovery.
DEFAULT_EN_US.update({
    "language.install_help_modern": "DerridAI translates from the canonical English interface, validates every key and placeholder, and reports any strings that require an English fallback or retry.",
    "language.atomic_install_help": "Unsafe strings are tracked individually. Fewer than 10% may fall back to canonical English; larger failures remain resumable instead of discarding completed work.",
    "language.background_translation_help_modern": "Progress remains visible here and in Operations. If the job stops, validated translations are retained for a later resume.",
    "language.translation_started_modern": "Translation started. DerridAI is translating the English interface set before installing the locale.",
    "language.translation_incomplete_title": "Translation incomplete",
    "language.translation_incomplete_help": "{done} safe translations were retained. Retry resumes this partial dictionary instead of starting over; {failed} string(s) still need translation or review.",
    "language.resume_translation": "Resume translation",
    "language.resuming_partial": "Resuming retained work",
    "language.resuming_partial_help": "DerridAI will keep the {count} validated strings from the previous attempt and translate only unfinished or unsafe entries.",
    "language.translation_resumed": "Translation resumed from the retained partial dictionary.",
    "language.partial_translation_restored": "The incomplete translation was retained and can be resumed.",
    "language.resume_no_longer_needed": "This incomplete translation cannot be resumed because the locale is already installed or its locale code is unavailable.",
    "language.installed_with_fallbacks": "Language installed with {count} English fallback string(s). Review them under Needs review.",
    "language.model_translation_risk_title": "Translation quality warning",
    "language.model_translation_risk_embedding": "{model} appears to be an embedding or reranking model rather than a text-generation model. It is unlikely to be able to translate an interface dictionary.",
    "language.model_translation_risk_code": "{model} appears to be code-specialized. DerridAI treats code-focused families as higher-risk for natural-language interface translation.",
    "language.model_translation_risk_language": "{model} belongs to a smaller or English-centric family that is higher-risk for sustained multilingual interface translation. Consider a multilingual/instruction model if one is available.",
    "language.model_translation_risk_small": "{model} appears to be a very small model. Small models are higher-risk for complete dictionary translation, placeholder fidelity, and non-English fluency.",
    "language.model_translation_risk_ack": "I understand the risk and want to use this model anyway.",
    "language.model_translation_risk_ack_required": "Review and acknowledge the translation-quality warning before continuing with this model.",
    "language.tracked_fallbacks_title": "{count} translation fallback(s) need review",
    "language.tracked_fallbacks_help": "These exact keys were not translated safely during installation and are currently using canonical English. They remain tracked until you edit and save a localized value.",
    "language.review_fallbacks": "Review tracked fallbacks",
    "language.failure_details": "Failure details",
    "language.needs_review": "Needs review",
    "research.redirect_database": "Research needs a corpus database. Opening database creation now.",
    "faq.full_grade_output": "Full evaluation output",
})
DEFAULT_FR_CA.update({
    "language.install_help_modern": "DerridAI traduit depuis l’interface anglaise canonique, valide chaque clé et chaque variable, puis signale les chaînes qui nécessitent un repli en anglais ou une nouvelle tentative.",
    "language.atomic_install_help": "Les chaînes non sûres sont suivies individuellement. Si moins de 10 % échouent, elles peuvent utiliser l’anglais canonique comme valeur de repli; un échec plus important demeure reprenable sans perdre le travail terminé.",
    "language.background_translation_help_modern": "La progression reste visible ici et dans Opérations. Si la tâche s’arrête, les traductions validées sont conservées pour une reprise ultérieure.",
    "language.translation_started_modern": "La traduction a démarré. DerridAI traduit l’interface anglaise avant d’installer le paramètre régional.",
    "language.translation_incomplete_title": "Traduction incomplète",
    "language.translation_incomplete_help": "{done} traductions sûres ont été conservées. Une nouvelle tentative reprend ce dictionnaire partiel au lieu de recommencer; {failed} chaîne(s) doivent encore être traduites ou révisées.",
    "language.resume_translation": "Reprendre la traduction",
    "language.resuming_partial": "Reprise du travail conservé",
    "language.resuming_partial_help": "DerridAI conservera les {count} chaînes validées de la tentative précédente et ne traduira que les entrées inachevées ou non sûres.",
    "language.translation_resumed": "La traduction a repris à partir du dictionnaire partiel conservé.",
    "language.partial_translation_restored": "La traduction incomplète a été conservée et peut être reprise.",
    "language.resume_no_longer_needed": "Cette traduction incomplète ne peut pas être reprise parce que le paramètre régional est déjà installé ou que son code n’est plus disponible.",
    "language.installed_with_fallbacks": "Langue installée avec {count} chaîne(s) de repli en anglais. Révisez-les sous À réviser.",
    "language.model_translation_risk_title": "Avertissement sur la qualité de la traduction",
    "language.model_translation_risk_embedding": "{model} semble être un modèle de plongements vectoriels ou de reclassement plutôt qu’un modèle de génération de texte. Il est peu probable qu’il puisse traduire un dictionnaire d’interface.",
    "language.model_translation_risk_code": "{model} semble être spécialisé en programmation. DerridAI considère les familles axées sur le code comme plus risquées pour la traduction d’une interface en langage naturel.",
    "language.model_translation_risk_language": "{model} appartient à une famille plus petite ou surtout axée sur l’anglais, donc plus risquée pour une traduction d’interface multilingue soutenue. Préférez un modèle multilingue ou d’instructions lorsqu’il est disponible.",
    "language.model_translation_risk_small": "{model} semble être un très petit modèle. Les petits modèles présentent un risque plus élevé pour la traduction complète du dictionnaire, la fidélité des variables et la qualité dans les langues autres que l’anglais.",
    "language.model_translation_risk_ack": "Je comprends le risque et je souhaite quand même utiliser ce modèle.",
    "language.model_translation_risk_ack_required": "Consultez et acceptez l’avertissement sur la qualité de la traduction avant de poursuivre avec ce modèle.",
    "language.tracked_fallbacks_title": "{count} valeur(s) de repli à réviser",
    "language.tracked_fallbacks_help": "Ces clés précises n’ont pas pu être traduites de façon sûre pendant l’installation et utilisent actuellement l’anglais canonique. Elles demeurent suivies jusqu’à ce que vous saisissiez et enregistriez une valeur localisée.",
    "language.review_fallbacks": "Réviser les valeurs de repli suivies",
    "language.failure_details": "Détails des échecs",
    "language.needs_review": "À réviser",
    "research.redirect_database": "L’espace Recherche nécessite une base de données du corpus. Ouverture de la création d’une base de données.",
    "faq.full_grade_output": "Sortie complète de l’évaluation",
})


# 0.35.17 — Lingua Franca: durable diagnostics, accessible annotations, and a
# structured evaluation-report experience. Built-in language display names are
# intentionally region-neutral; their flags still indicate the shipped locale.
DEFAULT_EN_US.update({
    "language.english_us": "English",
    "language.french_ca": "Français",
    "language.english_source_set": "Source: English",
    "language.page_description": "Manage the built-in English and Français interfaces, install additional locale dictionaries from the canonical English set, and review translation coverage in one workspace.",
    "language.quebec_symbol": "Québec symbol",
    "language.quebec_symbol_help": "Unicode has no standardized Québec flag emoji; this option uses the fleur-de-lis symbol.",
    "annotations.annotation": "Annotation",
    "annotations.annotation_count": "{count} annotations",
    "annotations.no_note": "No note",
    "faq.full_grade_output": "Full evaluation report",
    "faq.evaluation_report": "Evaluation report",
    "faq.overall_score": "Overall score: {score} out of 10",
    "faq.grade_summary_fallback": "Structured evidence-grounding assessment",
    "faq.grade_categories": "Scoring categories",
    "faq.grade_strengths": "Strengths",
    "faq.grade_weaknesses": "Weaknesses",
    "faq.grade_risky_claims": "Unsupported or risky claims",
    "faq.grade_raw_output": "Technical raw output",
    "faq.grade_raw_output_help": "Raw grader output is retained for auditability and debugging.",
    "faq.grade_query_relevance": "Query relevance",
    "faq.grade_source_binding": "Source binding",
    "faq.grade_claim_traceability": "Claim traceability",
    "faq.grade_attribution_source_discrimination": "Attribution & source discrimination",
    "faq.grade_claim_evidence_fidelity": "Claim/evidence fidelity",
    "faq.grade_conceptual_precision": "Conceptual precision",
    "faq.grade_coverage": "Coverage",
    "faq.grade_interpretive_usefulness": "Interpretive usefulness",
})
DEFAULT_FR_CA.update({
    "language.english_us": "Anglais",
    "language.french_ca": "Français",
    "language.english_source_set": "Source : anglais",
    "language.page_description": "Gérez les interfaces intégrées en anglais et en français, installez d’autres dictionnaires régionaux à partir de l’ensemble anglais canonique et révisez la couverture de traduction dans un seul espace de travail.",
    "language.quebec_symbol": "Symbole du Québec",
    "language.quebec_symbol_help": "Unicode ne définit aucun émoji normalisé du drapeau du Québec; cette option utilise le symbole de la fleur de lys.",
    "annotations.annotation": "Annotation",
    "annotations.annotation_count": "{count} annotations",
    "annotations.no_note": "Aucune note",
    "faq.full_grade_output": "Rapport d’évaluation complet",
    "faq.evaluation_report": "Rapport d’évaluation",
    "faq.overall_score": "Note globale : {score} sur 10",
    "faq.grade_summary_fallback": "Évaluation structurée de l’ancrage dans les preuves",
    "faq.grade_categories": "Catégories de notation",
    "faq.grade_strengths": "Points forts",
    "faq.grade_weaknesses": "Points faibles",
    "faq.grade_risky_claims": "Affirmations non étayées ou risquées",
    "faq.grade_raw_output": "Sortie technique brute",
    "faq.grade_raw_output_help": "La sortie brute de l’évaluateur est conservée pour l’auditabilité et le débogage.",
    "faq.grade_query_relevance": "Pertinence par rapport à la question",
    "faq.grade_source_binding": "Ancrage dans les sources",
    "faq.grade_claim_traceability": "Traçabilité des affirmations",
    "faq.grade_attribution_source_discrimination": "Attribution et distinction des sources",
    "faq.grade_claim_evidence_fidelity": "Fidélité affirmation-preuve",
    "faq.grade_conceptual_precision": "Précision conceptuelle",
    "faq.grade_coverage": "Couverture",
    "faq.grade_interpretive_usefulness": "Utilité interprétative",
})

system_store = SystemStore()
