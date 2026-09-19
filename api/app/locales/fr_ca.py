# Copyright 2026 Aaron John Schlosser, PhD.
# Canonical built-in locale. Keep keys synchronized with the paired locale module.

# French is Canadian French (Québec).
FR_CA: dict[str, str] = {'annotations.add_note': 'Ajouter une note',
 'annotations.add_note_tags': 'Ajouter une note / des étiquettes',
 'annotations.annotate_selection': 'Annoter la sélection',
 'annotations.annotation': 'Annotation',
 'annotations.annotation_count': '{count} annotations',
 'annotations.by_work': 'Par œuvre',
 'annotations.empty': 'Ajoutez d’abord une citation, une note ou une étiquette.',
 'annotations.no_note': 'Aucune note',
 'annotations.none_record': 'Aucune annotation pour cette fiche',
 'annotations.none_record_help': 'Sélectionnez du texte ou une valeur affichée ci-dessus pour y joindre une note ou '
                                 'des étiquettes.',
 'annotations.none_yet': 'Aucune annotation pour le moment.',
 'annotations.note': 'Note',
 'annotations.note_placeholder': 'Ajoutez une note sur cette sélection…',
 'annotations.open_failed': 'Impossible d’ouvrir la fiche annotée',
 'annotations.open_record': 'Ouvrir la fiche',
 'annotations.page_help': 'Examinez les annotations du corpus. La vue par défaut les regroupe par œuvre; passez à '
                          'Récentes pour un flux chronologique.',
 'annotations.recent': 'Récentes',
 'annotations.recent_annotations': 'Annotations récentes',
 'annotations.recent_help': 'Annotations les plus récentes parmi toutes les œuvres chargées.',
 'annotations.record_annotations': 'Annotations de la fiche',
 'annotations.record_annotations_help': 'Notes et étiquettes rattachées à des éléments précis de cette fiche.',
 'annotations.record_note': 'Note de fiche',
 'annotations.record_notes': 'Annotations',
 'annotations.remove_help': 'Cette action supprime l’annotation partagée et ne peut pas être annulée.',
 'annotations.remove_local_help': "Cette action supprime l'annotation de la fiche JSONL locale et consigne la "
                                  "modification dans son historique d'audit.",
 'annotations.remove_title': 'Supprimer l’annotation?',
 'annotations.removed': 'Annotation de la fiche supprimée.',
 'annotations.researcher_help': 'Les annotations sont organisées par œuvre lorsqu’elles sont disponibles dans l’espace '
                                'de travail actuel.',
 'annotations.save': 'Enregistrer l’annotation',
 'annotations.saved': 'Annotation de fiche enregistrée',
 'annotations.search_placeholder': 'Rechercher dans les annotations, étiquettes, citations, fiches ou œuvres…',
 'annotations.selected': 'Sélectionné',
 'annotations.selected_text': 'Texte sélectionné',
 'annotations.shared': 'Annotation partagée',
 'annotations.tags': 'Étiquettes',
 'annotations.tags_placeholder': 'Étiquettes séparées par des virgules',
 'annotations.unknown_author': 'Auteur inconnu',
 'annotations.view_all': 'Tout afficher',
 'app.name': 'DerridAI',
 'app.subtitle': 'Visionneuse de corpus',
 'auth.assigned_account': 'Utilisez le compte DerridAI qui vous a été attribué.',
 'auth.confirm_password': 'Confirmer le mot de passe',
 'auth.create_admin': 'Créer l’administrateur',
 'auth.create_first_admin': 'Créer le premier administrateur',
 'auth.first_admin_help': 'Le premier compte est administrateur. D’autres comptes administrateur et chercheur peuvent '
                          'ensuite être créés.',
 'auth.first_run': 'Configuration initiale',
 'auth.password': 'Mot de passe',
 'auth.password_note': 'Les mots de passe doivent comporter au moins 6 caractères. Aucun identifiant administrateur '
                       'par défaut n’est créé.',
 'auth.passwords_no_match': 'Les mots de passe ne correspondent pas.',
 'auth.required': 'Authentification requise',
 'auth.session_expired': 'Votre session a expiré. Connectez-vous de nouveau.',
 'auth.sign_in': 'Se connecter',
 'auth.sign_in_title': 'Se connecter à DerridAI',
 'auth.username': 'Nom d’utilisateur',
 'auth.working': 'Traitement…',
 'compare.clear_pasted': 'Effacer les fiches collées',
 'compare.need_two': 'Deux fiches sont nécessaires',
 'compare.need_two_help': 'Parcourez des fiches ou lancez une recherche, puis revenez à Comparer.',
 'compare.page_help': 'Comparez les métadonnées et le texte des fiches avec des différences ciblées côte à côte.',
 'compare.paste_guidance_help': 'Les objets JSON et les fiches JSONL sur une seule ligne sont pris en charge. DerridAI '
                                'compare les champs analysés lorsque les deux côtés sont valides.',
 'compare.paste_guidance_title': 'Collez une fiche de chaque côté',
 'compare.paste_records': 'Coller des fiches',
 'compare.record_a': 'Fiche A',
 'compare.record_b': 'Fiche B',
 'compare.researcher_source_help': 'Les fiches proviennent de la base de corpus sélectionnée et utilisent le même '
                                   'espace Comparer que les comptes administrateur. Les commandes de modification '
                                   'n’apparaissent que lorsque votre rôle les autorise.',
 'compare.workspace_records': 'Fiches de l’espace de travail',
 'content_filter.warning': 'Ce langage n’est pas permis dans les comptes chercheurs. Le terme signalé a été supprimé.',
 'context.global_search': 'Recherche globale',
 'dashboard.advanced_filters': 'Filtres avancés',
 'dashboard.all_works': 'Toutes les œuvres',
 'dashboard.annotations': 'Annotations',
 'dashboard.annotations_help': 'Rassemblez les notes, étiquettes et fils de discussion associés aux preuves du corpus.',
 'dashboard.appearance': 'Apparence',
 'dashboard.appearance_help': 'Choisissez la couleur d’accentuation qui offre la meilleure lisibilité.',
 'dashboard.appearance_saved': 'Apparence mise à jour.',
 'dashboard.browse_works': 'Parcourir les œuvres',
 'dashboard.corpus_overview': 'Aperçu du corpus',
 'dashboard.databases': 'Bases de données',
 'dashboard.default_provider': 'Fournisseur par défaut',
 'dashboard.discourse_roles_share_work': 'Principaux rôles discursifs en pourcentage des rôles consignés',
 'dashboard.global_search': 'Recherche globale',
 'dashboard.interface_language': 'Langue de l’interface',
 'dashboard.interface_theme': 'Thème de l’interface',
 'dashboard.language_settings': 'Paramètres de langue',
 'dashboard.language_settings_help': 'Choisissez la langue de l’interface et gérez les dictionnaires de traduction.',
 'dashboard.last_viewed_record': 'Dernière fiche consultée',
 'dashboard.latest_annotation': 'Dernière annotation',
 'dashboard.latest_annotation_help': 'Annotation de corpus la plus récente',
 'dashboard.llm_provider_help': 'Configurez le fournisseur utilisé pour les flux de travail assistés par LLM.',
 'dashboard.llm_provider_settings': 'Paramètres des fournisseurs LLM',
 'dashboard.manage_languages': 'Gérer les langues',
 'dashboard.manage_provider': 'Gérer le fournisseur',
 'dashboard.model': 'Modèle',
 'dashboard.more_appearance_settings': 'Autres paramètres d’apparence',
 'dashboard.next_chart': 'Graphique suivant',
 'dashboard.no_recent_activity': 'Aucune modification suivie récente.',
 'dashboard.no_record_available': 'Aucune fiche n’est disponible à ouvrir.',
 'dashboard.no_record_selected': 'Ouvrez une fiche pour la garder à portée de main ici.',
 'dashboard.not_configured': 'Non configuré',
 'dashboard.other_works': 'Autres œuvres',
 'dashboard.previous_chart': 'Graphique précédent',
 'dashboard.quote': '« Il n’y a pas de hors-texte. »',
 'dashboard.random_record': 'Une fiche du corpus',
 'dashboard.recent_activity': 'Activité récente',
 'dashboard.record': 'Fiche',
 'dashboard.record_view': 'Vue de fiche',
 'dashboard.records': 'Fiches',
 'dashboard.search_corpus_placeholder': 'Rechercher dans le corpus…',
 'dashboard.search_help': 'Recherchez dans les œuvres, les métadonnées, les annotations et, lorsqu’elle est '
                          'disponible, la base sémantique.',
 'dashboard.start_searching': 'Commencer la recherche',
 'dashboard.tagline': 'Rechercher. Comparer. Annoter. Toujours déjà.',
 'dashboard.top_avg_record_length': '5 principales œuvres par longueur moyenne des fiches',
 'dashboard.top_concepts_work': '5 principaux concepts mentionnés dans l’œuvre',
 'dashboard.top_discourse_targets_work': '5 principales cibles discursives de l’œuvre',
 'dashboard.top_persons_work': '5 principales personnes mentionnées dans l’œuvre',
 'dashboard.top_topics_work': '5 principaux sujets de l’œuvre',
 'dashboard.top_total_words': '5 œuvres principales par nombre total de mots',
 'dashboard.top_works_records': '5 œuvres principales par nombre de fiches',
 'dashboard.total_words': 'Nombre total de mots',
 'dashboard.updated_record': 'Fiche mise à jour',
 'dashboard.view_all_works': 'Voir toutes les œuvres',
 'dashboard.welcome': 'Bienvenue dans DerridAI',
 'dashboard.words': 'mots',
 'dashboard.work_charts': 'Graphiques des œuvres',
 'dashboard.work_record_share': 'Répartition des œuvres selon le nombre total de fiches',
 'dashboard.work_word_share': 'Répartition des œuvres selon le nombre total de mots',
 'dashboard.works': 'Œuvres',
 'dashboard.year_not_recorded': 'Année non indiquée',
 'dynamic.annotation_one': 'annotation',
 'dynamic.annotations': 'annotations',
 'dynamic.cached_response_one': 'réponse mise en cache',
 'dynamic.cached_responses': 'réponses mises en cache',
 'dynamic.change_one': 'modification',
 'dynamic.changes': 'modifications',
 'dynamic.character_one': 'caractère',
 'dynamic.characters': 'caractères',
 'dynamic.cleaned_records': '{records} fiches nettoyées · {changes} modifications consignées',
 'dynamic.cleared_history_records': 'Historique des modifications effacé pour {count} fiches',
 'dynamic.completed_grading': 'Terminé · {graded} évaluations réussies, {failed} échecs',
 'dynamic.completed_works': 'Terminé · {works} œuvres traitées, {failed} échecs',
 'dynamic.exported_records': '{count} fiches exportées depuis {collection}',
 'dynamic.grading_progress': 'Évaluation {current} sur {total} · {question}',
 'dynamic.history_latest': 'Affichage des {shown} plus récentes parmi {total} modifications. L’historique complet est '
                           'conservé dans le champ updates de la fiche.',
 'dynamic.loaded_records': '{count} fiches chargées',
 'dynamic.loaded_records_issues': '{count} fiches chargées · {issues} problèmes d’analyse',
 'dynamic.merged_tabs_records': '{tabs} onglets fusionnés et remplacés · {records} fiches',
 'dynamic.model_one': 'modèle',
 'dynamic.models': 'modèles',
 'dynamic.page': 'page',
 'dynamic.page_of_pages': 'Page {page} / {pages}',
 'dynamic.profile_one': 'profil',
 'dynamic.profiles': 'profils',
 'dynamic.ready_models': 'Prêt · {count} modèles',
 'dynamic.record_one': 'fiche',
 'dynamic.record_range_count': '{shown} sur {total} fiches',
 'dynamic.records': 'fiches',
 'dynamic.restored_fields': 'État original de la fiche restauré · {count} champs modifiés',
 'dynamic.running_operation': 'Exécution : {label}',
 'dynamic.selected_count': '{count} éléments sélectionnés',
 'dynamic.selected_evidence': 'preuves sélectionnées',
 'dynamic.translating_interface': 'Traduction de {count} chaînes d’interface vers {locale}',
 'dynamic.waiting_ollama_active': 'En attente d’une place Ollama : {active} actives / {allowed} permises',
 'dynamic.waiting_provider_active': 'En attente d’une place chez le fournisseur : {active} actives / {allowed} '
                                    'permises',
 'dynamic.waiting_provider_active_paren': 'En attente d’une place chez le fournisseur ({active}/{allowed} actives)',
 'dynamic.word_one': 'mot',
 'dynamic.words': 'mots',
 'dynamic.work_one': 'œuvre',
 'dynamic.works': 'œuvres',
 'export.aggregate': 'JSONL agrégé',
 'export.all': 'Tous les fichiers séparément',
 'export.changed': 'Fichiers modifiés',
 'export.changed_aggregate': 'Modifiés + agrégé',
 'export.current': 'Fichier actuel',
 'export.nothing': "Il n'y a aucun fichier à exporter.",
 'export.title': 'Exporter en JSONL',
 'faq.archive_help': 'Parcourez ou recherchez les questions enregistrées, puis ouvrez-en une pour revoir sa réponse et '
                     'ses preuves.',
 'faq.browse_archive': 'Parcourir les recherches enregistrées',
 'faq.browse_controls': 'Commandes de la bibliothèque de réponses',
 'faq.cached_responses': 'réponses mises en cache',
 'faq.cached_result': 'Résultat mis en cache',
 'faq.current_question': 'Question actuelle',
 'faq.current_response': 'Réponse enregistrée affichée',
 'faq.deduplicated': 'Après déduplication',
 'faq.elapsed': 'Durée',
 'faq.empty_help': 'Les recherches terminées et mises en cache apparaîtront ici avec leurs liaisons aux preuves.',
 'faq.empty_title': 'Aucune réponse de recherche mise en cache',
 'faq.evaluation_report': 'Rapport d’évaluation',
 'faq.evidence_bound': 'Preuves liées',
 'faq.evidence_short': 'preuves',
 'faq.find_another_question': 'Rechercher une autre question',
 'faq.find_question': 'Rechercher une question',
 'faq.full_grade_output': 'Rapport d’évaluation complet',
 'faq.grade_attribution_source_discrimination': 'Attribution et distinction des sources',
 'faq.grade_categories': 'Catégories de notation',
 'faq.grade_claim_evidence_fidelity': 'Fidélité affirmation-preuve',
 'faq.grade_claim_traceability': 'Traçabilité des affirmations',
 'faq.grade_conceptual_precision': 'Précision conceptuelle',
 'faq.grade_coverage': 'Couverture',
 'faq.grade_interpretive_usefulness': 'Utilité interprétative',
 'faq.grade_query_relevance': 'Pertinence par rapport à la question',
 'faq.grade_raw_output': 'Sortie technique brute',
 'faq.grade_raw_output_help': 'La sortie brute de l’évaluateur est conservée pour l’auditabilité et le débogage.',
 'faq.grade_risky_claims': 'Affirmations non étayées ou risquées',
 'faq.grade_source_binding': 'Ancrage dans les sources',
 'faq.grade_strengths': 'Points forts',
 'faq.grade_summary_fallback': 'Évaluation structurée de l’ancrage dans les preuves',
 'faq.grade_weaknesses': 'Points faibles',
 'faq.library_help': 'Parcourez d’abord les questions enregistrées, puis rouvrez une réponse avec ses liaisons aux '
                     'preuves.',
 'faq.library_kicker': 'Bibliothèque',
 'faq.library_title': 'Questions enregistrées',
 'faq.loading': 'Chargement des réponses de recherche mises en cache…',
 'faq.matches': 'résultats correspondants',
 'faq.meta_deduplicated_count': 'Après déduplication',
 'faq.meta_document_languages': 'Langues des documents',
 'faq.meta_effective_rerank_top_n': 'Preuves après reclassement',
 'faq.meta_evidence_record_char_limit': 'Caractères par fiche de preuve',
 'faq.meta_evidence_total_char_limit': 'Nombre total de caractères de preuve',
 'faq.meta_fetch_k': 'Ensemble de candidats',
 'faq.meta_k': 'Candidats conservés',
 'faq.meta_lambda_mult': 'Équilibre de pertinence MMR',
 'faq.meta_limit_reranking': 'Limite de reclassement',
 'faq.meta_limit_retrieval': 'Limite de repérage',
 'faq.meta_prompt_instructions': 'Consignes de l’invite',
 'faq.meta_prompt_query': 'Requête de repérage',
 'faq.meta_prompt_query_fr': 'Requête de repérage en français',
 'faq.meta_query_decomposition': 'Décomposition de la requête',
 'faq.meta_query_decomposition_num_predict': 'Limite de jetons pour la décomposition',
 'faq.meta_raw_count': 'Candidats repérés',
 'faq.meta_rerank_top_n': 'Nombre à reclasser',
 'faq.meta_reranked_count': 'Après reclassement',
 'faq.meta_reranker': 'Module de reclassement',
 'faq.meta_response_language': 'Langue de la réponse',
 'faq.meta_rrf_k': 'Lissage de la fusion des rangs',
 'faq.meta_search_types': 'Voies de recherche',
 'faq.meta_selected_evidence_count': 'Preuves épinglées',
 'faq.meta_skip_retrieval': 'Exécution avec preuves sélectionnées seulement',
 'faq.new_research': 'Nouvelle recherche',
 'faq.no_matches': 'Aucune question enregistrée ne correspond à cette recherche',
 'faq.no_matches_help': 'Essayez des termes plus généraux ou effacez la recherche.',
 'faq.overall_score': 'Note globale : {score} sur 10',
 'faq.page_kicker': 'Archives de recherche',
 'faq.page_of': 'Page {page} sur {pages}',
 'faq.page_subtitle': 'Revenez aux réponses mises en cache avec la même présentation des preuves liées aux sources que '
                      'dans l’espace Recherche.',
 'faq.query_help': 'Façon dont la question a été interprétée et acheminée pour cette exécution.',
 'faq.question_matches': 'questions correspondantes',
 'faq.questions_help': 'Sélectionnez une question pour ouvrir sa réponse enregistrée.',
 'faq.questions_label': 'Questions',
 'faq.reranked': 'Après reclassement',
 'faq.results': 'résultats',
 'faq.retrieval_help': 'Paramètres et dénombrements de repérage conservés avec cette réponse mise en cache.',
 'faq.retrieved': 'Repérées',
 'faq.run_provenance': 'Provenance de l’exécution et évaluation enregistrée',
 'faq.run_provenance_help': 'Consultez le diagnostic de repérage, les métadonnées de la requête et les évaluations '
                            'conservées sans masquer la réponse.',
 'faq.run_summary': 'Résumé de l’exécution',
 'faq.run_summary_help': 'Vue concise de ce qui s’est produit avant la génération de la réponse.',
 'faq.saved_grade': 'Évaluation enregistrée',
 'faq.saved_grades': 'Évaluations LLM enregistrées',
 'faq.saved_grades_help': 'Évaluations conservées avec cette réponse mise en cache.',
 'faq.saved_on': 'Enregistré le',
 'faq.saved_questions': 'questions enregistrées',
 'faq.saved_responses': 'Réponses enregistrées',
 'faq.search_label': 'Rechercher dans les questions enregistrées',
 'faq.search_placeholder': 'Rechercher dans le texte des questions…',
 'faq.select_response': 'Choisissez une réponse enregistrée',
 'faq.select_response_help': 'Sélectionnez une question dans la bibliothèque pour rouvrir sa réponse et ses liaisons '
                             'aux preuves.',
 'faq.technical_metadata': 'Métadonnées techniques',
 'faq.untitled_question': 'Question sans titre',
 'field.__db_status': 'État de la BD',
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
 'language.add_key': 'Ajouter une clé',
 'language.add_source_key': 'Ajouter une clé anglaise canonique',
 'language.add_source_key_help': 'L’anglais définit l’ensemble canonique des clés. Les nouvelles clés apparaissent '
                                 'comme valeurs anglaises de repli dans les paramètres régionaux installés jusqu’à '
                                 'leur traduction.',
 'language.api_key': 'Clé API',
 'language.atomic_install': 'Validation avant installation',
 'language.atomic_install_help': 'Les chaînes non sûres sont suivies individuellement. Si moins de 10 % échouent, '
                                 'elles peuvent utiliser l’anglais canonique comme valeur de repli; un échec plus '
                                 'important demeure reprenable sans perdre le travail terminé.',
 'language.background_translation': 'S’exécute en arrière-plan',
 'language.background_translation_help': 'Vous pouvez fermer cette fenêtre immédiatement et poursuivre votre travail.',
 'language.background_translation_help_modern': 'La progression reste visible ici et dans Opérations. Si la tâche '
                                                's’arrête, les traductions validées sont conservées pour une reprise '
                                                'ultérieure.',
 'language.base_url': 'URL de base',
 'language.built_in': 'Intégré',
 'language.canonical': 'Canonique',
 'language.canonical_source': 'Source canonique',
 'language.checking_provider': 'Vérification du fournisseur…',
 'language.choose_flag': 'Choisir un drapeau de pays',
 'language.concurrent_requests': 'nombre maximal de requêtes simultanées',
 'language.coverage': 'Couverture',
 'language.custom': 'Personnalisé',
 'language.description_app': 'Texte d’identité de l’application',
 'language.description_generic': 'Texte d’interface',
 'language.description_language': 'Texte des paramètres de langue',
 'language.description_nav': 'Libellé de navigation',
 'language.description_rag': 'Texte des flux Recherche et RAG',
 'language.description_record': 'Texte de l’espace de fiche',
 'language.description_research': 'Texte de l’espace Recherche',
 'language.description_role': 'Libellé de rôle',
 'language.description_section': 'Titre de section',
 'language.description_ui': 'Action, état ou aide de l’interface',
 'language.description_users': 'Texte de gestion des utilisateurs et rôles',
 'language.dictionary_key': 'Clé du dictionnaire',
 'language.dictionary_value': 'Valeur du dictionnaire',
 'language.discard_switch': 'Ignorer et changer',
 'language.english_fallback_note': 'Correspond actuellement à la source anglaise',
 'language.english_short': 'Anglais',
 'language.english_source': 'Source anglaise',
 'language.english_source_set': 'Source : anglais',
 'language.english_us': 'Anglais (États-Unis)',
 'language.english_value': 'Valeur anglaise',
 'language.failure_details': 'Détails des échecs',
 'language.field_description': 'Description',
 'language.filled': 'Renseignées',
 'language.flag': 'Drapeau / symbole',
 'language.flag_help': 'Émoji ou symbole Unicode affiché à côté du nom de la langue.',
 'language.flag_library': 'Bibliothèque de drapeaux de pays',
 'language.flag_library_help': 'Choisissez un drapeau dans la bibliothèque ou utilisez le globe neutre pour les '
                               'langues sans paramètre régional propre à un pays.',
 'language.french_ca': 'Français (Québec)',
 'language.french_short': 'Français',
 'language.identity_section': 'Identité de la langue',
 'language.identity_section_help': 'Choisissez le code régional et le libellé affiché dans le sélecteur de langue.',
 'language.identity_section_help_modern': 'Utilisez une balise de langue BCP 47. Les paramètres régionaux avec '
                                          'écriture explicite, comme zh-Hant-TW, sont pris en charge.',
 'language.install': 'Installer une langue',
 'language.install_dictionary': 'Installer un dictionnaire traduit',
 'language.install_dictionary_modern': 'Traduire et installer le paramètre régional',
 'language.install_help': 'Le dictionnaire canonique en-US est traduit avec le fournisseur choisi. Les clés restent '
                          'inchangées.',
 'language.install_help_modern': 'DerridAI traduit depuis l’interface anglaise canonique, valide chaque clé et chaque '
                                 'variable, puis signale les chaînes qui nécessitent un repli en anglais ou une '
                                 'nouvelle tentative.',
 'language.install_kicker': 'Nouvelle langue d’interface',
 'language.install_review_note': 'Après l’installation, vérifiez et modifiez chaque champ traduit dans le tableau du '
                                 'dictionnaire.',
 'language.install_steps': 'Étapes de l’installation',
 'language.installed': 'Langues installées',
 'language.installed_with_fallbacks': 'Langue installée avec {count} chaîne(s) de repli en anglais. Révisez-les sous À '
                                      'réviser.',
 'language.interface_strings': 'chaînes d’interface',
 'language.key': 'Clé',
 'language.key_context': 'Clé et contexte',
 'language.leave_install_help': 'La gestion des profils fournisseur ouvre une autre page. Les valeurs saisies dans ce '
                                'formulaire d’installation seront perdues.',
 'language.leave_install_title': 'Quitter l’installation de la langue?',
 'language.leave_manage_providers': 'Quitter et gérer les fournisseurs',
 'language.locale_already_installed': 'Ce paramètre régional est déjà installé. Sélectionnez-le dans la liste pour le '
                                      'modifier.',
 'language.locale_code': 'Code de langue et de région',
 'language.locale_code_help': 'Identifiant BCP 47 de langue et de région, par exemple de-DE ou es-MX.',
 'language.locale_code_help_modern': 'Exemples : de-DE, pt-BR, zh-Hant-TW.',
 'language.locale_count': 'langues',
 'language.locale_icon': 'Icône du paramètre régional',
 'language.locale_identity': 'Identité du paramètre régional',
 'language.locale_library': 'Bibliothèque de paramètres régionaux',
 'language.locale_pending': 'Code de langue et de région requis',
 'language.locales': 'Paramètres régionaux',
 'language.localization_summary': 'Résumé de la localisation',
 'language.localized': 'Localisées',
 'language.manage': 'Gérer les langues',
 'language.manage_providers': 'Gérer les profils fournisseurs',
 'language.matches_english': 'Identique à l’anglais',
 'language.missing': 'Manquantes',
 'language.model': 'Modèle',
 'language.model_not_set': 'modèle non défini',
 'language.model_translation_risk_ack': 'Je comprends le risque et je souhaite quand même utiliser ce modèle.',
 'language.model_translation_risk_ack_required': 'Consultez et acceptez l’avertissement sur la qualité de la '
                                                 'traduction avant de poursuivre avec ce modèle.',
 'language.model_translation_risk_code': '{model} semble être spécialisé en programmation. DerridAI considère les '
                                         'familles axées sur le code comme plus risquées pour la traduction d’une '
                                         'interface en langage naturel.',
 'language.model_translation_risk_embedding': '{model} semble être un modèle de plongements vectoriels ou de '
                                              'reclassement plutôt qu’un modèle de génération de texte. Il est peu '
                                              'probable qu’il puisse traduire un dictionnaire d’interface.',
 'language.model_translation_risk_language': '{model} appartient à une famille plus petite ou surtout axée sur '
                                             'l’anglais, donc plus risquée pour une traduction d’interface multilingue '
                                             'soutenue. Préférez un modèle multilingue ou d’instructions lorsqu’il est '
                                             'disponible.',
 'language.model_translation_risk_small': '{model} semble être un très petit modèle. Les petits modèles présentent un '
                                          'risque plus élevé pour la traduction complète du dictionnaire, la fidélité '
                                          'des variables et la qualité dans les langues autres que l’anglais.',
 'language.model_translation_risk_title': 'Avertissement sur la qualité de la traduction',
 'language.name': 'Nom',
 'language.name_help': 'Nom lisible affiché dans le sélecteur de langue.',
 'language.needs_review': 'À réviser',
 'language.new_language': 'Nouvelle langue',
 'language.no_country_flag': 'Aucun drapeau de pays',
 'language.no_flag_matches': 'Aucun pays ne correspond à cette recherche.',
 'language.no_locale_matches': 'Aucun paramètre régional installé ne correspond à cette recherche.',
 'language.no_provider_profiles': 'Aucun profil fournisseur LLM n’est configuré',
 'language.no_provider_profiles_help': 'Créez d’abord un profil fournisseur, puis revenez ici pour traduire un '
                                       'dictionnaire.',
 'language.no_string_matches': 'Aucune chaîne d’interface ne correspond à ces filtres.',
 'language.page_description': 'Gérez les interfaces intégrées en anglais et en français, installez d’autres '
                              'dictionnaires régionaux à partir de l’ensemble anglais canonique et révisez la '
                              'couverture de traduction dans un seul espace de travail.',
 'language.page_description_modern': 'Gérez les paramètres régionaux de l’interface dans un même espace de traduction '
                                     'bilingue. L’anglais constitue la source canonique; les paramètres régionaux '
                                     'installés demeurent modifiables et vérifiables.',
 'language.page_title': 'Langues et internationalisation',
 'language.partial_translation_restored': 'La traduction incomplète a été conservée et peut être reprise.',
 'language.provider': 'Fournisseur',
 'language.provider_model_required': 'Le profil fournisseur sélectionné n’a pas de modèle configuré.',
 'language.provider_pending': 'Profil fournisseur requis',
 'language.provider_profile': 'Profil fournisseur',
 'language.provider_profile_help': 'Utilise les mêmes profils fournisseurs et paramètres de modèle que Recherche, les '
                                   'outils PDF et la révision LLM.',
 'language.provider_profile_required': 'Configurez un profil fournisseur LLM avant d’installer un dictionnaire.',
 'language.provider_unavailable': 'Le fournisseur sélectionné est inaccessible : {message}',
 'language.provider_unavailable_short': 'fournisseur inaccessible',
 'language.quebec_symbol': 'Symbole du Québec',
 'language.quebec_symbol_help': 'Unicode ne définit aucun émoji normalisé du drapeau du Québec; cette option utilise '
                                'le symbole de la fleur de lys.',
 'language.remove_confirm': 'Supprimer la langue?',
 'language.remove_help': 'Le dictionnaire installé sera supprimé de cette instance DerridAI.',
 'language.remove_key': 'Supprimer la clé du dictionnaire',
 'language.remove_language': 'Supprimer la langue',
 'language.removed': 'Langue supprimée.',
 'language.resume_no_longer_needed': 'Cette traduction incomplète ne peut pas être reprise parce que le paramètre '
                                     'régional est déjà installé ou que son code n’est plus disponible.',
 'language.resume_translation': 'Reprendre la traduction',
 'language.resuming_partial': 'Reprise du travail conservé',
 'language.resuming_partial_help': 'DerridAI conservera les {count} chaînes validées de la tentative précédente et ne '
                                   'traduira que les entrées inachevées ou non sûres.',
 'language.review_after': 'Réviser après l’exécution',
 'language.review_after_help': 'Une fois la traduction terminée, le dictionnaire installé apparaîtra ici; révisez et '
                               'modifiez ensuite chaque champ au besoin.',
 'language.review_fallbacks': 'Réviser les valeurs de repli suivies',
 'language.save_dictionary': 'Enregistrer le dictionnaire',
 'language.save_switch': 'Enregistrer et changer',
 'language.saved': 'Dictionnaire de langue enregistré.',
 'language.search_flags': 'Rechercher des pays…',
 'language.search_locales': 'Rechercher des paramètres régionaux',
 'language.search_strings': 'Rechercher des clés, la source anglaise ou la traduction…',
 'language.source_key_count': '{count} chaînes d’interface seront traduites.',
 'language.source_language': 'Langue source',
 'language.source_language_help': 'Toutes les traductions installées sont rattachées à l’ensemble canonique de '
                                  'l’interface anglaise.',
 'language.source_strings': 'Chaînes anglaises',
 'language.start_translation': 'Lancer la traduction',
 'language.starting': 'Démarrage…',
 'language.step_identity': 'Langue',
 'language.step_provider': 'Profil fournisseur',
 'language.step_review': 'Installation',
 'language.title': 'Langue',
 'language.track_operations': 'Suivre dans Opérations',
 'language.track_operations_help': 'La progression et les erreurs s’affichent avec les autres tâches en arrière-plan.',
 'language.tracked_fallbacks_help': 'Ces clés précises n’ont pas pu être traduites de façon sûre pendant '
                                    'l’installation et utilisent actuellement l’anglais canonique. Elles demeurent '
                                    'suivies jusqu’à ce que vous saisissiez et enregistriez une valeur localisée.',
 'language.tracked_fallbacks_title': '{count} valeur(s) de repli à réviser',
 'language.translate_install': 'Traduire et installer',
 'language.translated_keys': 'clés traduites',
 'language.translating': 'Traduction…',
 'language.translating_install': 'Traduction avant installation',
 'language.translation': 'Traduction',
 'language.translation_complete': 'Langue traduite et installée.',
 'language.translation_editor': 'Éditeur de traduction',
 'language.translation_failed': 'Échec de la traduction.',
 'language.translation_failed_detail': 'Le modèle ou fournisseur sélectionné n’a pas pu installer cette langue : '
                                       '{message}',
 'language.translation_filters': 'Filtres de traduction',
 'language.translation_in_progress': 'Traduction du dictionnaire anglais canonique…',
 'language.translation_incomplete_help': '{done} traductions sûres ont été conservées. Une nouvelle tentative reprend '
                                         'ce dictionnaire partiel au lieu de recommencer; {failed} chaîne(s) doivent '
                                         'encore être traduites ou révisées.',
 'language.translation_incomplete_title': 'Traduction incomplète',
 'language.translation_resumed': 'La traduction a repris à partir du dictionnaire partiel conservé.',
 'language.translation_section': 'Fournisseur de traduction',
 'language.translation_section_help': 'Utilisez un profil fournisseur LLM existant afin que le modèle, le point de '
                                      'terminaison, les identifiants et les réglages restent cohérents avec le reste '
                                      'de DerridAI.',
 'language.translation_section_help_modern': 'DerridAI vérifie le fournisseur avant de démarrer. La traduction '
                                             's’effectue par lots bornés afin que les petits modèles locaux ne '
                                             'reçoivent pas tout le dictionnaire en une seule fois.',
 'language.translation_started': 'La traduction a démarré en arrière-plan. Suivez sa progression dans Opérations; la '
                                 'nouvelle langue apparaîtra lorsque la tâche sera terminée.',
 'language.translation_started_modern': 'La traduction a démarré. DerridAI traduit l’interface anglaise avant '
                                        'd’installer le paramètre régional.',
 'language.translation_target': 'Cible de traduction',
 'language.unsaved_changes': 'Modifications non enregistrées',
 'language.unsaved_help': 'Ce paramètre régional comporte des modifications non enregistrées au dictionnaire ou à son '
                          'identité.',
 'language.unsaved_title': 'Enregistrer les modifications avant de changer de paramètre régional?',
 'language.use_locale_region': 'Utiliser la région du paramètre régional',
 'language.what_happens_next': 'Ce qui se passe ensuite',
 'language.workspace_kicker': 'Studio de localisation',
 'runtime.accepted_fields': 'champs acceptés',
 'runtime.accepted_results': 'résultats acceptés',
 'runtime.active_jsonl_tab': 'Onglet JSONL actif',
 'runtime.active_ollama_rag': 'RAG Ollama actif',
 'runtime.add_column': 'Ajouter une colonne',
 'runtime.additional_instructions': 'Instructions supplémentaires',
 'runtime.aggregate_jsonl': 'Agréger le JSONL',
 'runtime.all': 'Tout',
 'runtime.all_loaded_records': 'Toutes les fiches chargées',
 'runtime.all_works': 'Toutes les œuvres',
 'runtime.allowed_fields': 'Champs autorisés',
 'runtime.already_first_page': 'Vous êtes déjà à la première page.',
 'runtime.already_last_page': 'Vous êtes déjà à la dernière page.',
 'runtime.answer': 'Réponse',
 'runtime.any': 'N’importe lequel',
 'runtime.api_key': 'Clé API',
 'runtime.append_works_cited': 'Ajouter les ouvrages cités',
 'runtime.apply': 'Appliquer',
 'runtime.attribution': 'Attribution',
 'runtime.attribution_confidence': 'Fiabilité de l’attribution',
 'runtime.auto': 'Automatique',
 'runtime.auto_improve_changes': 'Modifications d’amélioration automatique',
 'runtime.auto_router': 'Routage automatique',
 'runtime.available_loaded_works': 'Œuvres chargées disponibles',
 'runtime.available_models': 'Modèles disponibles',
 'runtime.back': '← Retour',
 'runtime.background_auto_improve': 'Amélioration automatique en arrière-plan',
 'runtime.background_operation': 'Opération en arrière-plan',
 'runtime.background_operations': 'Opérations en arrière-plan',
 'runtime.background_review': 'Révision en arrière-plan',
 'runtime.backup_restore': 'Sauvegarde et restauration',
 'runtime.backup_restore_help': 'Créez une archive compressée portable qui contient l’espace de travail du navigateur, '
                               'les fiches JSONL chargées, l’historique d’audit, la configuration des fournisseurs et '
                               'du RAG, le PDF actuel ainsi que chaque collection Chroma et ses vecteurs stockés.',
 'runtime.cached_as': 'Mis en cache sous',
 'runtime.cached_faq_suffix': '. Elle est accessible dans la bibliothèque de réponses.',
 'runtime.cached_responses': 'Réponses en mémoire cache',
 'runtime.cancel': 'Annuler',
 'runtime.cancel_operation': 'Annuler l’opération',
 'runtime.cancel_requested': 'Annulation demandée',
 'runtime.cancelling': 'Annulation…',
 'runtime.case_sensitive': 'Sensible à la casse',
 'runtime.change_history': 'Historique des modifications',
 'runtime.changed': 'Modifié',
 'runtime.changed_files': 'Fichiers modifiés',
 'runtime.changed_lower': 'modifié',
 'runtime.check': 'Vérifier',
 'runtime.checking': 'Vérification…',
 'runtime.choose_discovered_model': 'Choisir un modèle détecté',
 'runtime.choose_previous_rag': 'Choisissez d’abord une question RAG précédente.',
 'runtime.chroma_destination': 'Destination Chroma',
 'runtime.chroma_sync': 'Synchronisation Chroma',
 'runtime.citation': 'Citation',
 'runtime.citations': 'Citations',
 'runtime.claim_scope': 'Portée de l’énoncé',
 'runtime.cleaned_page_text': 'Texte de page nettoyé',
 'runtime.clear': 'Effacer',
 'runtime.clear_all_histories': 'Effacer tous les historiques',
 'runtime.clear_all_updates_confirm': 'Effacer tous les historiques de modifications?',
 'runtime.clear_cache': 'Vider la mémoire cache',
 'runtime.clear_history': 'Effacer l’historique',
 'runtime.clear_instructions': 'Effacer les instructions',
 'runtime.clear_past_results': 'Effacer les résultats précédents',
 'runtime.clear_record': 'Effacer la fiche',
 'runtime.clear_record_updates_confirm': 'Effacer l’historique des modifications de la fiche?',
 'runtime.clear_search': 'Effacer la recherche',
 'runtime.clear_selection': 'Effacer la sélection',
 'runtime.close': 'Fermer',
 'runtime.close_preview': 'Fermer l’aperçu',
 'runtime.coding': 'Programmation',
 'runtime.collapse_all': 'Tout réduire',
 'runtime.collection': 'Collection',
 'runtime.collection_name': 'Nom de la collection',
 'runtime.column_already_first': 'Cette colonne est déjà la première.',
 'runtime.column_already_last': 'Cette colonne est déjà la dernière.',
 'runtime.columns': 'Colonnes',
 'runtime.completed_rag_cached': 'Les exécutions RAG terminées seront automatiquement mises en cache et apparaîtront '
                                'ici.',
 'runtime.condition': 'Condition',
 'runtime.configure_columns': 'Configurer les colonnes',
 'runtime.configured_model': 'Modèle configuré',
 'runtime.context': 'Contexte',
 'runtime.context_num_ctx': 'Contexte (num_ctx)',
 'runtime.copy_answer': 'Copier la réponse',
 'runtime.copy_entire_record': 'Copier toute la fiche',
 'runtime.cover_url': 'URL de la couverture',
 'runtime.create_collection': 'Créer une collection',
 'runtime.create_download': 'Créer et télécharger',
 'runtime.create_subset_tab': 'Créer un onglet de sous-ensemble',
 'runtime.created': 'Créé',
 'runtime.cross_encoder': 'Encodeur croisé',
 'runtime.cross_encoder_model': 'Modèle d’encodeur croisé',
 'runtime.cross_file_work_overview': 'Vue d’ensemble de l’œuvre dans plusieurs fichiers',
 'runtime.current': 'Actuel',
 'runtime.current_file': 'Fichier actuel',
 'runtime.current_page_records': 'Fiches de la page actuelle',
 'runtime.current_pdf': 'PDF actuel',
 'runtime.decision_state': 'état de décision',
 'runtime.default': 'par défaut',
 'runtime.default_reranker': 'Module de reclassement par défaut',
 'runtime.default_run_mode': 'Mode d’exécution par défaut',
 'runtime.delete': 'Supprimer',
 'runtime.desktop_notifications': 'Notifications du bureau',
 'runtime.details': 'Détails',
 'runtime.details_timeline': 'Détails / chronologie',
 'runtime.differences': 'Différences',
 'runtime.direct_quote': 'Citation directe',
 'runtime.discourse': 'Discours',
 'runtime.discovered': 'Découvert',
 'runtime.discovered_model': 'Modèle découvert',
 'runtime.discovered_models': 'Modèles découverts',
 'runtime.dismiss': 'Fermer',
 'runtime.document_author': 'Auteur du document',
 'runtime.document_language': 'Langue du document',
 'runtime.document_languages': 'Langues des documents',
 'runtime.document_title': 'Titre du document',
 'runtime.edit_chroma_record': 'Modifier la fiche Chroma',
 'runtime.edit_record': 'Modifier la fiche',
 'runtime.edit_work_metadata': 'Modifier les métadonnées de l’œuvre',
 'runtime.embedding': 'Plongement vectoriel',
 'runtime.endpoint': 'Point de terminaison',
 'runtime.english': 'Anglais',
 'runtime.every_field_shown': 'Tous les champs disponibles sont déjà affichés.',
 'runtime.evidence': 'Preuves',
 'runtime.evidence_selected': 'Preuve sélectionnée',
 'runtime.expand_all': 'Tout développer',
 'runtime.expand_inspect_records': 'Développez pour examiner ou prévisualiser ces fiches',
 'runtime.export_jsonl': 'Exporter en JSONL',
 'runtime.expression': 'Expression',
 'runtime.extract_all_text': 'Extraire tout le texte',
 'runtime.extract_page_text': 'Extraire le texte de la page',
 'runtime.extracted_text': 'Texte extrait',
 'runtime.extraction_quality': 'Qualité de l’extraction',
 'runtime.failed': 'échec',
 'runtime.fast_small': 'Rapide/léger',
 'runtime.field': 'Champ',
 'runtime.fields_changed': 'champs modifiés',
 'runtime.fields_compared': 'champs comparés',
 'runtime.filter': 'Filtrer',
 'runtime.filter_logic_help_prefix': 'Les groupes sont évalués en premier. Au niveau supérieur, ET est prioritaire sur '
                                    'OU. Cela permet des expressions comme',
 'runtime.filter_models': 'Filtrer les modèles…',
 'runtime.filter_placeholder': 'Filtrer…',
 'runtime.filter_value': 'Valeur du filtre',
 'runtime.finished': 'Terminé',
 'runtime.first': 'Premier',
 'runtime.forward': 'Suivant →',
 'runtime.fragment_and': 'et',
 'runtime.fragment_field_period': 'champ.',
 'runtime.fragment_or': 'ou',
 'runtime.fragment_tags_period': 'étiquettes.',
 'runtime.free_llm_openai_model_selection': 'Sélection de modèle FreeLLM / OpenAI',
 'runtime.french': 'Français',
 'runtime.full_citation': 'Citation complète',
 'runtime.full_cite': 'Citation complète',
 'runtime.general_chat': 'Général/conversation',
 'runtime.generation': 'Génération',
 'runtime.generation_model': 'Modèle de génération',
 'runtime.go': 'Aller',
 'runtime.grade_every_response': 'Évaluer chaque réponse',
 'runtime.graded': 'évalué',
 'runtime.grades': 'Évaluations',
 'runtime.grouped_conditions': 'Conditions groupées',
 'runtime.help.a_full_backup_can_contain_provider_api_keys_store_backup_zip_files_securely_installed_ollama_mo': 'Une '
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
 'runtime.help.add_at_least_one_condition': 'Ajoutez au moins une condition.',
 'runtime.help.additional_options_json': 'Options JSON supplémentaires',
 'runtime.help.advanced_ollama_options_json': 'Options JSON avancées d’Ollama',
 'runtime.help.advanced_openai_compatible_options_json': 'Options JSON avancées du fournisseur compatible avec OpenAI',
 'runtime.help.advanced_options_json': 'Options JSON avancées',
 'runtime.help.advanced_provider_options': 'Options avancées du fournisseur',
 'runtime.help.all_cached_responses_were_processed': 'Toutes les réponses en mémoire cache ont été traitées.',
 'runtime.help.all_files_separately': 'Tous les fichiers séparément',
 'runtime.help.all_loaded_jsonl_files': 'Tous les fichiers JSONL chargés',
 'runtime.help.allow_researcher_accounts_to_use_this_profile_for_research_without_exposing_credentials_or_prov': 'Permettre '
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
 'runtime.help.also_remove_from_chroma': 'Retirer également de Chroma',
 'runtime.help.an_administrator_must_create_or_restore_a_corpus_vector_database_before_researcher_search_and_r': 'Un '
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
 'runtime.help.api_keys_are_intentionally_omitted': 'Les clés API sont volontairement omises.',
 'runtime.help.apply_one_field_value_consistently_across_a_selected_record_set_every_actual_change_is_audited': 'Appliquez '
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
 'runtime.help.ask_a_research_question_about_derrida': 'Posez une question de recherche sur Derrida…',
 'runtime.help.ask_an_administrator_to_create_or_populate_a_corpus_vector_database': 'Demandez à un administrateur de '
                                                                                    'créer ou d’alimenter une base de '
                                                                                    'données vectorielle du corpus.',
 'runtime.help.auto_grade_final_response_as_the_last_pipeline_step': 'Évaluer automatiquement la réponse finale comme '
                                                                    'dernière étape du pipeline',
 'runtime.help.auto_grade_provider_profile': 'Profil fournisseur pour l’évaluation automatique',
 'runtime.help.auto_grade_the_final_rag_response_after_caching': 'Évaluer automatiquement la réponse RAG finale après '
                                                                'la mise en cache',
 'runtime.help.auto_improve_pass_in_progress': 'Passe d’amélioration automatique en cours',
 'runtime.help.autocomplete_searches_record_ids_works_authors_and_source_files_without_rendering_an_enormous_s': 'La '
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
 'runtime.help.automatic_pipeline_grade': 'Évaluation automatique du pipeline',
 'runtime.help.browse_summarized_records': 'Parcourir les fiches résumées',
 'runtime.help.browser_permission_is_required_notifications_are_local_browser_notifications': 'L’autorisation du '
                                                                                             'navigateur est requise. '
                                                                                             'Les notifications sont '
                                                                                             'envoyées localement par '
                                                                                             'le navigateur.',
 'runtime.help.build_explicit_boolean_groups_such_as_a_and_b_and_c_or_d_or_e_and_f': 'Créez des groupes booléens '
                                                                                    'explicites, par exemple A ET B ET '
                                                                                    '(C OU D OU E) ET F.',
 'runtime.help.bulk_edit_one_field': 'Modifier un champ en lot',
 'runtime.help.cached_rag_responses': 'réponses RAG en mémoire cache',
 'runtime.help.changed_aggregate': 'Modifiés + agrégés',
 'runtime.help.changes_stay_local_until_you_export_or_upsert_them': 'Les modifications demeurent locales jusqu’à leur '
                                                                   'exportation ou leur synchronisation.',
 'runtime.help.checking_configured_llm_provider': 'Vérification du fournisseur LLM configuré…',
 'runtime.help.choose_any_subset_the_selected_source_tabs_will_be_replaced_in_the_workspace_by_the_merged_tab': 'Choisissez '
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
 'runtime.help.choose_discovered_model': 'Choisir un modèle découvert',
 'runtime.help.choose_the_grading_provider_model_in_the_rag_runner': 'Choisissez le fournisseur et le modèle '
                                                                    'd’évaluation dans l’outil d’exécution RAG.',
 'runtime.help.clean_current_page_text': 'Nettoyer le texte de la page actuelle',
 'runtime.help.clear_column_filters': 'Effacer les filtres de colonnes',
 'runtime.help.clear_remembered_questions': 'Effacer les questions mémorisées',
 'runtime.help.completed_rag_runs_will_be_cached_automatically_and_appear_here': 'Les exécutions RAG terminées seront '
                                                                                'automatiquement mises en cache et '
                                                                                'apparaîtront ici.',
 'runtime.help.conservative_ligature_zero_width_character_and_broken_line_hyphen_cleanup_no_paraphrasing': 'Nettoyage '
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
 'runtime.help.copy_entire_record_json': 'Copier tout le JSON de la fiche',
 'runtime.help.corpus_chroma_collections': 'collections Chroma du corpus',
 'runtime.help.could_not_load_response_faq': 'Impossible de charger la bibliothèque de réponses.',
 'runtime.help.could_not_read_response_cache': 'Impossible de lire la mémoire cache des réponses.',
 'runtime.help.could_not_render_this_item': 'Impossible d’afficher cet élément.',
 'runtime.help.create_draft_record': 'Créer une fiche provisoire',
 'runtime.help.create_jsonl_subset': 'Créer un sous-ensemble JSONL',
 'runtime.help.create_or_restore_a_corpus_vector_database_before_upserting_pdf_drafts': 'Créez ou restaurez une base de '
                                                                                       'données vectorielle du corpus '
                                                                                       'avant de synchroniser les '
                                                                                       'brouillons issus de PDF.',
 'runtime.help.current_chroma_path': 'Chemin Chroma actuel',
 'runtime.help.decomposition_max_tokens': 'Nombre maximal de jetons pour la décomposition',
 'runtime.help.default_embedding_model': 'Modèle de plongement vectoriel par défaut',
 'runtime.help.default_embedding_provider': 'Fournisseur de plongements vectoriels par défaut',
 'runtime.help.default_provider_profile': 'Profil fournisseur par défaut',
 'runtime.help.default_review_preset': 'Préréglage de révision par défaut',
 'runtime.help.delete_audit_history': 'Supprimer l’historique d’audit…',
 'runtime.help.deletes_all_loaded_browser_jsonl_workspace_data_and_every_collection_in_the_current_chroma_pers': 'Supprime '
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
 'runtime.help.do_not_add_to_jsonl': 'Ne pas ajouter au JSONL',
 'runtime.help.download_merged_jsonl_immediately': 'Télécharger immédiatement le JSONL fusionné',
 'runtime.help.draft_record_from_pdf_page': 'Créer une fiche provisoire à partir de la page PDF',
 'runtime.help.drafts_persist_across_navigation_and_browser_refresh_the_40_most_recent_submitted_question_inst': 'Les '
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
 'runtime.help.drop_one_or_more_jsonl_files_anywhere_on_this_page_or_choose_files_manually_each_file_stays_in_': 'Déposez '
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
 'runtime.help.each_action_lets_you_choose_provider_model_parameters_and_run_mode': 'Chaque action permet de choisir le '
                                                                                   'fournisseur, le modèle, les '
                                                                                   'paramètres et le mode d’exécution.',
 'runtime.help.each_cache_record_stores_the_original_rag_query_instructions_run_parameters_answer_evidence_ret': 'Chaque '
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
 'runtime.help.enter_the_new_value_arrays_objects_use_json_enter_null_for_null': 'Saisissez la nouvelle valeur. Les '
                                                                                'tableaux et objets utilisent JSON. '
                                                                                'Saisissez __NULL__ pour une valeur '
                                                                                'nulle.',
 'runtime.help.evidence_retrieval_and_pipeline_details': 'Détails des preuves, du repérage et du pipeline',
 'runtime.help.expand_all_ui_panels': 'Développer tous les panneaux de l’interface',
 'runtime.help.expand_navigation_sidebar': 'Développer le volet de navigation',
 'runtime.help.filter_linked_records': 'Filtrer les fiches liées',
 'runtime.help.five_most_recent_runs': 'Cinq exécutions les plus récentes',
 'runtime.help.freellm_openai_model_selection': 'Sélection du modèle FreeLLM / OpenAI',
 'runtime.help.generation_defaults_advanced_parameters': 'Valeurs de génération par défaut et paramètres avancés',
 'runtime.help.latest_100_response_cache_entries_use_response_faq_for_full_answer_evidence_browsing_and_re_run': 'Les '
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
                                                                                                                'bibliothèque '
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
 'runtime.help.llm_query_decomposition_french_query_formulation': 'Décomposition de la requête par LLM + formulation de '
                                                                 'requêtes en français',
 'runtime.help.llm_review_workspace': 'Espace de révision LLM',
 'runtime.help.load_this_pdf_in_pdf_explorer_first': 'Chargez d’abord ce PDF dans l’explorateur PDF',
 'runtime.help.local_record_changed_since_job_started': 'la fiche locale a été modifiée depuis le début de la tâche',
 'runtime.help.match_link_page_to_record': 'Faire correspondre et lier la page à une fiche',
 'runtime.help.max_chars_evidence_record': 'Nombre maximal de caractères / preuve',
 'runtime.help.merge_and_replace_selected_tabs': 'Fusionner et remplacer les onglets sélectionnés',
 'runtime.help.mixed_across_records': 'valeurs variables selon les fiches',
 'runtime.help.model_selection_mode': 'Mode de sélection du modèle',
 'runtime.help.new_jsonl_tab_name': 'Nom du nouvel onglet JSONL',
 'runtime.help.no_answer_returned': 'Aucune réponse reçue.',
 'runtime.help.no_audit_history_recorded': 'Aucun historique d’audit enregistré.',
 'runtime.help.no_background_operations_yet': 'Aucune opération en arrière-plan pour le moment.',
 'runtime.help.no_cached_responses_yet': 'Aucune réponse en mémoire cache pour le moment.',
 'runtime.help.no_changes_proposed': 'Aucune modification proposée.',
 'runtime.help.no_corpus_chroma_collections': 'Aucune collection Chroma du corpus',
 'runtime.help.no_events_recorded': 'Aucun évènement enregistré.',
 'runtime.help.no_evidence_returned': 'Aucune preuve reçue.',
 'runtime.help.no_evidence_selected_yet_use_add_to_evidence_on_record_search_rows': 'Aucune preuve sélectionnée. '
                                                                                   'Utilisez « Ajouter aux preuves » '
                                                                                   'dans une fiche ou un résultat de '
                                                                                   'recherche.',
 'runtime.help.no_full_evidence_retained': 'Aucune preuve intégrale conservée.',
 'runtime.help.no_linked_records_match_this_filter': 'Aucune fiche liée ne correspond à ce filtre.',
 'runtime.help.no_llm_provider_profiles_configured': 'Aucun profil fournisseur LLM n’est configuré.',
 'runtime.help.no_matching_records': 'Aucune fiche correspondante',
 'runtime.help.no_matching_records_2': 'Aucune fiche correspondante.',
 'runtime.help.no_models_match_this_filter': 'Aucun modèle ne correspond à ce filtre.',
 'runtime.help.no_pdf_pages_linked_to_this_record': 'Aucune page PDF n’est liée à cette fiche.',
 'runtime.help.no_rag_jobs_yet_start_one_below': 'Aucune tâche RAG pour le moment. Lancez-en une ci-dessous.',
 'runtime.help.no_rag_pipeline_runs_recorded_yet': 'Aucune exécution de pipeline RAG enregistrée pour le moment.',
 'runtime.help.no_record_selected': 'Aucune fiche sélectionnée.',
 'runtime.help.no_records_linked_to_this_page_yet': 'Aucune fiche n’est encore liée à cette page.',
 'runtime.help.no_records_match_the_current_filters': 'Aucune fiche ne correspond aux filtres actuels.',
 'runtime.help.no_records_match_this_work': 'Aucune fiche ne correspond à cette œuvre.',
 'runtime.help.no_visible_columns': 'Aucune colonne visible.',
 'runtime.help.nuke_derridai_workspace': 'EFFACER l’espace de travail DerridAI',
 'runtime.help.ocr_text_cleanup': 'ROC / nettoyage du texte',
 'runtime.help.on_when_background_operations_finish': 'Activer à la fin des opérations en arrière-plan',
 'runtime.help.only_modify_records_whose_value_actually_differs': 'Modifier uniquement les fiches dont la valeur '
                                                                 'diffère réellement',
 'runtime.help.open_a_corpus_workspace': 'Ouvrir un espace de travail du corpus',
 'runtime.help.open_a_pdf_to_render_pages_read_its_embedded_title_metadata_extract_text_and_move_directly_betw': 'Ouvrez '
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
 'runtime.help.open_a_source_pdf': 'Ouvrir un PDF source',
 'runtime.help.openai_compatible_freellm': 'Compatible avec OpenAI / FreeLLM',
 'runtime.help.optional_constraints_on_the_answer_kept_separate_from_the_research_question': 'Contraintes facultatives '
                                                                                            'sur la réponse, '
                                                                                            'conservées séparément de '
                                                                                            'la question de recherche.',
 'runtime.help.optional_instructions_applied_to_every_record_in_this_batch': 'Instructions facultatives appliquées à '
                                                                            'chaque fiche de ce lot.',
 'runtime.help.parentheses_evaluate_this_block_as_one_boolean_value': 'Parenthèses : évaluer ce bloc comme une seule '
                                                                     'valeur booléenne',
 'runtime.help.pipeline_query_metadata': 'Métadonnées de la requête du pipeline',
 'runtime.help.preview_this_version': 'Aperçu de cette version',
 'runtime.help.proposals_are_intentionally_hidden_until_every_queued_record_has_been_processed': 'Les propositions '
                                                                                                'restent '
                                                                                                'volontairement '
                                                                                                'masquées jusqu’à ce '
                                                                                                'que toutes les fiches '
                                                                                                'en file aient été '
                                                                                                'traitées.',
 'runtime.help.proposed_changes_for_this_record': 'Modifications proposées pour cette fiche',
 'runtime.help.provider_choice_default_review_preset_and_whether_llm_review_opens_interactively_or_runs_as_a_b': 'Choix '
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
 'runtime.help.provider_endpoints_credentials_models_concurrency_limits_generation_defaults_readiness_and_inde': 'Les '
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
 'runtime.help.query_decomposition_max_tokens': 'Nombre maximal de jetons pour la décomposition de la requête',
 'runtime.help.question_instructions': 'Question et instructions',
 'runtime.help.rag_pipeline_activity': 'Activité du pipeline RAG',
 'runtime.help.rag_pipeline_defaults': 'Valeurs par défaut du pipeline RAG',
 'runtime.help.rag_response_cache': 'Mémoire cache des réponses RAG',
 'runtime.help.rag_response_grade': 'Évaluation de la réponse RAG',
 'runtime.help.raw_evidence_tagged_answer': 'Réponse brute balisée par preuve',
 'runtime.help.recall_a_previous_question': 'Retrouver une question précédente…',
 'runtime.help.recent_audit_history': 'Historique d’audit récent',
 'runtime.help.recent_cached_responses': 'Réponses récentes en mémoire cache',
 'runtime.help.recent_rag_pipelines': 'Pipelines RAG récents',
 'runtime.help.record_a_json_jsonl': 'Fiche A — JSON / JSONL',
 'runtime.help.record_b_json_jsonl': 'Fiche B — JSON / JSONL',
 'runtime.help.records_linked_anywhere_in_this_pdf': 'Fiches liées à une page de ce PDF',
 'runtime.help.records_selected_across_corpus_tables_are_pinned_into_this_run_you_can_also_bypass_retrieval_en': 'Les '
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
 'runtime.help.remove_all_pdf_links': 'Supprimer tous les liens PDF',
 'runtime.help.render_pages_extract_text_connect_pages_to_records_and_run_llm_assisted_source_workflows': 'Affichez les '
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
 'runtime.help.request_notification_permission': 'Demander l’autorisation d’envoyer des notifications',
 'runtime.help.research_question_prompt': 'Question de recherche / invite',
 'runtime.help.research_run_context': 'Contexte de l’exécution de recherche',
 'runtime.help.reset_table_columns': 'Réinitialiser les colonnes du tableau',
 'runtime.help.reset_ui_choices_or_remove_audit_history_without_deleting_records': 'Réinitialisez les choix de '
                                                                                  'l’interface ou supprimez '
                                                                                  'l’historique d’audit sans supprimer '
                                                                                  'les fiches.',
 'runtime.help.restore_removed_upsert_queue_items': 'Rétablir les éléments retirés de la file de synchronisation',
 'runtime.help.restore_this_version': 'Rétablir cette version',
 'runtime.help.retrieval_fusion_reranking_evidence_budget_and_query_decomposition_defaults_per_run_generation_': 'Valeurs '
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
 'runtime.help.review_add_draft': 'Réviser / ajouter le brouillon',
 'runtime.help.review_link_page': 'Réviser et lier la page',
 'runtime.help.same_model_grading_warning': 'Avertissement : même modèle pour l’évaluation.',
 'runtime.help.saved_to_response_faq_when_caching_succeeds': 'Enregistré dans la bibliothèque de réponses lorsque la '
                                                            'mise en cache réussit.',
 'runtime.help.saved_with_the_cached_rag_query_when_a_response_cache_record_is_available': 'Enregistré avec la requête '
                                                                                          'RAG mise en cache '
                                                                                          'lorsqu’une entrée '
                                                                                          'correspondante est '
                                                                                          'disponible.',
 'runtime.help.saving_updates_this_record_in_place_under_the_same_chroma_id_and_regenerates_its_embedding_when': 'L’enregistrement '
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
 'runtime.help.search_cached_questions': 'Rechercher dans les questions en mémoire cache',
 'runtime.help.search_text_in_this_file': 'Rechercher du texte dans ce fichier',
 'runtime.help.select_all_changes': 'Sélectionner toutes les modifications',
 'runtime.help.select_all_results': 'Sélectionner tous les résultats',
 'runtime.help.select_or_create_a_corpus_vector_database_first': 'Sélectionnez ou créez d’abord une base de données '
                                                                'vectorielle du corpus.',
 'runtime.help.select_or_paste_two_records_to_compare_them': 'Sélectionnez ou collez deux fiches pour les comparer.',
 'runtime.help.select_record_changes': 'Sélectionner les modifications de fiches',
 'runtime.help.select_two_records': 'Sélectionner deux fiches',
 'runtime.help.select_visible_records': 'Sélectionner les fiches visibles',
 'runtime.help.selected_evidence_only_retrieval_disabled': 'Preuves sélectionnées seulement · repérage désactivé',
 'runtime.help.start_from_scratch': 'Recommencer à zéro',
 'runtime.help.start_typing_to_search_loaded_records': 'Commencez à taper pour rechercher dans les fiches chargées.',
 'runtime.help.stop_after_current': 'Arrêter après l’élément en cours',
 'runtime.help.switch_freely_between_interactive_review_background_review_and_aggregate_auto_improve_before_st': 'Avant '
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
 'runtime.help.system_cache_only_this_collection_is_intentionally_excluded_from_corpus_vector_stores_corpus_db': 'Mémoire '
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
 'runtime.help.text_review_runs_separately_so_output_stays_bounded': 'La révision du texte s’exécute séparément afin de '
                                                                    'limiter la taille de la sortie.',
 'runtime.help.these_records_are_identical_across_all_compared_fields': 'Ces fiches sont identiques pour tous les '
                                                                       'champs comparés.',
 'runtime.help.this_cannot_be_undone_unless_you_have_exported_backed_up_your_jsonl_and_chroma_data': 'Cette action est '
                                                                                                    'irréversible, '
                                                                                                    'sauf si vous avez '
                                                                                                    'exporté ou '
                                                                                                    'sauvegardé vos '
                                                                                                    'données JSONL et '
                                                                                                    'Chroma.',
 'runtime.help.this_is_a_draft_generated_by_an_llm_review_attribution_page_metadata_quotation_provenance_and_t': 'Il '
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
 'runtime.help.this_is_the_reconstructed_original_state_before_tracked_updates': 'Il s’agit de l’état d’origine '
                                                                                'reconstitué avant les modifications '
                                                                                'consignées.',
 'runtime.help.this_local_record_changed_after_the_llm_job_started_current_values_below_may_differ_from_the_va': 'Cette '
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
 'runtime.help.this_setting_is_fixed_by_the_administrator_approved_researcher_profile': 'Ce paramètre est fixé par le '
                                                                                       'profil chercheur approuvé par '
                                                                                       'l’administrateur.',
 'runtime.help.top_level_and_or_plus_explicit_nested_groups': 'ET/OU au niveau supérieur avec groupes imbriqués '
                                                             'explicites',
 'runtime.help.type_nuke_to_enable': 'Tapez NUKE pour activer',
 'runtime.help.unlink_record_from_pdf': 'Dissocier la fiche du PDF',
 'runtime.help.use_as_current_page_text': 'Utiliser comme texte de la page actuelle',
 'runtime.help.use_extract_current_page_or_extract_all_text_if_both_pdf_js_and_pymupdf_find_no_text_the_page_l': 'Utilisez '
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
 'runtime.help.vector_database_defaults': 'Valeurs par défaut des bases de données vectorielles',
 'runtime.help.vector_database_or_selected_evidence_required': 'Base de données vectorielle ou preuves sélectionnées '
                                                              'requises',
 'runtime.help.waiting_for_model': 'En attente du modèle…',
 'runtime.help.when_more_than_one_provider_profile_is_configured_derridai_defaults_grading_to_a_profile_differ': 'Lorsque '
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
                                                                                                                'réponse.',
 'runtime.history_suffix': 'historique.',
 'runtime.identical_compared_fields': 'Ces fiches sont identiques pour tous les champs comparés.',
 'runtime.identical_fields': 'champs identiques',
 'runtime.inline': 'Dans le texte',
 'runtime.inline_citation': 'Citation dans le texte',
 'runtime.inline_cite': 'Citation dans le texte',
 'runtime.inspect_differences': 'Examiner les différences de champs et de texte',
 'runtime.instructions': 'Instructions',
 'runtime.interactive_foreground': 'Premier plan interactif',
 'runtime.jsonl_destination': 'Destination JSONL',
 'runtime.jsonl_tabs': 'Onglets JSONL',
 'runtime.kind_filter_help': 'Le filtre de type restreint les ID de modèles détectés par le point de terminaison selon '
                            'leur nom. Le routage automatique envoie le modèle auto; le mode manuel accepte tout ID de '
                            'modèle compatible.',
 'runtime.kind_filter_prefix': 'Le filtre de type restreint selon leur nom les ID de modèles détectés par le point de '
                              'terminaison. Le routage automatique envoie le modèle',
 'runtime.kind_filter_suffix': '; le mode manuel accepte tout ID de modèle compatible.',
 'runtime.last': 'Dernier',
 'runtime.lexical_vector': 'Lexical/vectoriel',
 'runtime.lexical_vector_fallback': 'Solution de rechange lexicale/vectorielle',
 'runtime.linked_pdf': 'le PDF lié',
 'runtime.linked_records': 'fiches liées',
 'runtime.linked_works': 'œuvres liées',
 'runtime.llm_operation': 'Tâche LLM',
 'runtime.llm_proposals': 'Propositions du LLM',
 'runtime.llm_providers': 'Fournisseurs LLM',
 'runtime.llm_providers_2': 'Fournisseurs LLM',
 'runtime.llm_review': 'Révision par LLM',
 'runtime.load': 'Charger',
 'runtime.load_jsonl_first': 'Chargez d’abord des fiches JSONL.',
 'runtime.loaded_records': 'fiches chargées',
 'runtime.loading_view': 'Chargement de la vue',
 'runtime.make_default': 'Définir par défaut',
 'runtime.manual': 'Manuel',
 'runtime.manual_model_id': 'Identifiant manuel du modèle',
 'runtime.match_all_and': 'Correspondre à TOUTES (ET)',
 'runtime.match_any_or': 'Correspondre à AU MOINS UNE (OU)',
 'runtime.max_output': 'Sortie maximale',
 'runtime.max_output_tokens': 'Nombre maximal de jetons de sortie',
 'runtime.merge_jsonl_tabs': 'Fusionner les onglets JSONL',
 'runtime.merge_tabs_help': 'Les onglets non sélectionnés demeurent inchangés. Les onglets sources sélectionnés sont '
                           'retirés de l’espace de travail après la création de la fusion; leurs fichiers sources sur '
                           'disque ne sont pas supprimés.',
 'runtime.merged_file_name': 'Nom du fichier fusionné',
 'runtime.metadata': 'Métadonnées',
 'runtime.metadata_output': 'Sortie des métadonnées',
 'runtime.mixed_leave_unchanged': 'Valeurs mixtes / laisser inchangé',
 'runtime.mmr_fetch_k': 'Bassin MMR (fetch_k)',
 'runtime.mmr_lambda': 'Lambda MMR',
 'runtime.model_default': 'valeur par défaut du modèle',
 'runtime.model_kind': 'Type de modèle',
 'runtime.model_kind_filter': 'Filtre du type de modèle',
 'runtime.model_mode': 'Mode du modèle',
 'runtime.model_name': 'Nom du modèle',
 'runtime.model_readiness': 'État de préparation du modèle',
 'runtime.model_selection_mode': 'Mode de sélection du modèle',
 'runtime.model_size': 'Taille du modèle',
 'runtime.more_text_tools': 'Autres outils de texte',
 'runtime.needs_review': 'À réviser',
 'runtime.needs_review_records': 'Fiches à réviser',
 'runtime.new_rag_query': 'Nouvelle requête RAG',
 'runtime.new_value': 'Nouvelle valeur',
 'runtime.newer': 'Plus récent →',
 'runtime.next': 'Suivant',
 'runtime.next_2': 'Suivant →',
 'runtime.no': 'Non',
 'runtime.no_cached_rag_search': 'Aucune réponse RAG mise en cache ne correspond à cette recherche.',
 'runtime.no_cached_responses': 'Aucune réponse mise en cache pour le moment.',
 'runtime.no_changes_proposed': 'Aucune modification proposée',
 'runtime.no_current_pdf_persist': 'Impossible d’enregistrer le PDF actuel dans le stockage persistant',
 'runtime.no_current_pdf_restore': 'Impossible de restaurer le PDF actuel',
 'runtime.no_data': 'Aucune donnée',
 'runtime.no_database': 'Aucune base de données',
 'runtime.no_earlier_location': 'Il n’y a aucun emplacement précédent dans l’historique de navigation.',
 'runtime.no_forward_location': 'Il n’y a aucun emplacement suivant dans l’historique de navigation.',
 'runtime.no_loaded_updates_history': 'Aucune fiche chargée n’a d’historique de modifications',
 'runtime.no_matches': 'Aucune correspondance',
 'runtime.no_next_newer': 'Il n’y a aucun élément suivant ni aucune version plus récente.',
 'runtime.no_pending_changes': 'Aucune modification en attente',
 'runtime.no_record_selected': 'Aucune fiche n’est sélectionnée.',
 'runtime.no_reranking': 'Aucun reclassement',
 'runtime.no_updates_history': 'Cette fiche n’a aucun historique de modifications',
 'runtime.no_workspace_prefs': 'Impossible d’enregistrer les préférences IndexedDB',
 'runtime.no_workspace_restore': 'Impossible de restaurer l’espace de travail IndexedDB',
 'runtime.none': 'Aucun',
 'runtime.none_reported': 'Aucun élément signalé.',
 'runtime.not_warmed': 'Pas encore préchauffé dans cette session',
 'runtime.notice': 'Avis',
 'runtime.ocr_text': 'ROC / texte',
 'runtime.offline': 'Hors ligne',
 'runtime.older': '← Plus ancien',
 'runtime.ollama_endpoint': 'Point de terminaison Ollama',
 'runtime.on_this_page': 'sur cette page',
 'runtime.online': 'En ligne',
 'runtime.only_changed_expanded': 'Seuls les champs modifiés sont développés par défaut.',
 'runtime.open_dashboard': 'Ouvrir l’accueil',
 'runtime.open_full_details': 'Ouvrir tous les détails',
 'runtime.open_in_faq': 'Ouvrir dans la bibliothèque de réponses',
 'runtime.open_jsonl': 'Ouvrir un fichier JSONL',
 'runtime.open_library': 'Ouvrir la bibliothèque',
 'runtime.open_pdf_explorer': 'Ouvrir l’explorateur PDF',
 'runtime.open_result': 'Ouvrir le résultat',
 'runtime.openai_compatible_endpoint': 'Point de terminaison compatible avec OpenAI',
 'runtime.operation_timeline': 'Chronologie de l’opération',
 'runtime.original_language': 'Langue originale',
 'runtime.original_title': 'Titre original',
 'runtime.other_fields': 'Autres champs',
 'runtime.page': 'Page',
 'runtime.page_end': 'Dernière page',
 'runtime.page_start': 'Première page',
 'runtime.page_text': 'Texte de la page',
 'runtime.pages': 'Pages',
 'runtime.pdf_document': 'Document PDF',
 'runtime.pdf_explorer': 'Explorateur PDF',
 'runtime.pdf_file': 'Fichier PDF',
 'runtime.pdf_links': 'Liens PDF',
 'runtime.pdf_page': 'Page PDF',
 'runtime.pdf_pages': 'Pages PDF',
 'runtime.pending': 'En attente',
 'runtime.pipeline_timings': 'Durées du pipeline',
 'runtime.pipeline_timings_source': 'Adapté des étapes du pipeline DerridAI fournies',
 'runtime.precomputed_vectors': 'Vecteurs précalculés',
 'runtime.preview_record': 'Aperçu de la fiche',
 'runtime.previous': 'Précédent',
 'runtime.previous_2': '← Précédent',
 'runtime.primary_text': 'Texte principal',
 'runtime.profiles': 'profils',
 'runtime.progress': 'Progression',
 'runtime.proposed': 'Proposé',
 'runtime.proposed_change': 'modification proposée',
 'runtime.provider_concurrency_help': 'La simultanéité est propre à chaque profil. Ollama démarre normalement à 1 '
                                     'requête simultanée; les profils FreeLLM ou compatibles avec OpenAI utilisent 32 '
                                     'par défaut et peuvent être réglés de 1 à 64.',
 'runtime.provider_model': 'Fournisseur / modèle',
 'runtime.provider_overview_help': 'Créez et configurez les fournisseurs réutilisables une seule fois, puis '
                                  'sélectionnez-les partout où DerridAI utilise un LLM.',
 'runtime.provider_profile': 'Profil fournisseur',
 'runtime.provider_profiles': 'Profils fournisseurs',
 'runtime.provider_profiles_help': 'Points de terminaison, modèle et paramètres de génération réutilisables pour tous '
                                  'les flux de travail LLM. Les profils compatibles avec OpenAI interrogent GET '
                                  '/models lorsque le point de terminaison le permet. Les profils Ollama qui partagent '
                                  'un point de terminaison utilisent une même limite d’exécution et la plus faible '
                                  'limite de simultanéité configurée pour ce point de terminaison.',
 'runtime.publication_place': 'Lieu de publication',
 'runtime.publication_year': 'Année de publication',
 'runtime.publisher': 'Maison d’édition',
 'runtime.quantization': 'Quantification',
 'runtime.query_decomposition': 'Décomposition de la requête',
 'runtime.question': 'Question',
 'runtime.question_prompt': 'Question / invite',
 'runtime.queued': 'En attente',
 'runtime.quotation_chain': 'Chaîne de citations',
 'runtime.quotation_provenance': 'Provenance des citations',
 'runtime.quoted_addressee': 'Destinataire cité',
 'runtime.quoted_author': 'Auteur cité',
 'runtime.quoted_referent': 'Référent cité',
 'runtime.quoted_work': 'Œuvre citée',
 'runtime.rag_language_exists_suffix': 'existe, le RAG utilise la collection linguistique correspondante. Les langues '
                                      'demandées qui n’existent pas utilisent la collection source avec un filtre sur',
 'runtime.rag_pipeline': 'Pipeline RAG',
 'runtime.rag_result': 'Résultat RAG',
 'runtime.random': 'aléatoire',
 'runtime.rationale': 'Justification',
 'runtime.ready': 'Prêt',
 'runtime.reasoning': 'Raisonnement',
 'runtime.record': 'Fiche',
 'runtime.record_actions': 'Actions sur la fiche',
 'runtime.record_annotation': 'Annotation de fiche',
 'runtime.record_comparison': 'Comparaison de fiches',
 'runtime.record_history': 'Historique de la fiche',
 'runtime.record_preview': 'Aperçu de la fiche',
 'runtime.records': 'fiches',
 'runtime.records_to_sync': 'Fiches à synchroniser',
 'runtime.region_author': 'Auteur de la région',
 'runtime.region_type': 'Type de région',
 'runtime.reject_selected': 'Rejeter la sélection',
 'runtime.rejected_fields': 'champs rejetés',
 'runtime.rejected_results': 'résultats rejetés',
 'runtime.remove': 'Supprimer',
 'runtime.remove_condition': 'Supprimer la condition',
 'runtime.remove_evidence': 'Retirer la preuve',
 'runtime.remove_filter': 'Supprimer le filtre',
 'runtime.remove_from_queue': 'Retirer de la file',
 'runtime.remove_group': 'Supprimer le groupe',
 'runtime.remove_work': 'Retirer l’œuvre',
 'runtime.remove_work_help': 'Retirez toutes les fiches de cette œuvre des fichiers JSONL chargés sélectionnés et, au '
                            'besoin, de la collection Chroma choisie. La suppression dans une collection principale '
                            'retire également les fiches correspondantes de ses collections linguistiques.',
 'runtime.request_configuration': 'Configuration de la requête',
 'runtime.rerank_top_n': 'Reclasser les N premiers',
 'runtime.reranker': 'Module de reclassement',
 'runtime.researcher_access': 'Accès des chercheurs',
 'runtime.reset_defaults': 'Rétablir les valeurs par défaut',
 'runtime.response_faq': 'Bibliothèque de réponses',
 'runtime.response_language': 'Langue de la réponse',
 'runtime.responses': 'réponses',
 'runtime.restore_original': 'Rétablir l’original',
 'runtime.result_summary': 'Résumé du résultat',
 'runtime.retrieval_diagnostics': 'Diagnostics de repérage',
 'runtime.retrieval_k': 'k de repérage',
 'runtime.retrieval_routes': 'Voies de repérage',
 'runtime.review': 'Réviser',
 'runtime.review_available_results': 'Réviser les résultats disponibles',
 'runtime.review_behavior': 'Comportement de révision',
 'runtime.review_failed': 'Échec de la révision',
 'runtime.review_preset': 'Préréglage de révision',
 'runtime.review_reason': 'Motif de révision',
 'runtime.review_results': 'Résultats de la révision',
 'runtime.review_status': 'État de la révision',
 'runtime.reviewed': 'Révisé',
 'runtime.reviewing': 'Révision',
 'runtime.rotate_left_90': 'Rotation de 90° à gauche',
 'runtime.rotate_right_90': 'Rotation de 90° à droite',
 'runtime.run_in_background': 'Exécuter en arrière-plan',
 'runtime.run_in_foreground': 'Exécuter au premier plan',
 'runtime.run_mode': 'Mode d’exécution',
 'runtime.run_rag_query': 'Lancer une requête RAG',
 'runtime.run_review': 'Lancer la révision',
 'runtime.running': 'En cours…',
 'runtime.running_rag_pipeline': 'Pipeline RAG en cours',
 'runtime.same_model_grade_help': 'Ce fournisseur et ce modèle ont aussi servi à générer la réponse RAG. '
                                 'L’autoévaluation peut être systématiquement biaisée; utilisez un autre modèle pour '
                                 'obtenir une évaluation plus indépendante.',
 'runtime.save_columns': 'Enregistrer les colonnes',
 'runtime.search_cached_questions': 'Rechercher dans les questions mises en cache',
 'runtime.search_page_text': 'Rechercher dans le texte de la page',
 'runtime.search_record_id_work_file': 'Rechercher l’ID de fiche, l’œuvre ou le fichier source',
 'runtime.secondary_text': 'Texte secondaire',
 'runtime.select_all': 'Tout sélectionner',
 'runtime.select_change_first': 'Sélectionnez d’abord au moins une modification proposée.',
 'runtime.select_metadata': 'Sélectionner les métadonnées',
 'runtime.select_none': 'Tout désélectionner',
 'runtime.select_record_first': 'Sélectionnez d’abord une fiche.',
 'runtime.selected_changes_note': 'sélectionnées · les modifications acceptées sont immédiatement retirées de cette '
                                 'file d’attente',
 'runtime.selected_evidence': 'preuves sélectionnées',
 'runtime.selected_records': 'Fiches sélectionnées',
 'runtime.selected_value': 'Valeur sélectionnée',
 'runtime.selection_mode': 'Mode de sélection',
 'runtime.self_grade_help': 'Cette évaluation a utilisé le même modèle que celui qui a généré la réponse; '
                           'interprétez-la comme une autoévaluation plutôt que comme une évaluation indépendante.',
 'runtime.semantic_classification_confidence': 'Fiabilité de la classification sémantique',
 'runtime.semantic_function': 'Fonction sémantique',
 'runtime.semantics': 'Sémantique',
 'runtime.short_title': 'Titre abrégé',
 'runtime.source': 'Source',
 'runtime.source_collection': 'Collection source',
 'runtime.start_operation': 'Lancer l’opération',
 'runtime.start_typing_records': 'Commencez à saisir du texte pour rechercher les fiches chargées.',
 'runtime.started': 'Démarré',
 'runtime.started_by': 'Lancé par',
 'runtime.status': 'État',
 'runtime.status_error': 'Erreur d’état',
 'runtime.summary': 'Résumé',
 'runtime.target_records': 'Fiches ciblées',
 'runtime.temperature': 'Température',
 'runtime.text': 'Texte',
 'runtime.text_length': 'Longueur du texte',
 'runtime.think': 'Réflexion',
 'runtime.this_version': 'Cette version',
 'runtime.traditional_search': 'Recherche traditionnelle',
 'runtime.translation': 'Traduction',
 'runtime.translator': 'Traducteur',
 'runtime.type_choose_installed_model': 'Saisissez ou choisissez un modèle installé',
 'runtime.type_choose_model': 'Saisissez ou choisissez un ID de modèle',
 'runtime.type_record_work_author_file': 'Saisissez un ID de fiche, une œuvre, un auteur ou un fichier…',
 'runtime.unavailable': 'Indisponible',
 'runtime.unknown': 'Inconnu',
 'runtime.unknown_error': 'erreur inconnue',
 'runtime.untagged': 'sans étiquette',
 'runtime.untitled_question': 'Question sans titre',
 'runtime.use_model': 'Utiliser le modèle',
 'runtime.value': 'Valeur',
 'runtime.values': 'Valeurs',
 'runtime.vector_defaults_prefix': 'Les nouvelles collections utilisent par défaut les plongements vectoriels Ollama '
                                  'avec',
 'runtime.vector_defaults_suffix': '. Les collections linguistiques Chroma utilisent les étiquettes générales',
 'runtime.verify': 'vérifier',
 'runtime.verify_carefully': 'vérifier attentivement',
 'runtime.viewer_configuration': 'Configuration du visualiseur',
 'runtime.waiting_in_queue': 'En attente dans la file.',
 'runtime.warm': 'Préchauffé',
 'runtime.warming': 'Préchauffage',
 'runtime.warmup': 'Préchauffage',
 'runtime.warmup_failed': 'Échec du préchauffage',
 'runtime.when': 'Lorsque',
 'runtime.words': 'mots',
 'runtime.work_metadata_help_prefix': 'uniquement pour les champs qui doivent être modifiés dans toutes les fiches '
                                     'associées. La modification de',
 'runtime.work_metadata_help_suffix': 'renomme l’œuvre dans toutes les fiches chargées. Chaque champ modifié est '
                                     'consigné dans l’',
 'runtime.works': 'œuvres',
 'runtime.works_and_records': 'Œuvres et fiches',
 'runtime.works_cited': 'Ouvrages cités',
 'runtime.works_referenced': 'Œuvres citées',
 'runtime.yes': 'Oui',
 'llm.connection_from_profile': 'Le point de terminaison et les identifiants proviennent du profil de fournisseur et '
                                'sont gérés de façon centralisée.',
 'llm.manage_provider_profiles': 'Gérer les profils de fournisseur',
 'llm.model_not_set': 'Modèle non défini',
 'llm.openai_compatible': 'Compatible avec OpenAI',
 'llm.provider_profile': 'Profil de fournisseur',
 'nav.annotations': 'Annotations',
 'nav.cache': 'Mémoire cache des réponses',
 'nav.compare': 'Comparer',
 'nav.config': 'Paramètres',
 'nav.dashboard': 'Accueil',
 'nav.faq': 'Bibliothèque de réponses',
 'nav.home': 'Accueil',
 'nav.more_tools': 'Autres outils',
 'nav.pdf': 'Générateur de corpus',
 'nav.providers': 'Fournisseurs LLM',
 'nav.rag': 'Recherche',
 'nav.record': 'Vue de fiche',
 'nav.records': 'Fiches',
 'nav.roles': 'Rôles et autorisations',
 'nav.search': 'Recherche',
 'nav.users': 'Utilisateurs et rôles',
 'nav.vector': 'Bases vectorielles',
 'nav.works': 'Œuvres',
 'operations.active': 'active(s)',
 'operations.background': 'Opérations en arrière-plan',
 'operations.blocking_sync_help': 'Cette synchronisation volumineuse s’exécute au premier plan par lots de 500. Les '
                                  'autres actions DerridAI sont suspendues jusqu’à la fin ou jusqu’à l’annulation.',
 'operations.cancelled_ollama_wait': 'Annulé pendant l’attente d’une place Ollama',
 'operations.cancelled_provider_wait': 'Annulé pendant l’attente d’une place chez le fournisseur',
 'operations.cancelled_queue': 'Annulé pendant l’attente dans la file',
 'operations.cancelling': 'Annulation…',
 'operations.cancelling_after_batch': 'Annulation de la requête en cours…',
 'operations.clear_finished': 'Effacer les opérations terminées',
 'operations.continue_sync': 'Continuer la synchronisation',
 'operations.drag_help': 'Faites glisser les opérations n’importe où · double-cliquez pour réinitialiser',
 'operations.foreground_sync_active_help': 'Attendez la fin de la grande synchronisation au premier plan avant d’en '
                                           'lancer une autre.',
 'operations.foreground_sync_active_title': 'Grande synchronisation déjà en cours',
 'operations.foreground_sync_batch': 'Validation des fiches {start} à {end} sur {total}',
 'operations.foreground_sync_committed': '{count} fiches validées',
 'operations.foreground_sync_complete': '{count} fiches terminées sans créer d’opération en arrière-plan.',
 'operations.foreground_sync_done': '{count} fiches synchronisées vers {store}',
 'operations.foreground_sync_failed': 'Échec de la synchronisation : {message}',
 'operations.foreground_sync_failed_title': 'Échec de la grande synchronisation',
 'operations.foreground_sync_help': 'Les grandes synchronisations sont traitées par petits lots au premier plan afin '
                                    'que le navigateur reste réactif.',
 'operations.foreground_sync_title': 'Synchronisation de {count} fiches',
 'operations.keep_tab_open': 'Gardez cet onglet DerridAI ouvert pendant la synchronisation.',
 'operations.large_sync_background_help': '{count} fiches seront préparées une fois, puis DerridAI construira et '
                                          'validera la collection en arrière-plan. Vous pouvez continuer à travailler '
                                          'pendant l’opération.',
 'operations.large_sync_background_title': 'Construire la collection en arrière-plan?',
 'operations.large_sync_foreground_help': '{count} fiches seront synchronisées par lots au premier plan afin que le '
                                          'navigateur demeure réactif. Gardez cet onglet DerridAI ouvert jusqu’à la '
                                          'fin.',
 'operations.large_sync_foreground_title': 'La grande synchronisation s’exécute au premier plan',
 'operations.minimize': 'Réduire les opérations',
 'operations.no_finished': 'Aucune opération terminée à effacer.',
 'operations.preparing_sync': 'Préparation des fiches…',
 'operations.rag_cancelled': 'Processus RAG annulé',
 'operations.rag_complete': 'Processus RAG terminé',
 'operations.rag_complete_cache_failed': 'Processus RAG terminé; échec de l’écriture dans la mémoire cache des '
                                         'réponses',
 'operations.rag_complete_grade': 'Processus RAG et évaluation automatique terminés',
 'operations.rag_complete_grade_failed': 'Processus RAG terminé; échec de l’évaluation automatique',
 'operations.rag_job_cancelled': 'Tâche RAG annulée',
 'operations.refreshing_after_sync': 'Actualisation de l’état de la collection…',
 'operations.shared_queue': 'Les appels LLM, les pipelines RAG, les constructions de corpus PDF et les '
                            'synchronisations Chroma partagent cette file',
 'operations.show': 'Afficher les opérations',
 'operations.start_background_build': 'Démarrer la construction en arrière-plan',
 'operations.summary': '{active} active(s) · {retained} conservée(s) · {queue}',
 'operations.sync_cancelled': 'Synchronisation annulée. Les lots terminés restent synchronisés.',
 'operations.syncing_records': 'Synchronisation des fiches…',
 'operations.vector_build_queued': '{count} fiches mises en file pour la construction en arrière-plan de {store}',
 'operations.vector_sync_active_help': '{label} doit se terminer ou être annulée avant de démarrer une autre '
                                       'construction.',
 'operations.vector_sync_active_title': 'Une synchronisation vectorielle est déjà active',
 'operations.waiting_to_start': 'En attente de démarrage',
 'pdf_corpus.absolute_safety_splits': 'Scissions au plafond absolu',
 'pdf_corpus.accept': 'Accepter',
 'pdf_corpus.accept_all': 'Tout accepter',
 'pdf_corpus.accept_all_queue': 'Accepter la file',
 'pdf_corpus.accept_blocked_metadata': 'Confirmez les métadonnées requises avant d’accepter cette fiche : {fields}.',
 'pdf_corpus.accept_blocked_source': 'Résolvez ou rejetez ce problème d’extraction de la source avant d’accepter la '
                                     'fiche.',
 'pdf_corpus.accept_clean': 'Accepter les fiches nettes ({count})',
 'pdf_corpus.accept_clean_confirm': 'Accepter {count} fiche(s) sans problème? Les fiches ayant des problèmes de '
                                    'métadonnées, de topologie ou de source resteront à réviser.',
 'pdf_corpus.accept_clean_done': '{count} fiche(s) sans problème acceptée(s). Seules les exceptions restent.',
 'pdf_corpus.accept_next': 'Accepter et suivante',
 'pdf_corpus.accept_selected': 'Accepter la sélection',
 'pdf_corpus.accepted': 'acceptées',
 'pdf_corpus.accepted_label': 'Acceptée',
 'pdf_corpus.accepted_notice': 'Fiche acceptée. Passage à la fiche suivante.',
 'pdf_corpus.active_build_capacity': '{count} construction(s) active(s). Une nouvelle construction est indépendante et '
                                     'utilise la capacité du profil fournisseur sélectionné.',
 'pdf_corpus.active_metadata_tasks': 'Tâches de métadonnées actives',
 'pdf_corpus.active_now': 'Actives maintenant',
 'pdf_corpus.add_evidence': 'Ajouter comme preuve',
 'pdf_corpus.advanced_metadata': 'Métadonnées avancées',
 'pdf_corpus.already_running': 'Cette construction est déjà en cours. Son état en direct est affiché ci-dessous.',
 'pdf_corpus.api_key': 'Clé API',
 'pdf_corpus.attention_required': 'Vérification requise',
 'pdf_corpus.auto_published': 'Révision terminée. {count} fiches ont été publiées automatiquement.',
 'pdf_corpus.auto_retry': 'Relance automatique',
 'pdf_corpus.automatic_resolution': 'Résolution automatique',
 'pdf_corpus.base_url': 'URL de base',
 'pdf_corpus.blocking_pages': '{count} page(s) bloquante(s)',
 'pdf_corpus.blocks': 'blocs',
 'pdf_corpus.boundary_budget_skipped': '{count} transition(s) candidate(s) de moindre valeur résolue(s) par CONSERVER '
                                       'selon le budget LLM.',
 'pdf_corpus.boundary_candidates': 'Transitions candidates',
 'pdf_corpus.boundary_failures_kept': '{count} échec(s) du classificateur résolu(s) par CONSERVER.',
 'pdf_corpus.boundary_review_required': 'Limites à réviser',
 'pdf_corpus.build_configuration': 'Configuration de la construction',
 'pdf_corpus.build_error': 'Erreur de construction',
 'pdf_corpus.build_progress': 'Progression de la construction du corpus',
 'pdf_corpus.build_records': 'Construire l’ensemble de fiches',
 'pdf_corpus.build_resumed': 'Construction reprise depuis son dernier point de contrôle terminé.',
 'pdf_corpus.build_settings_summary': 'Paramètres de construction',
 'pdf_corpus.build_started': 'Construction du corpus démarrée. La progression et les points de contrôle terminés sont '
                             'persistés côté serveur.',
 'pdf_corpus.build_stopped_checkpoint': 'La reprise ne recommence pas les étapes terminées et ne supprime pas les '
                                        'notices validées.',
 'pdf_corpus.build_stopped_help': 'Les points de contrôle terminés ont été conservés. Vérifiez le fournisseur et les '
                                  'paramètres d’exécution ci-dessus, puis reprenez au dernier point de contrôle sûr.',
 'pdf_corpus.build_stopped_title': 'Construction arrêtée avant la fin',
 'pdf_corpus.build_timeline': 'Chronologie de construction',
 'pdf_corpus.building_records': 'Construction des fiches',
 'pdf_corpus.building_records_help': 'DerridAI analyse la structure du document et les frontières sémantiques. '
                                     'L’espace de révision apparaîtra automatiquement dès que des fiches révisables '
                                     'seront enregistrées.',
 'pdf_corpus.building_records_title': 'La construction du corpus est en cours',
 'pdf_corpus.builds': 'Constructions de corpus',
 'pdf_corpus.bulk_confirm': '{action} {count} fiche(s) dans la file actuelle?',
 'pdf_corpus.bulk_done': '{count} fiche(s) mise(s) à jour.',
 'pdf_corpus.bulk_done_metadata_blocked': '{count} fiche(s) admissible(s) acceptée(s); {blocked} fiche(s) exigent '
                                          'encore des décisions de métadonnées et sont maintenant affichées dans la '
                                          'file des métadonnées.',
 'pdf_corpus.cancel': 'Annuler',
 'pdf_corpus.cancel_build': 'Annuler la construction',
 'pdf_corpus.cancel_requested': 'Annulation demandée. L’espace de travail segmenté demeure modifiable, et vous pourrez démarrer une autre construction dès que l’annulation sera terminée.',
 'pdf_corpus.characters': 'car.',
 'pdf_corpus.choose_pdf': 'Choisir un PDF source',
 'pdf_corpus.choose_persisted_pdf': 'Choisir un PDF persistant…',
 'pdf_corpus.choose_source_prompt': 'Choisissez un PDF source pour continuer.',
 'pdf_corpus.choose_value': 'Choisir une valeur…',
 'pdf_corpus.citation_issues': 'problème(s) de citation',
 'pdf_corpus.complete': 'Terminé',
 'pdf_corpus.concurrency': 'Concurrence',
 'pdf_corpus.concurrent_requests': 'requête(s) simultanée(s) max.',
 'pdf_corpus.confidence': 'Confiance',
 'pdf_corpus.configure_another_build': 'Configurer une autre construction',
 'pdf_corpus.configure_new_build': 'Configurer une nouvelle construction',
 'pdf_corpus.confirm_field_value': 'Confirmer la valeur',
 'pdf_corpus.confirm_manifest_continue': 'Confirmer le document et continuer',
 'pdf_corpus.confirm_no_value': 'Confirmer qu’aucune valeur n’est étayée',
 'pdf_corpus.confirmed_on_accept': 'Cette proposition sera confirmée par la personne réviseuse lors de l’acceptation '
                                   'de la fiche.',
 'pdf_corpus.context_budget_detail': 'Le plus grand tour de segmentation exige environ {required} jetons avant les '
                                     'frais généraux du fournisseur; le contexte est de {context}.',
 'pdf_corpus.context_safe': 'Le budget de contexte semble adéquat',
 'pdf_corpus.context_start_blocked': 'Augmentez la fenêtre de contexte ou réduisez la fenêtre/le budget de sortie de '
                                     'segmentation avant de démarrer. Minimum approximatif : {count} jetons.',
 'pdf_corpus.context_unknown': 'Le profil de fournisseur ne précise pas de fenêtre de contexte; DerridAI ne peut pas '
                               'vérifier la capacité à l’avance.',
 'pdf_corpus.context_unsafe': 'Le budget de contexte est insuffisant',
 'pdf_corpus.context_window': 'Fenêtre de contexte',
 'pdf_corpus.context_window_help': 'Nombre maximal de jetons de contexte du modèle pour cette construction.',
 'pdf_corpus.continue_unresolved': 'Continuer avec les métadonnées non résolues',
 'pdf_corpus.coverage': 'Couverture',
 'pdf_corpus.current_stage': 'Étape actuelle',
 'pdf_corpus.data_tab': 'Données',
 'pdf_corpus.decision_saved': 'Décision enregistrée',
 'pdf_corpus.deterministic_fields': 'Champs déterministes',
 'pdf_corpus.deterministic_splits': 'Scissions déterministes',
 'pdf_corpus.discourse_output': 'Sortie des métadonnées discursives',
 'pdf_corpus.disposition.accepted': 'Acceptée',
 'pdf_corpus.disposition.pending': 'En attente',
 'pdf_corpus.disposition.rejected': 'Rejetée',
 'pdf_corpus.document_manifest': 'Manifeste du document',
 'pdf_corpus.document_metadata_edit_help': 'Les modifications mettent à jour les métadonnées héritées et les citations '
                                           'dans toute la construction. Les remplacements explicites effectués par une '
                                           'personne au niveau de la fiche sont conservés.',
 'pdf_corpus.document_metadata_locked_running': 'Les métadonnées du document restent visibles, mais ne peuvent pas '
                                                'être modifiées pendant l’enrichissement actif des fiches. Utilisez un '
                                                'remplacement au niveau d’une fiche déjà traitée, ou attendez la fin '
                                                'de l’enrichissement avant de modifier le manifeste du document.',
 'pdf_corpus.download_jsonl': 'Télécharger le JSONL',
 'pdf_corpus.edit_document_metadata': 'Modifier les métadonnées du document',
 'pdf_corpus.edit_text': 'Modifier le texte',
 'pdf_corpus.elapsed': 'Temps écoulé',
 'pdf_corpus.enrichment_deep': 'Enrichissement savant approfondi',
 'pdf_corpus.enrichment_deep_help': 'Exécute plus largement l’analyse du discours, des citations et l’indexation '
                                    'sémantique. Plus lent; destiné à un enrichissement délibéré.',
 'pdf_corpus.enrichment_fast': 'Construction rapide du corpus',
 'pdf_corpus.enrichment_fast_help': 'Métadonnées déterministes d’abord; analyse des citations seulement en présence '
                                    'd’indices; indexation sémantique désactivée sauf activation ci-dessous.',
 'pdf_corpus.enrichment_strategy': 'Stratégie d’enrichissement',
 'pdf_corpus.enrichment_strategy_help': 'Le mode rapide n’envoie au LLM que les questions de métadonnées réellement '
                                        'utiles. Le mode approfondi élargit l’analyse de l’attribution, des citations '
                                        'et de l’indexation.',
 'pdf_corpus.escalation_provider': 'Fournisseur de relève',
 'pdf_corpus.escalation_provider_help': 'Solution de repli facultative utilisée seulement après l’épuisement des '
                                        'tentatives de sortie structurée du fournisseur principal.',
 'pdf_corpus.escalations': 'escalades',
 'pdf_corpus.eta': 'Temps restant estimé',
 'pdf_corpus.evidence_bindings': 'liens de preuve',
 'pdf_corpus.evidence_help': 'Choisissez un champ pour mettre en évidence uniquement les blocs source liés à cette '
                             'relation de métadonnées.',
 'pdf_corpus.evidence_issues': 'problème(s) de preuve',
 'pdf_corpus.evidence_review_help': 'Sélectionnez un champ de métadonnées pour inspecter ou ajuster ses preuves liées '
                                    'aux blocs sources.',
 'pdf_corpus.evidence_saved': 'Lien de preuve enregistré. La fiche reste ouverte pour révision.',
 'pdf_corpus.evidence_tab': 'Preuves',
 'pdf_corpus.execution_settings': 'Paramètres d’exécution',
 'pdf_corpus.execution_settings_custom': 'Paramètres personnalisés',
 'pdf_corpus.execution_settings_help': 'Ajustez cette construction de corpus sans modifier le profil de fournisseur '
                                       'enregistré. Les budgets d’étape limitent la sortie structurée; ils ne '
                                       'déterminent jamais les limites des notices.',
 'pdf_corpus.execution_settings_using_defaults': 'Valeurs du fournisseur · budget de contexte sûr',
 'pdf_corpus.extracted_source_text': 'Texte source extrait',
 'pdf_corpus.extracted_source_text_help': 'Il s’agit de la référence d’audit produite par l’extraction PDF. Les '
                                          'corrections humaines modifient le texte révisé de la fiche, jamais ces '
                                          'blocs source.',
 'pdf_corpus.extracting': 'Extraction…',
 'pdf_corpus.eyebrow': 'Générateur de corpus',
 'pdf_corpus.field': 'Champ',
 'pdf_corpus.field_evidence': 'Preuves par champ',
 'pdf_corpus.field_status.deterministic': 'déterministe',
 'pdf_corpus.field_status.human_confirmed': 'confirmé par une personne',
 'pdf_corpus.field_status.invalid': 'invalide',
 'pdf_corpus.field_status.llm_inferred': 'inféré par LLM',
 'pdf_corpus.field_status.unresolved': 'non résolu',
 'pdf_corpus.fields_to_resolve': 'champs à résoudre',
 'pdf_corpus.fields_unresolved': 'champs non résolus',
 'pdf_corpus.final_validation': 'Validation finale',
 'pdf_corpus.finalize_publish': 'Finaliser et publier',
 'pdf_corpus.finish_blocked_help': 'La révision des fiches est terminée. Résolvez les obstacles restants ci-dessous; '
                                   'DerridAI activera ensuite automatiquement la publication.',
 'pdf_corpus.finish_corpus_title': 'Terminer le corpus',
 'pdf_corpus.finish_metadata_before_publish': 'Terminer les métadonnées avant de publier',
 'pdf_corpus.finish_metadata_complete': 'Tous les champs de métadonnées requis pour la publication sont résolus et '
                                        'validés.',
 'pdf_corpus.finish_metadata_summary': '{records} fiche(s) contiennent {fields} champ(s) requis non résolu(s).',
 'pdf_corpus.finish_phase': 'Terminer le corpus',
 'pdf_corpus.finish_published_help': 'Cet instantané de publication immuable est terminé. La modification du brouillon '
                                     'crée une nouvelle révision non publiée.',
 'pdf_corpus.finish_ready_help': 'La révision des fiches, les métadonnées requises, la fidélité à la source et la '
                                 'validation de publication sont réussies.',
 'pdf_corpus.flow_metadata_help': 'Toutes les fiches sont acceptées. Relancez ou corrigez les métadonnées incomplètes '
                                  'avant la publication.',
 'pdf_corpus.flow_metadata_title': 'Révision terminée — métadonnées à vérifier',
 'pdf_corpus.flow_published_help': 'Cet instantané publié est immuable. La modification du brouillon crée une nouvelle '
                                   'révision non publiée.',
 'pdf_corpus.flow_published_title': 'Révision publiée',
 'pdf_corpus.flow_ready_help': 'La révision des fiches est terminée. Résolvez toute métadonnée restante, puis publiez '
                               'explicitement.',
 'pdf_corpus.flow_ready_title': 'Prêt à publier',
 'pdf_corpus.flow_review_help': 'Parcourez la file de révision. Accepter et Rejeter s’appliquent immédiatement et '
                                'passent à la proposition suivante.',
 'pdf_corpus.flow_review_title': 'Réviser les fiches générées',
 'pdf_corpus.focus_detail_tabs': 'Vues détaillées de la fiche',
 'pdf_corpus.focus_record_help': 'Évaluez la fiche proposée comme unité savante. Le texte et ses données '
                                 'interprétatives sont réunis afin de permettre une décision rapide.',
 'pdf_corpus.focus_record_title': 'Réviser la fiche proposée',
 'pdf_corpus.focus_view': 'Vue ciblée',
 'pdf_corpus.fragmentation_ratio': 'Taux de micro-lignes',
 'pdf_corpus.generated_records': 'Fiches générées',
 'pdf_corpus.home_empty': 'Aucune construction de corpus. Commencez avec un PDF source dans le Générateur de corpus.',
 'pdf_corpus.home_help': 'Les pipelines PDF-vers-corpus récents restent visibles ici même après avoir quitté le '
                         'Générateur de corpus.',
 'pdf_corpus.home_title': 'Constructions de corpus',
 'pdf_corpus.human_corrected': 'Corrigé par l’humain',
 'pdf_corpus.human_evidence_reason': 'Lien de preuve révisé par une personne.',
 'pdf_corpus.human_fields': 'Champs confirmés/remplacés par l’humain',
 'pdf_corpus.human_metadata_fields': '{count} champ(s) exigent un jugement',
 'pdf_corpus.human_metadata_help': 'Ces champs sont ambigus ou dépendent de la qualité de la source. Révisez la fiche '
                                   'proposée, les preuves, les valeurs permises et la provenance avant de confirmer '
                                   'une valeur.',
 'pdf_corpus.human_resolution': 'Résolution humaine',
 'pdf_corpus.human_review': 'Révision humaine',
 'pdf_corpus.immutable_text': 'Texte source immuable',
 'pdf_corpus.indexing_output': 'Sortie des métadonnées d’indexation',
 'pdf_corpus.inherited_fields': 'Champs hérités',
 'pdf_corpus.inspect_remaining_work': 'Examiner le travail restant',
 'pdf_corpus.interpretive_data': 'Données interprétatives',
 'pdf_corpus.interpretive_metadata': 'Métadonnées interprétatives',
 'pdf_corpus.issue_filter': 'Type de problème',
 'pdf_corpus.issue_filter_all': 'Tous les problèmes',
 'pdf_corpus.label_source': 'Source',
 'pdf_corpus.last_progress': 'Dernière tâche terminée',
 'pdf_corpus.llm_adjudications': 'Adjudications LLM',
 'pdf_corpus.llm_batch_calls': 'Appels LLM groupés',
 'pdf_corpus.llm_calls': 'appels LLM',
 'pdf_corpus.llm_contribution': 'Contribution du LLM',
 'pdf_corpus.llm_contribution_help': 'Mode {mode} · {calls} appel(s) de famille au modèle · {minutes} min de temps '
                                     'modèle.',
 'pdf_corpus.llm_contribution_title': 'Ce que l’automatisation a réellement apporté',
 'pdf_corpus.llm_retries': 'nouvelles tentatives',
 'pdf_corpus.llm_review_fields': 'Champs LLM à réviser',
 'pdf_corpus.llm_splits': 'Scissions LLM',
 'pdf_corpus.llm_usable_fields': 'Champs LLM utilisables',
 'pdf_corpus.loading_records': 'Chargement des fiches générées…',
 'pdf_corpus.manage_providers': 'Gérer les profils fournisseurs',
 'pdf_corpus.manifest_author': 'Auteur du document',
 'pdf_corpus.manifest_calls': 'analyse du document',
 'pdf_corpus.manifest_confirmed': 'Manifeste du document confirmé. La segmentation sémantique a commencé.',
 'pdf_corpus.manifest_edition': 'Édition',
 'pdf_corpus.manifest_help': 'Ces valeurs sont héritées de façon déterministe par les fiches. L’enregistrement '
                             'régénère les métadonnées héritées et les citations et rouvre les fiches touchées pour '
                             'révision.',
 'pdf_corpus.manifest_isbn': 'ISBN',
 'pdf_corpus.manifest_language': 'Langue du document',
 'pdf_corpus.manifest_main_end': 'Fin du texte principal à la page PDF physique',
 'pdf_corpus.manifest_main_start': 'Début du texte principal à la page PDF physique',
 'pdf_corpus.manifest_notes': 'Notes appuyées par la source',
 'pdf_corpus.manifest_original_language': 'Langue originale',
 'pdf_corpus.manifest_original_title': 'Titre original',
 'pdf_corpus.manifest_output': 'Sortie du manifeste',
 'pdf_corpus.manifest_place': 'Lieu de publication',
 'pdf_corpus.manifest_publisher': 'Éditeur',
 'pdf_corpus.manifest_review_required': 'Réviser la structure du document',
 'pdf_corpus.manifest_review_required_help': 'Confirmez les métadonnées au niveau de l’œuvre et la correspondance des '
                                             'pages imprimées avant leur propagation dans la segmentation et les '
                                             'notices générées.',
 'pdf_corpus.manifest_saved': 'Manifeste du document enregistré. Les métadonnées héritées et les citations ont été '
                              'régénérées pour révision.',
 'pdf_corpus.manifest_short_title': 'Titre abrégé',
 'pdf_corpus.manifest_title': 'Titre',
 'pdf_corpus.manifest_translation': 'Statut de traduction',
 'pdf_corpus.manifest_translator': 'Traducteur ou traductrice',
 'pdf_corpus.manifest_type': 'Type de document',
 'pdf_corpus.manifest_unknown': 'Inconnu',
 'pdf_corpus.manifest_year': 'Année de publication',
 'pdf_corpus.manual_provider': 'Paramètres manuels de compatibilité fournisseur',
 'pdf_corpus.manual_provider_help': 'Utilisés uniquement lorsqu’aucun profil fournisseur n’est sélectionné. Les '
                                    'profils enregistrés sont recommandés, car DerridAI réutilise leurs paramètres de '
                                    'modèle et n’écrit jamais les clés API dans les manifestes de construction.',
 'pdf_corpus.matches': 'correspondances',
 'pdf_corpus.max_concurrent': 'Notices simultanées maximales',
 'pdf_corpus.max_concurrent_help': 'Les familles de métadonnées restent séquentielles pour chaque notice; ce réglage '
                                   'limite le nombre de notices traitées en parallèle.',
 'pdf_corpus.merge_next': 'Fusionner avec la suivante',
 'pdf_corpus.merge_previous': 'Fusionner avec la précédente',
 'pdf_corpus.merged': 'Fusion avec la fiche {direction}; la limite fusionnée doit maintenant être révisée.',
 'pdf_corpus.metadata_attention': 'Métadonnées à vérifier',
 'pdf_corpus.metadata_blocking_help': 'La révision des fiches est terminée, mais {count} fiche(s) contiennent encore '
                                      'des métadonnées critiques à résoudre.',
 'pdf_corpus.metadata_calls': 'enrichissement des notices',
 'pdf_corpus.metadata_decision_required': 'Décision de métadonnées requise',
 'pdf_corpus.metadata_decisions_count': '{count} décision(s) de métadonnées',
 'pdf_corpus.metadata_enrichment': 'Enrichissement des métadonnées',
 'pdf_corpus.metadata_family.all': 'Toutes les familles de métadonnées',
 'pdf_corpus.metadata_family.discourse': 'Discours / attribution',
 'pdf_corpus.metadata_family.indexing': 'Indexation sémantique',
 'pdf_corpus.metadata_family.quotation': 'Relations de citation',
 'pdf_corpus.metadata_family_rerun': 'Métadonnées {family} relancées à partir du texte révisé actuel de la fiche.',
 'pdf_corpus.metadata_field_confirmed': '{field} confirmé. L’état de préparation à la publication a été recalculé.',
 'pdf_corpus.metadata_field_status.deterministic': 'Déterministe',
 'pdf_corpus.metadata_field_status.human_confirmed': 'Confirmé par une personne',
 'pdf_corpus.metadata_field_status.human_override': 'Remplacement humain',
 'pdf_corpus.metadata_field_status.inherited': 'Hérité',
 'pdf_corpus.metadata_field_status.invalid': 'Invalide',
 'pdf_corpus.metadata_field_status.llm_inferred': 'Inféré par LLM',
 'pdf_corpus.metadata_field_status.unresolved': 'Non résolu',
 'pdf_corpus.metadata_help': 'Seules les métadonnées appartenant au modèle ou à l’humain sont modifiables ici. Le '
                             'texte, les pages, les segments source et les identifiants de fiche sont protégés côté '
                             'serveur.',
 'pdf_corpus.metadata_inline_help': 'Les métadonnées sont révisées avec la fiche. Seuls les champs incertains exigent '
                                    'une décision explicite.',
 'pdf_corpus.metadata_inline_help_v46': 'Les métadonnées de la fiche sont toujours inspectables. Les métadonnées '
                                        'documentaires héritées peuvent être délibérément remplacées pour cette fiche; '
                                        'les décisions humaines priment sur tout enrichissement automatique ultérieur.',
 'pdf_corpus.metadata_invalid': 'Les métadonnées doivent être un objet JSON valide.',
 'pdf_corpus.metadata_issue_help': 'Seuls les champs critiques pour la publication qui ne sont pas résolus sont '
                                   'relancés. Les métadonnées terminées sont conservées.',
 'pdf_corpus.metadata_issue_queue': 'File des problèmes de métadonnées',
 'pdf_corpus.metadata_issue_table': 'Détails des problèmes de métadonnées',
 'pdf_corpus.metadata_live_summary': '{complete} terminées · {running} actives · {queued} en attente · {failed} à '
                                     'réviser',
 'pdf_corpus.metadata_live_title': 'Les métadonnées automatiques sont en cours',
 'pdf_corpus.metadata_needs_attention': 'Métadonnées à vérifier',
 'pdf_corpus.metadata_ready': 'Prête',
 'pdf_corpus.metadata_reason.ambiguous': 'Les preuves de la source sont ambiguës',
 'pdf_corpus.metadata_reason.evidence_failed': 'Échec de la validation des preuves',
 'pdf_corpus.metadata_reason.invalid_value': 'Le modèle a retourné une valeur invalide',
 'pdf_corpus.metadata_reason.llm_failed': 'Échec de la requête au LLM',
 'pdf_corpus.metadata_reason.not_run': 'L’enrichissement n’est pas terminé',
 'pdf_corpus.metadata_reason.source_quality': 'La qualité de l’extraction bloque l’inférence',
 'pdf_corpus.metadata_reason.unresolved': 'Aucune valeur validée n’est disponible',
 'pdf_corpus.metadata_record_help': 'Ne résolvez que les champs requis affichés ci-dessous. L’acceptation structurelle '
                                    'de cette fiche est suivie séparément.',
 'pdf_corpus.metadata_record_resolved': 'Tous les champs de métadonnées requis de cette fiche sont résolus.',
 'pdf_corpus.metadata_record_review_help': 'Révisez les métadonnées proposées par le LLM avec le texte. Les champs '
                                           'incertains doivent être résolus avant l’acceptation; accepter la fiche '
                                           'confirme les autres propositions.',
 'pdf_corpus.metadata_remaining': 'métadonnées restantes',
 'pdf_corpus.metadata_rerun': 'Métadonnées interprétatives relancées. Le texte source primaire est resté inchangé.',
 'pdf_corpus.metadata_resolution': 'Résolution des métadonnées',
 'pdf_corpus.metadata_resolution_intro': 'La construction du corpus et la révision des fiches peuvent être terminées '
                                         'alors que des métadonnées savantes requises demeurent non résolues. '
                                         '{records} fiche(s) contiennent {fields} problème(s) de champ requis.',
 'pdf_corpus.metadata_resolved_ready': 'Métadonnées confirmées. Cette fiche est prête à être approuvée.',
 'pdf_corpus.metadata_retry_complete': 'Relance des métadonnées terminée',
 'pdf_corpus.metadata_retry_failed': 'Échec de la relance des métadonnées',
 'pdf_corpus.metadata_retry_failed_help': 'La relance s’est arrêtée sans modifier les métadonnées réussies. Révisez la '
                                          'file restante ou corrigez le fournisseur avant de réessayer.',
 'pdf_corpus.metadata_retry_progress': '{processed} fiche(s) sur {total} traitée(s) · {resolved} champs résolus',
 'pdf_corpus.metadata_retry_result': '{resolved} champs résolus · {remaining} champs nécessitent encore une '
                                     'vérification',
 'pdf_corpus.metadata_retry_running': 'Relance des métadonnées résolubles automatiquement',
 'pdf_corpus.metadata_retry_start': 'Relance des métadonnées pour {count} fiche(s). Les métadonnées terminées ne '
                                    'seront pas recalculées.',
 'pdf_corpus.metadata_retry_start_fields': 'Relance de {fields} champ(s) non résolu(s) dans {records} fiche(s). La '
                                           'topologie et les métadonnées terminées sont conservées.',
 'pdf_corpus.metadata_saved': 'Métadonnées enregistrées. Le texte lié à la source et la provenance n’ont pas été '
                              'modifiés.',
 'pdf_corpus.metadata_stalled_title': 'La progression des métadonnées semble bloquée',
 'pdf_corpus.metadata_tab': 'Métadonnées',
 'pdf_corpus.metadata_task.discourse': 'Discours',
 'pdf_corpus.metadata_task.indexing': 'Indexation',
 'pdf_corpus.metadata_task.quotation': 'Citation',
 'pdf_corpus.metadata_task_progress': 'Progression des tâches de métadonnées',
 'pdf_corpus.metadata_validation': 'Validation des métadonnées',
 'pdf_corpus.method': 'Méthode',
 'pdf_corpus.min_p': 'Min P',
 'pdf_corpus.mirostat': 'Mirostat',
 'pdf_corpus.mirostat_eta': 'Eta de Mirostat',
 'pdf_corpus.mirostat_off': 'Désactivé',
 'pdf_corpus.mirostat_tau': 'Tau de Mirostat',
 'pdf_corpus.model': 'Modèle',
 'pdf_corpus.model_not_set': 'modèle non défini',
 'pdf_corpus.need_attention': 'à vérifier',
 'pdf_corpus.need_review': 'à réviser',
 'pdf_corpus.needs_attention': 'À vérifier',
 'pdf_corpus.needs_review': 'À réviser',
 'pdf_corpus.next': 'suivante',
 'pdf_corpus.next_action.download_publication': 'Téléchargez l’instantané publié ou modifiez le brouillon pour créer '
                                                'une nouvelle révision.',
 'pdf_corpus.next_action.inspect': 'Examinez l’état restant du corpus.',
 'pdf_corpus.next_action.publish': 'Publiez l’instantané validé du corpus.',
 'pdf_corpus.next_action.resolve_metadata': 'Résolvez les problèmes de métadonnées requises.',
 'pdf_corpus.next_action.resolve_rejections': 'Résolvez les fiches rejetées.',
 'pdf_corpus.next_action.resolve_validation': 'Résolvez les obstacles de validation ou de qualité de la source.',
 'pdf_corpus.next_action.review_records': 'Révisez les fiches proposées restantes.',
 'pdf_corpus.next_action.wait': 'L’opération en cours est en traitement.',
 'pdf_corpus.next_finish_metadata': 'Terminez ou relancez les métadonnées incomplètes avant la publication.',
 'pdf_corpus.next_publish': 'Les contrôles de qualité sont réussis. Vérifiez le résumé de publication et publiez le '
                            'JSONL.',
 'pdf_corpus.next_published': 'Cette révision est publiée. Téléchargez-la ou modifiez le brouillon pour créer une '
                              'nouvelle révision.',
 'pdf_corpus.next_resolve_rejections': 'Résolvez ou rouvrez les fiches rejetées avant la publication.',
 'pdf_corpus.next_review_records': 'Révisez les fiches proposées restantes.',
 'pdf_corpus.next_stage': 'Prochaine étape',
 'pdf_corpus.next_step': 'Étape suivante',
 'pdf_corpus.next_wait_build': 'La construction du corpus est en cours.',
 'pdf_corpus.no_active_builds': 'Aucune autre construction de corpus n’est active.',
 'pdf_corpus.no_automatic_metadata_work': 'Aucun champ relançable automatiquement ne reste.',
 'pdf_corpus.no_bound_blocks': 'Aucun bloc source lié',
 'pdf_corpus.no_builds': 'Aucune construction pour le moment.',
 'pdf_corpus.no_clean_records': 'Aucune fiche sans problème n’attend l’approbation.',
 'pdf_corpus.no_escalation_provider': 'Aucun — conserver les échecs pour révision humaine',
 'pdf_corpus.no_evidence': 'Aucune preuve par champ enregistrée.',
 'pdf_corpus.no_evidence_reason': 'Aucune justification de preuve n’est enregistrée.',
 'pdf_corpus.no_field_evidence': 'Aucune preuve au niveau du champ n’est enregistrée pour cette proposition.',
 'pdf_corpus.no_human_metadata_work': 'Aucun champ de métadonnées n’exige un jugement humain.',
 'pdf_corpus.no_provider_profiles': 'Aucun profil fournisseur LLM n’est configuré',
 'pdf_corpus.no_provider_profiles_help': 'Créez un profil fournisseur ou utilisez les paramètres de compatibilité '
                                         'manuels ci-dessous.',
 'pdf_corpus.no_records_filter': 'Aucune fiche ne correspond à ce filtre de révision.',
 'pdf_corpus.no_retryable_metadata': 'Aucune métadonnée relançable automatiquement ne reste. Ouvrez la file des '
                                     'problèmes pour une résolution humaine.',
 'pdf_corpus.no_selected_build': 'Aucune construction de corpus sélectionnée',
 'pdf_corpus.no_selected_build_help': 'Persistez une source PDF et lancez une construction sémantique, ou choisissez '
                                      'une construction historique dans le rail.',
 'pdf_corpus.no_source_bound': 'aucun bloc source lié',
 'pdf_corpus.not_identified': 'Non identifié',
 'pdf_corpus.not_persisted': 'Non persistée dans le manifeste de construction',
 'pdf_corpus.not_yet': 'pas encore',
 'pdf_corpus.ocr_pages': 'page(s) OCR',
 'pdf_corpus.open_build': 'Ouvrir la construction du corpus',
 'pdf_corpus.open_builder': 'Ouvrir le générateur de corpus',
 'pdf_corpus.open_metadata_queue': 'Ouvrir la file des métadonnées',
 'pdf_corpus.open_pdf_explorer': 'Ouvrir dans l’explorateur PDF',
 'pdf_corpus.open_pdf_first': 'Ouvrez d’abord un PDF dans l’Explorateur, ou choisissez un PDF source ici.',
 'pdf_corpus.openai_compatible': 'Compatible OpenAI',
 'pdf_corpus.operation_label': 'Construction de corpus PDF',
 'pdf_corpus.ownership.attention': 'À réviser',
 'pdf_corpus.ownership.deterministic': 'Dérivé de la source',
 'pdf_corpus.ownership.human': 'Confirmé par l’humain',
 'pdf_corpus.ownership.inherited': 'Hérité',
 'pdf_corpus.ownership.llm': 'Inféré par LLM',
 'pdf_corpus.ownership.override': 'Remplacement',
 'pdf_corpus.ownership.unknown': 'Non classé',
 'pdf_corpus.ownership_help.attention': 'Ce champ exige une décision humaine.',
 'pdf_corpus.ownership_help.deterministic': 'Dérivé de la structure de la source ou de règles déterministes.',
 'pdf_corpus.ownership_help.human': 'Une personne a confirmé cette valeur au niveau de la fiche.',
 'pdf_corpus.ownership_help.inherited': 'Hérité du manifeste du document; cette valeur peut être remplacée pour cette '
                                        'fiche.',
 'pdf_corpus.ownership_help.llm': 'Proposé par le modèle de langage et conservé avec sa provenance.',
 'pdf_corpus.ownership_help.override': 'Cette fiche remplace délibérément une métadonnée documentaire héritée.',
 'pdf_corpus.ownership_help.unknown': 'Aucune provenance de propriété n’a été enregistrée.',
 'pdf_corpus.page_label_issues': 'problème(s) de pagination imprimée',
 'pdf_corpus.page_mapping': 'Correspondance des pages imprimées',
 'pdf_corpus.page_mapping_help': 'Les pages PDF physiques ne changent jamais. Corrigez uniquement l’étiquette de page '
                                 'imprimée savante lorsque l’étiquette PDF ou le folio détecté est erroné.',
 'pdf_corpus.page_mapping_issues': 'problème(s) de correspondance des pages',
 'pdf_corpus.page_mapping_saved': 'Corrections des pages imprimées enregistrées. Les nouvelles constructions de corpus '
                                  'utiliseront les étiquettes corrigées.',
 'pdf_corpus.pages': 'p.',
 'pdf_corpus.passed': 'Réussi',
 'pdf_corpus.pdf_highlight_help': 'Page {page}. Les cadres en surbrillance indiquent les blocs source liés au champ de '
                                  'preuve sélectionné.',
 'pdf_corpus.pdf_loading': 'Rendu de la page source…',
 'pdf_corpus.pdf_page_canvas': 'Page PDF {page}',
 'pdf_corpus.pdf_page_of': 'Page PDF {page} sur {total}',
 'pdf_corpus.pdf_pages': 'Pages PDF',
 'pdf_corpus.pdf_render_error': 'Impossible d’afficher la page source : {error}',
 'pdf_corpus.pending': 'En attente',
 'pdf_corpus.persisted': 'persisté',
 'pdf_corpus.physical_pdf_page': 'Page PDF physique',
 'pdf_corpus.pipeline.construct': 'Construire les fiches',
 'pdf_corpus.pipeline.construct_wait': 'En attente de la topologie du corpus',
 'pdf_corpus.pipeline.enrich': 'Enrichir les métadonnées',
 'pdf_corpus.pipeline.enrich_wait': 'En attente des fiches',
 'pdf_corpus.pipeline.extract': 'Extraire la source',
 'pdf_corpus.pipeline.extract_detail': 'Texte PDF et géométrie des pages disponibles',
 'pdf_corpus.pipeline.extract_detail_count': '{count} blocs sources disponibles',
 'pdf_corpus.pipeline.metadata_complete': 'Métadonnées requises résolues',
 'pdf_corpus.pipeline.metadata_progress': '{done} sur {total} aux métadonnées complètes',
 'pdf_corpus.pipeline.metadata_remaining': '{count} fiche(s) ont encore besoin de métadonnées requises',
 'pdf_corpus.pipeline.publish': 'Publier l’instantané',
 'pdf_corpus.pipeline.publish_wait': 'En attente des contrôles de validation',
 'pdf_corpus.pipeline.published': 'Instantané JSONL immuable publié',
 'pdf_corpus.pipeline.ready_publish': 'Prêt pour une publication explicite',
 'pdf_corpus.pipeline.records_created': '{count} fiches créées',
 'pdf_corpus.pipeline.review': 'Valider les fiches',
 'pdf_corpus.pipeline.review_progress': '{done} sur {total} révisées',
 'pdf_corpus.pipeline.review_wait': 'En attente des fiches',
 'pdf_corpus.pipeline.validate': 'Valider le corpus',
 'pdf_corpus.pipeline.validation_passed': 'Contrôles de source, métadonnées et schéma réussis',
 'pdf_corpus.pipeline.validation_wait': 'La validation comporte des obstacles non résolus',
 'pdf_corpus.pipeline_title': 'Pipeline du corpus',
 'pdf_corpus.previous': 'précédente',
 'pdf_corpus.primary_text_help': 'Indiquez si cette fiche appartient au texte substantiel de l’œuvre plutôt qu’aux '
                                 'pages liminaires/finales ou à l’appareil éditorial.',
 'pdf_corpus.printed_label': 'Étiquette imprimée',
 'pdf_corpus.printed_label_for_page': 'Étiquette imprimée de la page PDF physique {page}',
 'pdf_corpus.printed_pages': 'imprimé',
 'pdf_corpus.profile_active_builds': '{count} active(s) sur ce profil',
 'pdf_corpus.profile_model': 'Modèle du profil',
 'pdf_corpus.profile_model_help': 'Les nouvelles constructions utilisent par défaut le modèle de ce profil '
                                  'fournisseur.',
 'pdf_corpus.progress_percent': '{percent} % terminé',
 'pdf_corpus.proposed_record': 'Fiche proposée',
 'pdf_corpus.provenance': 'Provenance',
 'pdf_corpus.provider': 'Fournisseur',
 'pdf_corpus.provider_default': 'Valeur par défaut du fournisseur',
 'pdf_corpus.provider_profile': 'Profil fournisseur',
 'pdf_corpus.provider_profile_help': 'Utilisez un profil de fournisseur géré centralement. Son modèle et ses '
                                     'paramètres de génération demeurent réutilisables dans les flux DerridAI.',
 'pdf_corpus.provisional_splits': 'Scissions de sécurité',
 'pdf_corpus.publication': 'Publication',
 'pdf_corpus.publication_ready_help': 'Tous les contrôles requis sont réussis. La publication crée un instantané JSONL '
                                      'UTF-8 immuable.',
 'pdf_corpus.publication_snapshot_summary': 'Révision publiée avec {count} fiche(s).',
 'pdf_corpus.publication_waiting_help': 'La publication sera activée automatiquement après la résolution des obstacles '
                                        'de cette vue Terminer le corpus.',
 'pdf_corpus.publish_corpus': 'Publier le corpus',
 'pdf_corpus.publish_jsonl': 'Publier le JSONL',
 'pdf_corpus.published': '{count} fiches publiées · SHA-256 {hash}…',
 'pdf_corpus.published_completion_help': 'L’instantané JSONL immuable est prêt à être téléchargé. La modification du '
                                         'brouillon créera une nouvelle révision non publiée.',
 'pdf_corpus.published_revision': 'Révision publiée',
 'pdf_corpus.quality.accounted': 'de la source comptabilisée',
 'pdf_corpus.quality.attention': 'Attention requise',
 'pdf_corpus.quality.boundaries': 'limites validées',
 'pdf_corpus.quality.help': 'Les contrôles de qualité résument la topologie sémantique, l’achèvement des métadonnées '
                            'et la fidélité à la source avant la publication.',
 'pdf_corpus.quality.median_chars': 'caractères médians',
 'pdf_corpus.quality.metadata': 'Métadonnées',
 'pdf_corpus.quality.need_review': '{count} à réviser',
 'pdf_corpus.quality.passed': 'Validation réussie',
 'pdf_corpus.quality.pending': 'En attente',
 'pdf_corpus.quality.record_size': 'Taille des notices',
 'pdf_corpus.quality.records_complete': 'notices terminées',
 'pdf_corpus.quality.resolved': 'Résolue',
 'pdf_corpus.quality.segmentation': 'Segmentation',
 'pdf_corpus.quality.size_detail': 'P10 {p10} · médiane {median} · P90 {p90} · max. {max} · {over} au-dessus de la '
                                   'plage préférée · {long} exception(s) longue(s)',
 'pdf_corpus.quality.source': 'Fidélité à la source',
 'pdf_corpus.quality.target_range': 'cible {range} · P90 {p90}',
 'pdf_corpus.quality.title': 'Qualité de la construction',
 'pdf_corpus.quality.unresolved': '{count} non résolue(s)',
 'pdf_corpus.queue_accepted': 'Acceptées',
 'pdf_corpus.queue_all': 'Toutes',
 'pdf_corpus.queue_attention': 'Attention topologique',
 'pdf_corpus.queue_issues': 'À vérifier',
 'pdf_corpus.queue_metadata': 'Décisions de métadonnées',
 'pdf_corpus.queue_pending': 'Révision en attente',
 'pdf_corpus.queue_ready': 'Révisables',
 'pdf_corpus.queue_rejected': 'Rejetées',
 'pdf_corpus.queue_source': 'Problème de source',
 'pdf_corpus.queue_topology': 'Topologie',
 'pdf_corpus.quotation_output': 'Sortie des métadonnées de citation',
 'pdf_corpus.read_record': 'Lire la fiche',
 'pdf_corpus.readiness_blocker.boundary_attention': 'Des décisions de frontière exigent encore une révision',
 'pdf_corpus.readiness_blocker.metadata_validation': 'Échec de la validation des métadonnées',
 'pdf_corpus.readiness_blocker.record_attention': 'Des fiches exigent encore une vérification structurelle',
 'pdf_corpus.readiness_blocker.rejected_records': 'Les fiches rejetées doivent être résolues',
 'pdf_corpus.readiness_blocker.required_metadata': 'Des métadonnées requises ne sont pas résolues',
 'pdf_corpus.readiness_blocker.review_pending': 'La révision des fiches est incomplète',
 'pdf_corpus.readiness_blocker.source_quality': 'La qualité de l’extraction bloque l’enrichissement',
 'pdf_corpus.readiness_blocker.source_validation': 'Échec de la validation de fidélité à la source',
 'pdf_corpus.ready': 'Prêt',
 'pdf_corpus.ready_acceptance': 'Prête à être acceptée',
 'pdf_corpus.ready_completion_help': 'La révision, la validation de la source et les contrôles des métadonnées '
                                     'requises sont réussis.',
 'pdf_corpus.ready_to_build': 'Prêt à construire',
 'pdf_corpus.ready_to_publish': 'Prêt à publier',
 'pdf_corpus.reason': 'Raison',
 'pdf_corpus.reconciliation_output': 'Sortie de réconciliation',
 'pdf_corpus.record': 'Fiche',
 'pdf_corpus.record_data': 'Données et preuves de la fiche',
 'pdf_corpus.record_decision': 'Décision sur la fiche',
 'pdf_corpus.record_inspector': 'Inspecteur de fiche',
 'pdf_corpus.record_metadata_review': 'Révision des métadonnées de la fiche',
 'pdf_corpus.record_review': 'Révision des fiches',
 'pdf_corpus.record_revision': 'Révision de la fiche',
 'pdf_corpus.record_sizing.absolute': 'Plafond absolu de sécurité',
 'pdf_corpus.record_sizing.absolute_help': 'Plafond de sécurité seulement. Le générateur peut demander une révision si '
                                           'son respect exige de rompre une transition protégée d’attribution ou de '
                                           'syntaxe.',
 'pdf_corpus.record_sizing.advanced': 'Limites avancées pour les exceptions',
 'pdf_corpus.record_sizing.help': 'La longueur guide une topologie adaptée à la recherche sans jamais primer sur '
                                  'l’attribution ni l’intégrité sémantique. Le générateur vise la plage préférée et '
                                  'permet des exceptions cohérentes plus longues au besoin.',
 'pdf_corpus.record_sizing.long': 'Exception pour notice longue',
 'pdf_corpus.record_sizing.long_help': 'Une pensée cohérente peut atteindre cette longueur lorsqu’aucune bonne limite '
                                       'n’existe près de la plage préférée.',
 'pdf_corpus.record_sizing.preferred': 'Longueur préférée d’une notice',
 'pdf_corpus.record_sizing.preferred_range': 'Plage cible : environ {low} à {high} caractères.',
 'pdf_corpus.record_sizing.title': 'Taille des notices',
 'pdf_corpus.record_sizing.tolerance': 'Souplesse préférée',
 'pdf_corpus.record_sizing.tolerance_help': 'Permet une limite sémantique nette légèrement avant ou après la cible.',
 'pdf_corpus.record_state.accepted': 'Acceptée',
 'pdf_corpus.record_state.metadata': 'Métadonnées',
 'pdf_corpus.record_state.preparing': 'Préparation',
 'pdf_corpus.record_state.ready': 'Révisable',
 'pdf_corpus.record_state.rejected': 'Rejetée',
 'pdf_corpus.record_state.source': 'Problème de source',
 'pdf_corpus.record_state.topology': 'Topologie',
 'pdf_corpus.records': 'fiches',
 'pdf_corpus.records_incomplete': 'fiches incomplètes',
 'pdf_corpus.records_metadata_complete': 'fiches aux métadonnées complètes',
 'pdf_corpus.refresh_builds': 'Actualiser les constructions',
 'pdf_corpus.reject': 'Rejeter',
 'pdf_corpus.reject_all': 'Tout rejeter',
 'pdf_corpus.reject_all_queue': 'Rejeter la file',
 'pdf_corpus.reject_next': 'Rejeter et suivante',
 'pdf_corpus.reject_queue': 'Rejeter les fiches problématiques visibles',
 'pdf_corpus.reject_selected': 'Rejeter la sélection',
 'pdf_corpus.reject_selected_count': 'Rejeter la sélection ({count})',
 'pdf_corpus.rejected': 'Rejeté',
 'pdf_corpus.rejected_notice': 'Fiche rejetée. Passage à la fiche suivante.',
 'pdf_corpus.rejections_blocking_help': '{count} fiche(s) rejetée(s) doivent être corrigées, supprimées ou rouvertes '
                                        'avant la publication.',
 'pdf_corpus.remaining': 'restantes',
 'pdf_corpus.remove_evidence': 'Retirer comme preuve',
 'pdf_corpus.reopen': 'Rouvrir',
 'pdf_corpus.reopened_notice': 'Fiche rouverte pour révision.',
 'pdf_corpus.repeat_penalty': 'Pénalité de répétition',
 'pdf_corpus.required_metadata': 'Métadonnées requises',
 'pdf_corpus.rerun_family': 'Relancer',
 'pdf_corpus.rerun_metadata': 'Relancer les métadonnées',
 'pdf_corpus.resolve_metadata_before_accept': 'Résolvez les champs de métadonnées signalés avant d’accepter cette '
                                              'fiche.',
 'pdf_corpus.resolve_metadata_before_accept_fields': 'Confirmez {fields} avant d’accepter cette fiche.',
 'pdf_corpus.resolve_metadata_issues': 'Résoudre les problèmes de métadonnées',
 'pdf_corpus.resolve_metadata_to_accept': 'Résoudre les métadonnées pour accepter',
 'pdf_corpus.resolve_rejections_title': 'Résoudre les fiches rejetées',
 'pdf_corpus.resolve_source_before_accept': 'Résolvez le problème d’extraction de la source ou rejetez cette fiche '
                                            'avant de l’accepter.',
 'pdf_corpus.resolve_source_with_correction': 'Marquer le problème source de cette fiche comme résolu par la '
                                              'correction révisée',
 'pdf_corpus.resume': 'Reprendre au dernier point de contrôle',
 'pdf_corpus.resume_safe': 'Reprise sécurisée',
 'pdf_corpus.retry_automatically': 'Relancer automatiquement',
 'pdf_corpus.retry_fields_with_model': 'Relancer {count} champ(s) avec {model}',
 'pdf_corpus.retry_in_progress': 'Nouvelle tentative de segmentation non résolue',
 'pdf_corpus.retry_in_progress_help': 'DerridAI a repris au dernier point de contrôle sûr. L’action de nouvelle '
                                      'tentative est verrouillée pendant l’exécution; suivez l’étape et la progression '
                                      'ici ou à l’Accueil.',
 'pdf_corpus.retry_incomplete_metadata': 'Relancer les métadonnées incomplètes',
 'pdf_corpus.retry_metadata_count': 'Relancer {count} fiche(s)',
 'pdf_corpus.retry_metadata_failures': 'Réessayer les métadonnées incomplètes',
 'pdf_corpus.retry_metadata_fields': 'Relancer {count} champ(s)',
 'pdf_corpus.retry_segmentation': 'Réessayer la segmentation non résolue',
 'pdf_corpus.retryable_metadata_fields': '{count} champ(s) peuvent être relancés',
 'pdf_corpus.retryable_metadata_help': 'Ces problèmes proviennent d’une réponse de modèle échouée ou invalide, ou d’un '
                                       'seuil de preuve. La relance ne touche que les fiches non résolues; les '
                                       'métadonnées terminées et la topologie sont conservées.',
 'pdf_corpus.retrying_metadata': 'Relance des métadonnées…',
 'pdf_corpus.review_ambiguous_metadata': 'Réviser les métadonnées ambiguës',
 'pdf_corpus.review_complete': 'Révision des fiches terminée',
 'pdf_corpus.review_controls': 'Commandes de révision des fiches',
 'pdf_corpus.review_detail_views': 'Vues détaillées de révision',
 'pdf_corpus.review_details': 'Détails de la révision',
 'pdf_corpus.review_manually': 'Réviser manuellement',
 'pdf_corpus.review_metadata_issues': 'Réviser les problèmes de métadonnées',
 'pdf_corpus.review_metadata_records': 'Réviser {count} fiche(s) touchée(s)',
 'pdf_corpus.review_mode': 'Révision des fiches',
 'pdf_corpus.review_mode_help': 'Révisez la fiche proposée et ses métadonnées ensemble. Les diagnostics de '
                                'construction restent accessibles sous Détails techniques de la construction.',
 'pdf_corpus.review_only': 'À réviser seulement',
 'pdf_corpus.review_preparing_help': 'L’enrichissement des métadonnées est toujours en cours. Chaque fiche devient '
                                     'révisable dès que son propre enrichissement est terminé; vous pouvez donc '
                                     'commencer sans attendre la fin du livre entier.',
 'pdf_corpus.review_preparing_progress': '{done} fiche(s) sur {total} ont terminé l’enrichissement des métadonnées. '
                                         'Les fiches terminées peuvent être révisées immédiatement.',
 'pdf_corpus.review_preparing_title': 'Enrichissement des métadonnées des fiches',
 'pdf_corpus.review_progress_compact': '{accepted} acceptées · {pending} en attente · {metadata} décisions de '
                                       'métadonnées',
 'pdf_corpus.review_queue': 'File de révision',
 'pdf_corpus.review_rejected_records': 'Réviser les fiches rejetées',
 'pdf_corpus.review_selected_preparing': 'La fiche sélectionnée est encore en cours d’enrichissement. Choisissez une '
                                         'fiche terminée pour commencer la révision pendant que les autres continuent '
                                         'en arrière-plan.',
 'pdf_corpus.review_selected_preparing_title': 'La fiche sélectionnée est encore en traitement',
 'pdf_corpus.review_validation_issues': 'Réviser les problèmes de validation',
 'pdf_corpus.reviewed': 'Révisées',
 'pdf_corpus.reviewed_record_text': 'Texte révisé de la fiche',
 'pdf_corpus.revision': 'révision',
 'pdf_corpus.save_field_value': 'Enregistrer la valeur',
 'pdf_corpus.save_manifest': 'Enregistrer le manifeste du document',
 'pdf_corpus.save_metadata': 'Enregistrer les métadonnées',
 'pdf_corpus.save_page_overrides': 'Enregistrer {count} correction(s)',
 'pdf_corpus.save_reviewed_text': 'Enregistrer le texte révisé',
 'pdf_corpus.saved_checkpoint': 'point de reprise enregistré',
 'pdf_corpus.saving_decision': 'Enregistrement de la décision…',
 'pdf_corpus.schema_issues': 'problème(s) de schéma de métadonnées',
 'pdf_corpus.search_records': 'Rechercher dans les fiches générées',
 'pdf_corpus.seconds': 'secondes',
 'pdf_corpus.seed': 'Graine',
 'pdf_corpus.segmentation_blocked': 'Segmentation bloquée',
 'pdf_corpus.segmentation_blocked_help': 'DerridAI n’a pas pu valider toutes les transitions sémantiques requises; la '
                                         'construction s’est donc arrêtée avant de créer des notices. Aucune notice '
                                         'géante de repli n’a été fabriquée. Ajustez le fournisseur ou les paramètres, '
                                         'puis réessayez les régions non résolues.',
 'pdf_corpus.segmentation_calls': 'segmentation',
 'pdf_corpus.segmentation_output': 'Sortie de segmentation',
 'pdf_corpus.segmentation_review_help': 'Le corpus a été construit malgré un petit nombre de transitions incertaines. '
                                        'Seuls les enregistrements concernés sont marqués À réviser. Inspectez-les '
                                        'ci-dessous et utilisez Scinder ou Fusionner pour corriger la topologie; il '
                                        'n’est pas nécessaire de répéter le même appel déterministe de segmentation.',
 'pdf_corpus.segmentation_review_title': 'Révision localisée de la segmentation',
 'pdf_corpus.segmentation_telemetry': 'Décisions de segmentation',
 'pdf_corpus.segmentation_telemetry_help': 'La plupart des transitions sont résolues de façon déterministe. Le LLM est '
                                           'limité à un petit sous-ensemble ambigu; l’incertitude, l’omission et les '
                                           'échecs du classificateur sont résolus prudemment par CONSERVER.',
 'pdf_corpus.segmentation_window': 'Fenêtre d’entrée de segmentation',
 'pdf_corpus.segmentation_window_help': 'Nombre approximatif de jetons d’entrée par fenêtre d’analyse sémantique; ce '
                                        'réglage ne sert jamais de règle de taille des notices.',
 'pdf_corpus.select_record': 'Sélectionnez une fiche générée pour examiner son lien à la source et ses métadonnées.',
 'pdf_corpus.select_record_id': 'Sélectionner {record}',
 'pdf_corpus.select_records_first': 'Sélectionnez d’abord une ou plusieurs fiches.',
 'pdf_corpus.select_visible': 'Sélectionner les éléments visibles',
 'pdf_corpus.semantic_indexing': 'Indexation sémantique',
 'pdf_corpus.semantic_indexing_help': 'Générer les thèmes, concepts, personnes et œuvres citées. Le mode approfondi '
                                      'inclut toujours l’indexation.',
 'pdf_corpus.settle_requested': 'Finalisation des tâches restantes…',
 'pdf_corpus.settle_requested_notice': 'Les tâches automatiques restantes deviendront des exceptions à réviser dès que '
                                       'toute requête active aura atteint son délai maximal.',
 'pdf_corpus.show_all_records': 'Afficher toutes les fiches',
 'pdf_corpus.show_review_records': 'Afficher les enregistrements concernés',
 'pdf_corpus.size_optimized_splits': 'Limites optimisées selon la taille',
 'pdf_corpus.skip': 'Passer',
 'pdf_corpus.source_asset': 'Source PDF persistée',
 'pdf_corpus.source_blocks': 'blocs sources',
 'pdf_corpus.source_context': 'Contexte source',
 'pdf_corpus.source_coverage': 'Couverture de la source',
 'pdf_corpus.source_fidelity': 'Fidélité à la source',
 'pdf_corpus.source_ingested': 'Source ingérée : {pages} pages · {blocks} blocs source · OCR sur {ocr} pages.',
 'pdf_corpus.source_issue.fragmented_glyph_layout': 'Mise en page du texte fragmentée',
 'pdf_corpus.source_issue.source_quality_blocking': 'Couche de texte PDF endommagée',
 'pdf_corpus.source_issue_default': 'La source extraite peut ne pas être assez fiable pour une interprétation savante '
                                    'automatique.',
 'pdf_corpus.source_issue_help': 'Inspectez la source concernée et décidez s’il faut corriger le texte de la fiche ou '
                                 'reconstruire/réextraire la source PDF.',
 'pdf_corpus.source_issue_resolved': 'Problème source résolu',
 'pdf_corpus.source_issue_resolved_help': 'La personne chargée de la révision a corrigé le texte du corpus; '
                                          'l’extraction originale reste conservée pour l’audit.',
 'pdf_corpus.source_issue_title': 'Problème d’extraction de la source',
 'pdf_corpus.source_loading_or_unavailable': 'Les blocs sources sont en cours de chargement ou indisponibles.',
 'pdf_corpus.source_order_issues': 'problème(s) d’ordre de la source',
 'pdf_corpus.source_page_navigation': 'Navigation dans les pages source',
 'pdf_corpus.source_pdf': 'PDF source',
 'pdf_corpus.source_pdf_for_record': 'PDF source de la fiche sélectionnée',
 'pdf_corpus.source_quality': 'Qualité de la source',
 'pdf_corpus.source_setup_help': 'Choisissez un PDF extrait ou ajoutez le PDF actuellement ouvert dans l’Explorateur.',
 'pdf_corpus.source_setup_title': 'PDF source',
 'pdf_corpus.source_severity.blocking': 'Bloquant',
 'pdf_corpus.source_severity.minor': 'Mineur',
 'pdf_corpus.source_severity.warning': 'Avertissement',
 'pdf_corpus.source_tab': 'Source',
 'pdf_corpus.split_after': 'Scinder après ce bloc',
 'pdf_corpus.split_done': 'Fiche scindée à la limite sémantique sélectionnée. Les deux fiches doivent être révisées.',
 'pdf_corpus.stage': 'Étape',
 'pdf_corpus.stage.cancelled': 'annulée',
 'pdf_corpus.stage.document_review': 'révision du document',
 'pdf_corpus.stage.enriching': 'enrichissement des métadonnées',
 'pdf_corpus.stage.failed': 'échec',
 'pdf_corpus.stage.interrupted': 'interrompue',
 'pdf_corpus.stage.metadata_review': 'révision des métadonnées',
 'pdf_corpus.stage.published': 'publiée',
 'pdf_corpus.stage.queued': 'en file',
 'pdf_corpus.stage.ready': 'prête',
 'pdf_corpus.stage.reconciling': 'réconciliation des limites',
 'pdf_corpus.stage.resuming': 'reprise',
 'pdf_corpus.stage.review': 'révision humaine',
 'pdf_corpus.stage.segmentation_review': 'révision de la segmentation',
 'pdf_corpus.stage.segmenting': 'segmentation sémantique',
 'pdf_corpus.stage.structure': 'structure du document',
 'pdf_corpus.stage_budgets': 'Budgets de sortie structurée',
 'pdf_corpus.stage_budgets_help': 'Des réponses plus petites et bornées sont plus fiables avec les modèles locaux. '
                                  'Augmentez un budget seulement si une sortie validée est tronquée.',
 'pdf_corpus.stage_help.published': 'Le corpus révisé a été finalisé au format JSONL. La provenance de construction '
                                    'est regroupée sous corpus_build_details dans chaque fiche publiée.',
 'pdf_corpus.stage_help.reconciling': 'Finalisation de la topologie. Les classifications faibles, omises, incertaines '
                                      'ou en échec sont résolues par CONSERVER. Une scission de sécurité n’exige une '
                                      'révision que si toutes les limites proches présentent un risque de provenance.',
 'pdf_corpus.stage_help.segmenting': 'Évaluation locale des transitions structurelles. Les limites protégées ou '
                                     'faibles sont résolues sans inférence; seul un sous-ensemble ambigu et borné est '
                                     'soumis au LLM.',
 'pdf_corpus.stage_timeouts': 'Délais maximaux par étape',
 'pdf_corpus.stage_timeouts_help': 'Durée maximale de lecture ou d’exécution d’une tentative LLM. Un dépassement '
                                   'devient une exception révisable au lieu de bloquer toute la construction.',
 'pdf_corpus.start_another_build': 'Lancer une autre construction',
 'pdf_corpus.starting': 'Démarrage…',
 'pdf_corpus.status.awaiting_manifest_review': 'en attente de révision du document',
 'pdf_corpus.status.awaiting_metadata': 'en attente de métadonnées',
 'pdf_corpus.status.awaiting_review': 'en attente de révision',
 'pdf_corpus.status.blocked': 'bloquée',
 'pdf_corpus.status.cancelled': 'annulée',
 'pdf_corpus.status.failed': 'échec',
 'pdf_corpus.status.interrupted': 'interrompue',
 'pdf_corpus.status.published': 'publiée',
 'pdf_corpus.status.published_snapshot': 'publié',
 'pdf_corpus.status.queued': 'en file',
 'pdf_corpus.status.ready': 'prête',
 'pdf_corpus.status.running': 'en cours',
 'pdf_corpus.status_refresh_failed': 'L’actualisation de l’état a échoué. La construction peut toujours être en cours; '
                                     'DerridAI réessaiera automatiquement.',
 'pdf_corpus.structured_failures': 'corrections de sortie structurée',
 'pdf_corpus.subtitle': 'Un LLM propose les limites sémantiques et les métadonnées interprétatives; le texte source, '
                        'la provenance des pages, les identifiants, la validation et la publication restent '
                        'déterministes.',
 'pdf_corpus.technical_details': 'Détails techniques de construction',
 'pdf_corpus.temperature': 'Température',
 'pdf_corpus.text_fidelity_issues': 'problème(s) de fidélité du texte',
 'pdf_corpus.text_saved': 'Texte révisé enregistré. Le texte extrait immuable reste disponible dans Source.',
 'pdf_corpus.text_saved_resolved': 'Texte révisé enregistré et problème source de la fiche marqué comme résolu. '
                                   'Relancez les métadonnées si la correction affecte l’interprétation.',
 'pdf_corpus.thinking': 'Raisonnement',
 'pdf_corpus.thinking_high': 'Élevé',
 'pdf_corpus.thinking_low': 'Faible',
 'pdf_corpus.thinking_medium': 'Moyen',
 'pdf_corpus.thinking_off': 'Désactivé',
 'pdf_corpus.thinking_on': 'Activé',
 'pdf_corpus.timeout.discourse': 'Discours',
 'pdf_corpus.timeout.indexing': 'Indexation',
 'pdf_corpus.timeout.manifest': 'Manifeste',
 'pdf_corpus.timeout.quotation': 'Citation',
 'pdf_corpus.timeout.reconciliation': 'Réconciliation',
 'pdf_corpus.timeout.segmentation': 'Segmentation',
 'pdf_corpus.title': 'Créer des fiches auditables à partir de PDF sources',
 'pdf_corpus.top_k': 'Top K',
 'pdf_corpus.top_p': 'Top P',
 'pdf_corpus.total': 'au total',
 'pdf_corpus.undo': 'Annuler',
 'pdf_corpus.undo_done': 'La dernière fusion ou division a été annulée.',
 'pdf_corpus.unknown': 'inconnue',
 'pdf_corpus.unresolved_count': '{count} région(s) non résolue(s)',
 'pdf_corpus.unresolved_fields': 'champs non résolus',
 'pdf_corpus.unresolved_regions': 'décision(s) de limite à réviser',
 'pdf_corpus.use_current_pdf': 'Utiliser le PDF actuel de l’Explorateur',
 'pdf_corpus.use_profile_defaults': 'Utiliser les paramètres de génération du profil de fournisseur',
 'pdf_corpus.validation_attention': 'Validation à examiner',
 'pdf_corpus.validation_details': 'Détails de validation',
 'pdf_corpus.validation_passed': 'Validation réussie',
 'pdf_corpus.view_evidence': 'Preuves',
 'pdf_corpus.view_metadata_issue_details': 'Voir {count} problème(s) de métadonnées',
 'pdf_corpus.view_publication_blockers': 'Voir {count} obstacle(s) à la publication',
 'pdf_corpus.view_source_evidence': 'Voir les preuves de la source',
 'pdf_corpus.waiting': 'En attente',
 'pdf_corpus.warnings_count': '{count} avertissement(s) de construction',
 'pdf_corpus.what_next': 'Quelle est la prochaine étape?',
 'pdf_corpus.why_review': 'Pourquoi réviser',
 'pdf_corpus.workflow': 'Flux de travail',
 'pdf_corpus.workflow.analyze': 'Analyser la structure',
 'pdf_corpus.workflow.build': 'Construire les fiches',
 'pdf_corpus.workflow.complete': 'Terminé',
 'pdf_corpus.workflow.current': 'Étape actuelle',
 'pdf_corpus.workflow.enrich': 'Construire et enrichir',
 'pdf_corpus.workflow.label': 'Flux de construction du corpus',
 'pdf_corpus.workflow.publish': 'Publier',
 'pdf_corpus.workflow.review': 'Révision collaborative',
 'pdf_corpus.workflow.source': 'Source',
 'pdf_corpus.workflow.upcoming': 'À venir',
 'pdf_workspace.builder': 'Générateur de corpus',
 'pdf_workspace.explorer': 'Explorateur PDF',
 'pdf_workspace.help': 'Construisez des jeux de notices vérifiables; la lecture de la source demeure disponible dans '
                       'l’Explorateur PDF',
 'pdf_workspace.modes': 'Modes du générateur de corpus',
 'permissions.annotations_denied': 'Votre rôle ne permet pas de créer des annotations.',
 'permissions.appearance_denied': 'Les paramètres d’apparence sont désactivés pour ce rôle.',
 'permissions.corpus_denied': 'Votre rôle ne permet pas de gérer les bases de données du corpus.',
 'permissions.corpus_manage_denied': 'Votre rôle ne permet pas de charger des fichiers de corpus.',
 'permissions.evidence_denied': 'Votre rôle ne permet pas de modifier les preuves sélectionnées.',
 'permissions.faq_denied': 'Votre rôle ne permet pas d’ouvrir la bibliothèque de réponses.',
 'permissions.no_workspace_shortcuts': 'Aucune autre page de l’espace de travail n’est activée pour ce rôle.',
 'permissions.pdf_denied': 'Votre rôle ne permet pas d’ouvrir l’Explorateur PDF.',
 'permissions.rag_denied': 'Votre rôle ne permet pas d’exécuter des pipelines de recherche.',
 'permissions.record_edit_denied': 'Votre rôle ne permet pas de modifier les fiches locales.',
 'permissions.research_result_denied': 'Votre rôle ne permet pas d’ouvrir les résultats de recherche.',
 'providers.context_tokens': 'jetons de contexte',
 'providers.ollama': 'Ollama',
 'providers.openai_compatible': 'Compatible avec OpenAI',
 'rag.selected_evidence': 'Preuves sélectionnées',
 'rag.skip_retrieval': 'Utiliser uniquement les preuves sélectionnées (sans repérage)',
 'rag.skip_retrieval_short': 'Preuves seulement',
 'record.add_evidence': 'Ajouter aux preuves',
 'record.add_evidence_help': 'Ajoutez cette fiche aux preuves sélectionnées utilisées par Recherche et les exécutions '
                             'RAG fondées uniquement sur les preuves.',
 'record.add_selection': 'Ajouter à la sélection',
 'record.add_term': 'Ajouter : {label}',
 'record.attribution_path': 'Parcours d’attribution',
 'record.audit_trail': 'Piste d’audit',
 'record.change_history': 'Historique des modifications',
 'record.characters': 'caractères',
 'record.citations': 'Références',
 'record.clean_ocr': 'Nettoyer les artéfacts de ROC',
 'record.clear_find': 'Effacer la recherche dans la fiche',
 'record.clear_find_empty': 'Saisissez une recherche avant de l’effacer.',
 'record.clear_search': 'Effacer la recherche',
 'record.collection': 'Collection',
 'record.comma_separated': 'Séparez les valeurs multiples par des virgules.',
 'record.copy_failed': 'Impossible de copier la référence',
 'record.copy_full': 'Copier la référence complète',
 'record.copy_inline': 'Copier la citation dans le texte',
 'record.copy_json': 'Copier la fiche en JSON',
 'record.database_record': 'Fiche de la base de données',
 'record.discourse_role': 'Rôle discursif',
 'record.edit': 'Modifier la fiche',
 'record.edit_kicker': 'Métadonnées de la fiche',
 'record.evidence_selected': 'Preuve sélectionnée',
 'record.exit_focus': 'Quitter le mode concentration',
 'record.extracted_text': 'Texte extrait',
 'record.extraction_quality': 'Qualité de l’extraction',
 'record.find_text': 'Rechercher dans le texte de la fiche',
 'record.focus_mode': 'Mode concentration',
 'record.full_citation': 'Référence complète',
 'record.full_citation_copied': 'Référence complète copiée',
 'record.group_citation': 'Référence',
 'record.group_discourse': 'Discours',
 'record.group_indexing': 'Indexation',
 'record.group_language': 'Langue et traduction',
 'record.group_other': 'Autres champs',
 'record.group_quality': 'Qualité et révision',
 'record.group_quotation': 'Provenance de la citation',
 'record.group_source': 'Source',
 'record.group_text': 'Texte',
 'record.hide_inspector': 'Masquer le volet d’inspection',
 'record.history_undo': 'Historique et annulation',
 'record.id': 'Fiche',
 'record.indexing': 'Indexation',
 'record.indexing_kicker': 'Index de recherche',
 'record.inline_citation': 'Citation dans le texte',
 'record.inline_citation_copied': 'Citation dans le texte copiée',
 'record.inspector': 'Volet d’inspection de la fiche',
 'record.inspector_sections': 'Sections du volet d’inspection de la fiche',
 'record.link_current_pdf': 'Lier la page PDF actuelle',
 'record.load_failed': 'Impossible de charger la fiche',
 'record.loading': 'Chargement de la fiche…',
 'record.matches': 'correspondances',
 'record.metadata': 'Métadonnées',
 'record.more_actions': 'Autres actions sur la fiche',
 'record.navigation': 'Navigation entre les fiches',
 'record.needs_review': 'À réviser',
 'record.next': 'Fiche suivante',
 'record.no_changes': 'Aucun champ de la fiche n’a été modifié',
 'record.no_history': 'Aucune modification suivie pour cette fiche.',
 'record.no_pdf_links': 'Aucune page PDF n’est liée à cette fiche.',
 'record.no_record_help': 'Choisissez une fiche depuis Recherche globale, Œuvres ou Fiches.',
 'record.no_record_selected': 'Aucune fiche sélectionnée',
 'record.no_storage_id': 'Cette fiche de base de données n’a pas d’identifiant de stockage.',
 'record.no_unsaved_changes': 'Aucune modification non enregistrée',
 'record.open': 'Ouvrir la fiche',
 'record.open_history': 'Ouvrir l’historique et les options d’annulation',
 'record.open_page': 'Ouvrir la page',
 'record.open_pdf_first': 'Ouvrez {file} dans l’Explorateur PDF pour accéder à la page liée.',
 'record.overview': 'Aperçu',
 'record.page': 'Page',
 'record.page_not_recorded': 'Page non indiquée',
 'record.pdf_explorer': 'Explorateur PDF',
 'record.pdf_links': 'Liens PDF',
 'record.pdf_page': 'Page {page}',
 'record.position_of': '{current} sur {total}',
 'record.previous': 'Fiche précédente',
 'record.primary_text': 'Texte principal',
 'record.provenance': 'Provenance',
 'record.provenance_empty': 'Aucun champ d’attribution structurée n’est consigné pour ce passage.',
 'record.provenance_fields': '{count} champs d’attribution',
 'record.provenance_help': 'Vue structurée de l’attribution indiquant qui parle, quelle position est représentée, la '
                           'posture adoptée et sa cible.',
 'record.provenance_kicker': 'Structure d’attribution',
 'record.quotation_provenance': 'Provenance de la citation',
 'record.record_context': 'Contexte de la fiche',
 'record.record_json': 'fiche',
 'record.region_type': 'Type de région',
 'record.remove_all_pdf': 'Retirer tous les liens PDF',
 'record.remove_selection': 'Retirer de la sélection',
 'record.remove_term': 'Retirer {value}',
 'record.researcher_summary': 'Résumé pour la recherche',
 'record.resize_inspector': 'Redimensionner le volet d’inspection',
 'record.review_llm': 'Réviser avec un LLM',
 'record.saved': 'Modifications de la fiche enregistrées',
 'record.secondary_text': 'Texte secondaire',
 'record.select_help': 'Sélectionnez cette fiche pour les actions de révision, modification ou synchronisation en lot.',
 'record.selection_actions': 'Actions sur le texte sélectionné',
 'record.show_inspector': 'Afficher le volet d’inspection',
 'record.source_documents': 'Documents sources',
 'record.sparse_save_help': 'Seuls les champs modifiés seront enregistrés et ajoutés à la piste d’audit.',
 'record.status': 'État de la fiche',
 'record.summary': 'Résumé chercheur',
 'record.tab_annotations': 'Annotations',
 'record.tab_history': 'Historique',
 'record.tab_indexing': 'Indexation',
 'record.tab_overview': 'Aperçu',
 'record.tab_pdf': 'PDF',
 'record.tab_provenance': 'Provenance',
 'record.text': 'Texte de la fiche',
 'record.translation': 'Traduction',
 'record.unsaved_fields': '{count} champs non enregistrés',
 'record.untitled': 'Fiche sans titre',
 'record.upsert': 'Synchroniser la fiche',
 'record.words': 'mots',
 'record.workspace_kicker': 'Fiche du corpus',
 'records.choose_jsonl': 'Choisir des fichiers JSONL',
 'records.columns': 'Colonnes',
 'records.open_shared_workspace': 'Ouvrir l’espace de corpus partagé',
 'records.open_workspace': 'Ouvrir un espace de corpus',
 'records.open_workspace_help': 'Déposez un ou plusieurs fichiers JSONL n’importe où sur cette page ou choisissez-les '
                                'manuellement. Chaque fichier demeure dans son propre onglet et peut être modifié, '
                                'comparé, recherché, exporté ou envoyé à la base de données du corpus.',
 'records.shared_workspace_help': 'Ce lien conserve l’état du tableau et les filtres, tandis que le contenu JSONL '
                                  'demeure local au navigateur. Choisissez le même fichier JSONL pour rétablir cette '
                                  'vue partagée.',
 'records.table_scroll_label': 'Tableau des fiches. Faites défiler horizontalement pour afficher les colonnes '
                               'supplémentaires.',
 'research.active_pipelines': 'Pipelines de recherche actifs',
 'research.active_profile': 'Profil actif',
 'research.active_runs': 'actives',
 'research.add_filter': 'Ajouter un filtre',
 'research.add_metadata_filter': 'Ajouter un filtre de métadonnées',
 'research.added': 'Ajouté',
 'research.advanced_generation': 'Paramètres avancés de génération',
 'research.advanced_generation_help': 'Contexte, échantillonnage, limites de jetons et options propres au fournisseur',
 'research.all_records': 'Toutes les fiches',
 'research.answer': 'Réponse',
 'research.answer_copied': 'Réponse copiée',
 'research.answer_evidence': 'Preuves de la réponse',
 'research.answer_language': 'Langue de réponse',
 'research.answer_waiting': 'Votre réponse de recherche apparaîtra ici',
 'research.answer_waiting_help': 'Posez une question ci-dessus. La réponse reste dans l’espace de travail avec ses '
                                 'preuves plutôt que dans une fenêtre modale.',
 'research.apply_settings': 'Appliquer à la recherche',
 'research.ask_help': 'Posez une question savante. DerridAI repère, reclasse et synthétise les passages pertinents, '
                      'puis relie la réponse à des preuves vérifiables.',
 'research.ask_title': 'Que recherchez-vous?',
 'research.auto_grade': 'Évaluer automatiquement la réponse finale',
 'research.auto_grade_help': 'S’exécute comme dernière étape du pipeline en arrière-plan.',
 'research.bind_citations': 'Lier les balises de preuve aux citations',
 'research.bind_citations_help': 'Valider les identifiants de preuve avant le formatage final des sources.',
 'research.browse_description': 'Parcourez les œuvres et recherchez dans les bases vectorielles sans exposer de fiches '
                                'modifiables ni le texte intégral du corpus.',
 'research.cached': 'Mise en cache',
 'research.cancel_run': 'Annuler l’exécution de recherche',
 'research.cancelled': 'Annulée',
 'research.cancelling': 'Annulation',
 'research.candidate_pool': 'Bassin de candidats',
 'research.candidate_pool_help': 'Déterminez l’étendue du repérage avant la fusion des classements et le reclassement.',
 'research.characters': 'caractères',
 'research.clear_filters': 'Effacer les filtres',
 'research.clipboard_failed': 'Impossible d’accéder au presse-papiers',
 'research.collection': 'Collection',
 'research.compare_help': 'Comparez côte à côte les fiches résumées visibles par les chercheurs.',
 'research.complete': 'Terminée',
 'research.concepts': 'Concepts',
 'research.concurrent_requests': 'requêtes simultanées',
 'research.contains': 'contient',
 'research.context': 'Contexte de recherche',
 'research.context_window': 'Fenêtre de contexte',
 'research.copy_answer': 'Copier la réponse',
 'research.corpus': 'Corpus',
 'research.corpus_database': 'Base de corpus',
 'research.corpus_retrieval': 'Corpus et repérage',
 'research.corpus_retrieval_help': 'Routage linguistique, profondeur du repérage, reclassement, liaison des citations '
                                   'et évaluation.',
 'research.corpus_search': 'Recherche dans le corpus',
 'research.cross_encoder': 'Encodeur croisé',
 'research.cross_encoder_model': 'Modèle de cross-encoder',
 'research.current_run': 'Exécution actuelle',
 'research.database': 'Base de données',
 'research.database_count_many': '{count} bases de données',
 'research.database_count_one': '{count} base de données',
 'research.database_required': 'Une base de corpus ou des preuves sélectionnées sont requises.',
 'research.decomposition_tokens': 'Jetons de décomposition de requête',
 'research.discourse_role': 'Rôle discursif',
 'research.discover_models': 'Découvrir les modèles',
 'research.document_languages': 'Langues des documents',
 'research.evaluation': 'Évaluation',
 'research.evaluation_help': 'Évaluez facultativement la réponse finale après la génération, sans bloquer l’espace '
                             'Recherche.',
 'research.evidence': 'Preuve',
 'research.evidence_budget': 'Budget de preuves',
 'research.evidence_budget_help': 'Fixez une limite pour chaque passage et pour l’ensemble des preuves transmis au '
                                  'modèle de génération.',
 'research.evidence_citations': 'Preuves et citations',
 'research.evidence_citations_help': 'Contrôlez la taille du paquet de preuves et la liaison déterministe aux sources.',
 'research.evidence_list': 'Liste des preuves',
 'research.evidence_nav_help': 'Budget de contexte, liaison aux sources et évaluation',
 'research.evidence_only': 'Preuves seulement',
 'research.evidence_panel': 'Preuves',
 'research.evidence_records': 'preuves',
 'research.evidence_required': 'Sélectionnez au moins une preuve pour une recherche limitée aux preuves.',
 'research.expert_help': 'Ces paramètres servent à la reproductibilité, à l’évaluation et aux tâches inhabituelles. '
                         'Une recherche normale ne devrait pas les exiger.',
 'research.expert_sections': 'Sections des paramètres experts',
 'research.expert_settings': 'Paramètres experts',
 'research.failed': 'Échouée',
 'research.fetch_k_help': 'Réservoir de candidats MMR',
 'research.fetch_k_label': 'Bassin de candidats MMR',
 'research.filter_value': 'Valeur exacte du filtre',
 'research.filter_works': 'Filtrer les œuvres par titre',
 'research.filters_only': 'Filtres uniquement',
 'research.full_citation': 'Citation complète',
 'research.generation': 'Génération',
 'research.generation_nav_help': 'Modèle et paramètres d’inférence propres à l’exécution',
 'research.generation_override_help': 'Dérogations facultatives pour cette exécution; le profil fournisseur enregistré '
                                      'demeure inchangé.',
 'research.generation_provider': 'Fournisseur de génération',
 'research.generation_provider_help': 'Choisissez le fournisseur et le modèle autorisés pour cette exécution. Les '
                                      'réglages fins demeurent masqués tant qu’ils ne sont pas nécessaires.',
 'research.global_search_admin_help': 'Recherchez dans les fiches chargées ou passez à la recherche sémantique dans la '
                                      'base de corpus sélectionnée.',
 'research.global_search_help': 'Recherchez dans les fiches résumées par texte ou passez au classement sémantique dans '
                                'la base de corpus sélectionnée.',
 'research.grade': 'Analyser et évaluer',
 'research.grading_profile': 'Profil d’évaluation',
 'research.include_works_cited': 'Ajouter les ouvrages cités',
 'research.inference_parameters': 'Paramètres d’inférence',
 'research.inference_parameters_help': 'Paramètres du modèle propres à cette exécution. Conservez les valeurs du '
                                       'profil à moins qu’une dérogation reproductible soit nécessaire.',
 'research.inspect_evidence': 'Examiner les preuves pour',
 'research.instructions': 'Instructions supplémentaires',
 'research.instructions_placeholder': 'Contraintes facultatives sur le cadrage, la comparaison, les citations ou la '
                                      'forme de la réponse.',
 'research.invalid_provider_options': 'Les options du fournisseur doivent former un objet JSON valide.',
 'research.k_help': 'Candidats conservés par voie de repérage',
 'research.k_label': 'Candidats conservés',
 'research.keep_alive': 'Maintenir le modèle chargé',
 'research.lambda_help': 'Équilibre entre pertinence et diversité',
 'research.lambda_label': 'Équilibre de pertinence',
 'research.language_auto': 'Automatique',
 'research.language_help': 'Le routage par langue source reste indépendant.',
 'research.layout_cards': 'Cartes',
 'research.layout_compact': 'Tableau compact',
 'research.layout_roomy': 'Tableau confortable',
 'research.lexical_fallback': 'Solution de rechange lexicale/vectorielle',
 'research.loaded_record_search_placeholder': 'Rechercher dans le texte des fiches de tous les fichiers chargés',
 'research.loading_databases': 'Chargement des bases de données du corpus…',
 'research.loading_workspace': 'Chargement de l’espace de recherche…',
 'research.max_output_tokens': 'Sortie maximale',
 'research.metadata_filters': 'Filtres de métadonnées',
 'research.minimum_probability': 'Probabilité minimale',
 'research.model': 'Modèle',
 'research.model_auto': 'Modèle automatique',
 'research.models_found': 'modèles trouvés',
 'research.no_database': 'Aucune base de données du corpus disponible',
 'research.no_database_admin_help': 'Créez ou restaurez une base de données du corpus pour utiliser la recherche '
                                    'sémantique.',
 'research.no_database_help': 'Un administrateur doit créer ou restaurer une base de données du corpus avant que les '
                              'chercheurs puissent utiliser la recherche et l’espace Recherche.',
 'research.no_evidence_text': 'Aucun passage n’a été conservé pour cet élément de preuve.',
 'research.no_filters': 'Aucun filtre de base de données appliqué.',
 'research.no_matches': 'Aucune fiche correspondante. Essayez une requête plus générale ou une autre base de corpus.',
 'research.no_profile': 'Aucun profil',
 'research.no_profile_configured': 'Aucun profil LLM de recherche n’est disponible.',
 'research.no_recent_questions': 'Aucune question récente correspondante.',
 'research.no_records': 'Aucune fiche disponible',
 'research.no_runs': 'Aucune exécution de recherche',
 'research.no_runs_help': 'Les exécutions terminées et actives apparaîtront ici.',
 'research.no_selected_evidence': 'Aucune preuve épinglée',
 'research.no_selected_evidence_help': 'Ajoutez des fiches depuis Recherche, Œuvres ou la vue Fiche. Le repérage peut '
                                       'toujours trouver des preuves automatiquement.',
 'research.no_work_metadata': 'Aucune métadonnée d’œuvre n’a été trouvée dans cette collection.',
 'research.no_works': 'Aucune œuvre chargée.',
 'research.none': 'Aucun',
 'research.none_selected': 'Aucune base de données sélectionnée',
 'research.nucleus_sampling': 'Échantillonnage top-p',
 'research.of': 'sur',
 'research.off': 'Désactivé',
 'research.on': 'Activé',
 'research.open': 'Ouvrir',
 'research.optional': 'Facultatif',
 'research.page_kicker': 'Recherche fondée sur les preuves',
 'research.page_subtitle': 'Interrogez le corpus, examinez les preuves et conservez la provenance avec la réponse.',
 'research.page_title': 'Espace de recherche',
 'research.parallel_runs_help': 'Vous pouvez lancer une autre question à tout moment. Chaque exécution se poursuit '
                                'indépendamment; les limites de simultanéité du fournisseur déterminent quand les '
                                'tâches en attente s’exécutent.',
 'research.pipeline_help': 'Configurez le corpus, le repérage, les preuves et la génération. Les options avancées '
                           'demeurent disponibles sans détourner l’attention du flux principal de recherche.',
 'research.pipeline_options': 'Repérage, preuves et génération',
 'research.pipeline_running_one': 'pipeline en cours',
 'research.pipeline_stage': 'Étape du pipeline',
 'research.pipeline_title': 'Pipeline de recherche',
 'research.pipelines_running_many': 'pipelines en cours',
 'research.position_holder': 'Détenteur de la position',
 'research.preset_balanced': 'Équilibré',
 'research.preset_custom': 'Personnalisé',
 'research.preset_evidence': 'Preuves sélectionnées seulement',
 'research.preset_precision': 'Haute précision',
 'research.preset_recall': 'Rappel élevé',
 'research.profile': 'Profil de recherche',
 'research.prompt_required': 'Entrez une question de recherche.',
 'research.proposition_status': 'Statut de la proposition',
 'research.provider': 'Fournisseur',
 'research.provider_options': 'Options du fournisseur en JSON',
 'research.provider_options_help': 'Les options avancées propres au fournisseur s’appliquent uniquement à cette '
                                   'exécution.',
 'research.query_decomposition': 'Décomposition de la requête',
 'research.query_decomposition_help': 'Générer des sous-requêtes et des formulations françaises avant le repérage.',
 'research.query_metadata': 'Métadonnées de la requête',
 'research.question': 'Question de recherche',
 'research.question_placeholder': 'Interrogez un concept, un passage, une relation, une attribution ou un désaccord…',
 'research.question_restored': 'Question récente restaurée',
 'research.queued': 'En file',
 'research.quoted_speaker': 'Locuteur cité',
 'research.readonly_chip': 'Corpus en lecture seule · résumés Edmundson',
 'research.readonly_policy': 'La recherche RAG et la consultation des bases et œuvres sont en lecture seule. Le texte '
                             'est retourné sous forme de résumés Edmundson de 2 à 3 phrases.',
 'research.ready_to_run': 'Prêt à lancer la recherche',
 'research.recent_activity_private': 'L’activité locale de modification est visible par les administrateurs.',
 'research.recent_questions': 'Questions récentes',
 'research.record_actions': 'Actions sur la fiche',
 'research.record_char_limit': 'Caractères / preuve',
 'research.record_search_empty': 'Lancez une recherche pour trouver des fiches résumées.',
 'research.record_search_placeholder': 'Rechercher dans le texte des fiches…',
 'research.records': 'fiches',
 'research.redirect_database': 'L’espace Recherche nécessite une base de données du corpus. Ouverture de la création '
                               'd’une base de données.',
 'research.redirect_database_denied': 'Recherche nécessite une base de données du corpus, mais votre rôle ne permet '
                                      'pas d’ouvrir cette page. Demandez à un administrateur de configurer une base de '
                                      'données ou de vous accorder l’accès.',
 'research.remove_run_confirm': 'Retirer cette exécution de recherche et son résultat?',
 'research.repeat_penalty': 'Pénalité de répétition',
 'research.rerank_score': 'Score de reclassement',
 'research.rerank_top_n': 'N premiers à reclasser',
 'research.reranker': 'Reclassement',
 'research.reranking_decomposition': 'Reclassement et décomposition de la requête',
 'research.reranking_decomposition_help': 'Affinez l’ensemble fusionné des candidats et, au besoin, développez la '
                                          'question en sous-requêtes multilingues.',
 'research.rerun': 'Relancer avec ces paramètres',
 'research.rerun_loaded': 'Paramètres chargés dans le composeur',
 'research.research_history': 'Historique de recherche',
 'research.research_in_progress': 'Recherche en cours',
 'research.researcher_evidence_summary': 'Le texte du corpus peut être résumé pour les comptes chercheur.',
 'research.researcher_profile_locked': 'Les paramètres de génération sont fixés par le profil de recherche approuvé '
                                       'par l’administrateur.',
 'research.reset_section': 'Réinitialiser la section',
 'research.result_layout': 'Disposition des résultats',
 'research.result_unavailable': 'Cette exécution de recherche ne possède aucun identifiant de résultat.',
 'research.results': 'résultats',
 'research.retained_runs': 'conservées',
 'research.retrieval': 'Repérage',
 'research.retrieval_diagnostics': 'Diagnostic de repérage',
 'research.retrieval_expert_help': 'Réglez le rappel, la fusion de rangs, le reclassement et le routage multilingue.',
 'research.retrieval_nav_help': 'Routage, profondeur du bassin de candidats et reclassement',
 'research.retrieval_profile': 'Repérage',
 'research.retrieval_ready': 'Repérage prêt',
 'research.retrieval_routes': 'Voies de repérage',
 'research.retrieval_settings': 'Paramètres de repérage et de preuves',
 'research.routing': 'Routage',
 'research.routing_help': 'Choisissez les langues documentaires et les stratégies de repérage utilisées pour trouver '
                          'les candidats.',
 'research.rrf_help': 'Constante de lissage de fusion des rangs',
 'research.rrf_label': 'Lissage de la fusion',
 'research.run': 'Rechercher',
 'research.run_details': 'Détails de l’exécution',
 'research.run_failed': 'L’exécution de recherche a échoué.',
 'research.running': 'En cours',
 'research.runs': 'Exécutions',
 'research.saved_prompt': 'Question enregistrée',
 'research.search_embedding': 'Vectorisation de la requête et comparaison avec la collection sélectionnée…',
 'research.search_empty': 'Entrez une requête pour rechercher dans la base de corpus sélectionnée.',
 'research.search_failed': 'Échec de la recherche',
 'research.search_history': 'Rechercher dans les questions récentes',
 'research.search_loading': 'Recherche dans le corpus…',
 'research.search_method': 'Méthode de recherche',
 'research.search_placeholder': 'Rechercher sémantiquement dans le corpus',
 'research.search_results': 'Résultats de recherche',
 'research.section': 'Recherche',
 'research.seed': 'Graine',
 'research.selected': 'Sélectionnée',
 'research.selected_database_help': 'Les recherches portent uniquement sur la base de données sélectionnée.',
 'research.selected_evidence_count_many': '{count} preuves sélectionnées',
 'research.selected_evidence_count_one': '{count} preuve sélectionnée',
 'research.selected_evidence_only': 'Preuves sélectionnées seulement',
 'research.selected_preview_unavailable': 'L’aperçu du passage n’est pas disponible pour les preuves sélectionnées '
                                          'avant cette version; la fiche complète est résolue lors de la recherche.',
 'research.semantic_db_search': 'Recherche sémantique dans la BD',
 'research.semantic_help': 'Recherchez dans la collection sélectionnée. Le texte retourné est résumé avant d’atteindre '
                           'ce navigateur.',
 'research.semantic_search': 'Recherche sémantique en BD',
 'research.settings_applied': 'Paramètres de recherche appliqués',
 'research.settings_apply_note': 'Les changements s’appliqueront à la prochaine recherche; les profils de fournisseur '
                                 'enregistrés ne seront pas modifiés.',
 'research.settings_reproducibility_note': 'Ces valeurs sont enregistrées avec chaque exécution afin que l’analyse '
                                           'puisse être reproduite ultérieurement.',
 'research.similarity': 'Similarité',
 'research.similarity_help': 'Signal de classement dérivé de la distance vectorielle. Une valeur plus élevée indique '
                             'une plus grande proximité sémantique; ce n’est ni une probabilité ni un niveau de '
                             'confiance.',
 'research.source_binding': 'Liaison aux sources',
 'research.source_binding_help': 'Assurez la traçabilité des affirmations générées au moyen d’identifiants de preuve '
                                 'et de citations déterministes.',
 'research.speaker': 'Locuteur',
 'research.stage_auto_grade': 'Évaluation de la réponse',
 'research.stage_bind_sources': 'Liaison des affirmations aux sources',
 'research.stage_cancelled': 'Recherche annulée',
 'research.stage_completed': 'Recherche terminée',
 'research.stage_context': 'Préparation du contexte de preuves',
 'research.stage_deduplicate': 'Déduplication des preuves',
 'research.stage_failed': 'Échec de la recherche',
 'research.stage_generation': 'Génération de la réponse',
 'research.stage_query_metadata': 'Interprétation de la question',
 'research.stage_queued': 'En attente d’une place d’exécution',
 'research.stage_rerank': 'Reclassement des preuves candidates',
 'research.stage_response_cache': 'Écriture dans la mémoire cache des réponses',
 'research.stage_retrieval': 'Repérage des preuves candidates',
 'research.stage_starting': 'Démarrage du processus de recherche',
 'research.stance': 'Position',
 'research.starting': 'Démarrage…',
 'research.status_cancelled': 'Annulé',
 'research.status_cancelling': 'Annulation',
 'research.status_completed': 'Terminé',
 'research.status_failed': 'Échec',
 'research.status_queued': 'En attente',
 'research.status_running': 'En cours',
 'research.summary_policy': 'Vue chercheur · résumé Edmundson · 2–3 phrases',
 'research.target': 'Cible',
 'research.temperature': 'Température',
 'research.thinking': 'Raisonnement',
 'research.thinking_high': 'Élevé',
 'research.thinking_low': 'Faible',
 'research.thinking_medium': 'Moyen',
 'research.top_k_sampling': 'Échantillonnage top-k',
 'research.topics': 'Thèmes',
 'research.total_char_limit': 'Total de caractères de preuve',
 'research.traditional_search': 'Recherche de fiches',
 'research.untitled_run': 'Recherche sans titre',
 'research.view_all_runs': 'Voir toutes les exécutions',
 'research.waiting': 'En attente du pipeline…',
 'research.works_cited': 'Ouvrages cités',
 'research.works_cited_help': 'Ajoutez une bibliographie déterministe après la réponse.',
 'research.works_menu_help': 'Parcourez les œuvres de la base de corpus sélectionnée. Sélectionnez une œuvre pour voir '
                             'son aperçu, puis parcourez ses fiches résumées.',
 'research.workspace': 'Espace de recherche',
 'research.workspace_help': 'Formulez une question, choisissez les paramètres de repérage et de génération, épinglez '
                            'des preuves, puis exécutez le pipeline complet en conservant la provenance.',
 'research.workspace_title': 'Espace de recherche fondé sur les preuves',
 'role.admin': 'Administrateur',
 'role.researcher': 'Chercheur',
 'roles.admin_locked_help': 'L’accès administrateur demeure fixé au contrôle complet de l’application afin d’éviter sa '
                            'suppression accidentelle.',
 'roles.create': 'Créer un rôle',
 'roles.create_help': 'Commencez à partir d’un rôle non administrateur existant, puis ajustez ses autorisations.',
 'roles.created': 'Rôle créé.',
 'roles.custom_role': 'Rôle personnalisé',
 'roles.default_role': 'Rôle par défaut',
 'roles.delete': 'Supprimer le rôle',
 'roles.delete_confirm': 'Supprimer ce rôle? Les utilisateurs doivent d’abord être réaffectés.',
 'roles.deleted': 'Rôle supprimé.',
 'roles.description': 'Créez des rôles non administrateur et définissez précisément les pages et fonctions protégées '
                      'que chaque rôle peut utiliser.',
 'roles.manage': 'Gérer les autorisations',
 'roles.name': 'Nom du rôle',
 'roles.non_admin_help': 'Chercheur est le rôle non administrateur par défaut. Les rôles personnalisés respectent la '
                         'même frontière de protection des données, selon les autorisations activées ci-dessous.',
 'roles.role_description': 'Description',
 'roles.role_list': 'Rôles',
 'roles.saved': 'Autorisations du rôle enregistrées.',
 'roles.superuser': 'Superutilisateur',
 'roles.template': 'Commencer avec les autorisations de',
 'roles.title': 'Rôles et autorisations',
 'roles.users_link_help': 'Les capacités des rôles sont configurées centralement et appliquées à la fois dans la '
                          'navigation et dans les autorisations de l’API.',
 'search.active_filters': 'Filtres actifs',
 'search.advanced_filter_help': 'Utilisez des conditions par champ lorsque les facettes ne sont pas assez précises.',
 'search.advanced_filters': 'Filtres avancés',
 'search.auto_improve_selected': 'Améliorer automatiquement',
 'search.bulk_edit_selected': 'Modification en lot',
 'search.clear_all': 'Tout effacer',
 'search.clear_query': 'Effacer la requête',
 'search.clear_selection': 'Effacer la sélection',
 'search.column_help': 'Choisissez les champs affichés dans le tableau et leur ordre pour cette vue de recherche.',
 'search.condition': 'Condition',
 'search.configure_columns': 'Configurer les colonnes',
 'search.contains_filter_removed': 'Les filtres de métadonnées « contient » sont offerts seulement en mode Filtres '
                                   'seulement et ont été retirés.',
 'search.copy_link': 'Copier le lien',
 'search.corpus_database': 'Base de données du corpus',
 'search.database_context_help': 'Les résultats et les preuves demeurent liés à cette base de données du corpus.',
 'search.database_placeholder': 'Rechercher sémantiquement dans le corpus…',
 'search.database_result_note': 'Les facettes des résultats sémantiques affinent l’ensemble de candidats retourné; la '
                                'pertinence demeure liée à la méthode de classement choisie.',
 'search.db_in_database': 'Dans la BD',
 'search.db_none': 'Aucune base de données',
 'search.db_not_in_database': 'Absent de la BD',
 'search.db_pending': 'En attente',
 'search.db_synced': 'Synchronisé',
 'search.db_unknown': 'Inconnu',
 'search.delete_saved_view': 'Supprimer la vue enregistrée {name}',
 'search.enter_query': 'Saisissez d’abord une requête de recherche.',
 'search.exploration_history': 'Historique d’exploration',
 'search.field': 'Champ',
 'search.filter_facets': 'Filtrer les valeurs des facettes',
 'search.filter_match': 'Correspondance aux filtres de métadonnées',
 'search.filter_only_help': 'Retourne les fiches à l’aide des filtres de métadonnées sans vectoriser une requête '
                            'textuelle.',
 'search.filter_value_placeholder': 'Saisissez ou choisissez une valeur…',
 'search.filter_values': 'Filtrer les valeurs…',
 'search.filtered_view': 'Vue filtrée',
 'search.filters': 'Filtres',
 'search.kicker': 'Exploration du corpus',
 'search.layout_cards': 'Cartes',
 'search.layout_comfortable': 'Tableau confortable',
 'search.layout_compact': 'Tableau compact',
 'search.link_copied': 'Lien partageable de la recherche copié',
 'search.load_failed': 'Impossible de charger la recherche',
 'search.loaded_placeholder': 'Rechercher dans le texte extrait des fiches chargées…',
 'search.loaded_records': 'Fiches chargées',
 'search.loaded_scope_unavailable': 'La recherche dans les fiches chargées est offerte aux administrateurs qui ont des '
                                    'fiches JSONL locales.',
 'search.loading': 'Chargement de l’espace de recherche…',
 'search.method_filter': 'Filtres seulement',
 'search.method_filter_short': 'Métadonnées sans plongements vectoriels',
 'search.method_mmr': 'MMR',
 'search.method_mmr_short': 'Pertinent, mais moins répétitif',
 'search.method_similarity': 'Similarité',
 'search.method_similarity_short': 'Correspondances sémantiques les plus proches',
 'search.mmr_help': 'Équilibre la pertinence sémantique et la diversité de l’ensemble de résultats.',
 'search.mmr_lambda': 'Poids de pertinence (λ)',
 'search.mmr_match': 'Pertinence sémantique + diversité',
 'search.move_column_down': 'Déplacer {column} vers le bas',
 'search.move_column_up': 'Déplacer {column} vers le haut',
 'search.needs_review': 'À réviser',
 'search.no_database_help': 'Une base de données du corpus doit être créée avant de pouvoir lancer une recherche dans '
                            'la base de données.',
 'search.no_database_title': 'Aucune base de données du corpus disponible',
 'search.no_facet_values': 'Aucune valeur de facette ne correspond à ce filtre.',
 'search.no_recent_searches': 'Aucune recherche récente.',
 'search.no_results': 'Aucune fiche correspondante',
 'search.no_results_help': 'Essayez une requête plus générale, retirez un filtre ou choisissez une autre portée de '
                           'recherche.',
 'search.no_saved_views': 'Aucune vue enregistrée.',
 'search.operator_empty': 'est vide',
 'search.operator_eq': 'est égal à',
 'search.operator_gte': 'au moins',
 'search.operator_has': 'contient',
 'search.operator_lte': 'au plus',
 'search.operator_neq': 'n’est pas égal à',
 'search.operator_nhas': 'ne contient pas',
 'search.operator_notempty': 'n’est pas vide',
 'search.page': 'page',
 'search.page_of': 'Page {page} sur {pages}',
 'search.pagination': 'Pages des résultats de recherche',
 'search.precise_metadata_filter': 'Filtre précis de métadonnées',
 'search.query': 'Requête de recherche',
 'search.ranking_method': 'Méthode de classement',
 'search.ready_help': 'Saisissez une question, une expression, un concept ou un passage. Les options de recherche '
                      'règlent le classement sémantique et les contraintes de métadonnées.',
 'search.ready_title': 'Rechercher dans la base de données du corpus',
 'search.recent_searches': 'Recherches récentes',
 'search.recent_searches_help': 'États d’exploration récents de ce navigateur.',
 'search.redirect_database': 'La recherche nécessite une base de données du corpus. Ouverture de la création de base '
                             'de données.',
 'search.refine': 'Affiner',
 'search.relevance': 'Pertinence',
 'search.reset_defaults': 'Rétablir les valeurs par défaut',
 'search.resize_column': 'Redimensionner la colonne {column}',
 'search.result_count_many': '{count} résultats',
 'search.result_count_one': '{count} résultat',
 'search.result_layout': 'Disposition des résultats',
 'search.results': 'Résultats',
 'search.results_per_page': 'Résultats par page',
 'search.results_table_scroll': 'Tableau des résultats de recherche. Faites défiler horizontalement pour afficher les '
                                'colonnes supplémentaires.',
 'search.review_selected': 'Réviser avec un LLM',
 'search.reviewed': 'Révisé',
 'search.save_current': 'Enregistrer l’état actuel',
 'search.save_view': 'Enregistrer la vue',
 'search.save_view_help': 'Les vues enregistrées conservent l’URL partageable actuelle, y compris la portée, la '
                          'requête, les filtres, le tri, les colonnes et la disposition.',
 'search.saved_and_recent': 'Recherches enregistrées et récentes',
 'search.saved_views': 'Vues enregistrées',
 'search.saved_views_help': 'Espaces de recherche réutilisables enregistrés dans ce navigateur.',
 'search.scope': 'Portée de la recherche',
 'search.search_controls': 'Commandes de recherche',
 'search.search_options': 'Options de recherche',
 'search.searching': 'Recherche en cours…',
 'search.select_page': 'Sélectionner les fiches de cette page',
 'search.select_record': 'Sélectionner',
 'search.select_record_named': 'Sélectionner {record}',
 'search.selected_records': 'fiches sélectionnées',
 'search.selection_actions': 'Actions sur les fiches sélectionnées',
 'search.semantic_match': 'Similarité sémantique',
 'search.show_less': 'Afficher moins',
 'search.show_more': 'Afficher plus',
 'search.similar': 'similaire',
 'search.similarity_explanation': 'La similarité est dérivée de la distance vectorielle; une valeur plus élevée '
                                  'indique une correspondance sémantique plus étroite.',
 'search.similarity_help': 'Classe les fiches selon leur similarité sémantique avec votre requête.',
 'search.sort': 'Trier',
 'search.subtitle': 'Explorez les fiches chargées ou interrogez la base de données du corpus sans perdre le contexte '
                    'de votre requête, de vos filtres et de vos preuves.',
 'search.table_view': 'Vue tableau',
 'search.text_match': 'Correspondance textuelle',
 'search.title': 'Recherche',
 'search.value': 'Valeur',
 'search.view_actions': 'Actions de la vue de recherche',
 'search.view_name': 'Nom de la vue',
 'search.view_name_placeholder': 'p. ex. Passages d’Adieu à réviser',
 'search.view_saved': 'Vue de recherche enregistrée',
 'search.why_result': 'Pourquoi ce résultat',
 'section.corpus': 'Corpus',
 'section.overview': 'Aperçu',
 'section.research': 'Recherche',
 'section.storage': 'Stockage',
 'section.system': 'Système',
 'section.tools': 'Outils',
 'settings.appearance': 'Apparence',
 'settings.appearance_help': 'Choisissez le thème de couleur de votre espace de travail.',
 'settings.appearance_saved': 'Apparence enregistrée',
 'settings.browser_workspace_note': 'Les préférences de thème sont enregistrées dans cet espace de travail du '
                                    'navigateur.',
 'settings.color_theme': 'Thème de couleur',
 'settings.researcher_workspace': 'Espace de recherche',
 'settings.researcher_workspace_help': 'Les comptes chercheur utilisent du texte de corpus résumé et n’affichent pas '
                                       'les contrôles de gestion des bases ou des sources.',
 'settings.save_appearance': 'Enregistrer l’apparence',
 'settings.theme_blue': 'Bleu de référence',
 'settings.theme_blue_help': 'La palette bleue utilisée dans la référence visuelle.',
 'settings.theme_green': 'Vert DerridAI',
 'settings.theme_green_help': 'La palette verte sobre d’origine.',
 'settings.theme_slate': 'Ardoise',
 'settings.theme_slate_help': 'Une palette de recherche neutre, bleu graphite.',
 'storage.advanced_deployment': 'Paramètre de déploiement avancé.',
 'storage.apply_path': 'Appliquer le chemin',
 'storage.change_location': 'Modifier l’emplacement des données',
 'storage.change_location_short': 'Modifier l’emplacement',
 'storage.container_path': 'Chemin dans le conteneur',
 'storage.container_path_help': 'Chemin correspondant à l’intérieur du service DerridAI.',
 'storage.host_folder': 'Dossier hôte',
 'storage.host_folder_help': 'Dossier persistant sur l’ordinateur qui exécute DerridAI.',
 'storage.new_container_path': 'Nouveau chemin dans le conteneur',
 'storage.persistent': 'Stockage persistant',
 'storage.review_chroma': 'Vérifiez l’emplacement où les données Chroma sont stockées.',
 'storage.review_paths': 'Vérifiez le dossier persistant de l’hôte et le chemin du service.',
 'storage.settings': 'Paramètres de stockage',
 'subset.autocomplete_count': '{count} valeurs uniques dans la source JSONL sélectionnée.',
 'subset.autocomplete_large_field': 'La saisie semi-automatique est désactivée pour les grands champs de texte.',
 'subset.no_value': 'Aucune valeur requise',
 'subset.remove_condition': 'Supprimer la condition',
 'subset.value': 'Valeur',
 'theme.blue': 'Bleu',
 'theme.green': 'Vert',
 'theme.slate': 'Ardoise',
 'time.days_ago': 'il y a {count} j',
 'time.hours_ago': 'il y a {count} h',
 'time.just_now': 'à l’instant',
 'time.minutes_ago': 'il y a {count} min',
 'time.recently': 'Récemment',
 'ui.actions': 'Actions',
 'ui.active': 'Actif',
 'ui.add': 'Ajouter',
 'ui.add_evidence': 'Ajouter aux preuves',
 'ui.admin_actions': 'Actions',
 'ui.advanced': 'Avancé',
 'ui.all': 'Tout',
 'ui.apply': 'Appliquer',
 'ui.authentication_authorization': 'Authentification et autorisation',
 'ui.auto_improve_flagged': 'Améliorer les éléments signalés',
 'ui.back': 'Retour',
 'ui.bulk_edit': 'Modifier un champ en lot',
 'ui.cached_responses': 'réponses en cache',
 'ui.cancel': 'Annuler',
 'ui.cannot_delete_self': 'Vous ne pouvez pas supprimer votre compte actuel.',
 'ui.cannot_disable_self': 'Vous ne pouvez pas désactiver votre compte actuel.',
 'ui.change_role': 'Changer le rôle',
 'ui.clean_ocr': 'Nettoyer les artefacts OCR',
 'ui.clear': 'Effacer',
 'ui.clear_selection': 'Effacer la sélection',
 'ui.close': 'Fermer',
 'ui.close_file': 'Fermer le fichier',
 'ui.collapse_all': 'Tout réduire',
 'ui.collapse_sidebar': 'Réduire la barre latérale',
 'ui.columns': 'Colonnes',
 'ui.configure_columns': 'Configurer les colonnes',
 'ui.copied': 'Copié',
 'ui.copy': 'Copier',
 'ui.copy_full': 'Copier la citation complète',
 'ui.copy_inline': 'Copier la citation abrégée',
 'ui.corpus_dbs': 'BD de corpus',
 'ui.corpus_viewer': 'Visionneuse de corpus',
 'ui.create': 'Créer',
 'ui.create_subset': 'Créer un sous-ensemble',
 'ui.created': 'créé',
 'ui.current_role_locked': 'Votre rôle actuel ne peut pas être modifié dans cette ligne.',
 'ui.db_records': 'fiches en BD',
 'ui.default': 'Par défaut',
 'ui.delete': 'Supprimer',
 'ui.disable': 'Désactiver',
 'ui.disabled': 'Désactivé',
 'ui.dismiss': 'Fermer',
 'ui.done': 'Terminé',
 'ui.download': 'Télécharger',
 'ui.edit': 'Modifier',
 'ui.edit_record': 'Modifier la fiche',
 'ui.enable': 'Activer',
 'ui.evidence': 'Preuve',
 'ui.expand_all': 'Tout développer',
 'ui.expand_sidebar': 'Développer la barre latérale',
 'ui.export': 'Exporter',
 'ui.first_page': 'Vous êtes déjà à la première page.',
 'ui.forward': 'Suivant',
 'ui.full': 'Complète',
 'ui.get_citation': 'Obtenir la citation',
 'ui.global_search_placeholder': 'Rechercher dans le corpus, les œuvres, les concepts ou les annotations…',
 'ui.hide_api_key': 'Masquer la clé API',
 'ui.inline': 'Abrégée',
 'ui.jsonl_tabs': 'onglets JSONL',
 'ui.language_dictionaries_translation': 'Dictionnaires de langue et traduction',
 'ui.last_page': 'Vous êtes déjà à la dernière page.',
 'ui.loading': 'Chargement…',
 'ui.loading_derridai': 'Chargement de DerridAI…',
 'ui.loading_dictionary': 'Chargement du dictionnaire…',
 'ui.merge_tabs': 'Fusionner les onglets',
 'ui.more_actions': 'Autres actions',
 'ui.navigation_history': 'Historique de navigation',
 'ui.need_records_bulk_edit': 'Chargez des fiches JSONL avant la modification en lot.',
 'ui.need_records_export': 'Chargez des fiches JSONL avant l’exportation.',
 'ui.need_records_ocr': 'Chargez des fiches JSONL avant le nettoyage OCR.',
 'ui.need_records_subset': 'Chargez des fiches JSONL avant de créer un sous-ensemble.',
 'ui.need_two_tabs_merge': 'Chargez au moins deux onglets JSONL pour les fusionner.',
 'ui.next': 'Suivant',
 'ui.no': 'Non',
 'ui.no_matches': 'Aucun résultat',
 'ui.none': 'Aucun',
 'ui.not_set': 'Non défini',
 'ui.off': 'Désactivée',
 'ui.on': 'Activée',
 'ui.open': 'Ouvrir',
 'ui.open_jsonl': 'Ouvrir JSONL',
 'ui.operations': 'Opérations',
 'ui.previous': 'Précédent',
 'ui.primary_navigation': 'Navigation principale',
 'ui.record_actions': 'Actions de la fiche',
 'ui.records_loaded': 'fiches chargées',
 'ui.refresh': 'Actualiser',
 'ui.remove': 'Retirer',
 'ui.remove_evidence': 'Retirer des preuves',
 'ui.reset': 'Réinitialiser',
 'ui.retry': 'Réessayer',
 'ui.review_flagged': 'Examiner les éléments signalés',
 'ui.rows_per_page': 'Lignes par page',
 'ui.save': 'Enregistrer',
 'ui.saving': 'Enregistrement…',
 'ui.search': 'Rechercher',
 'ui.select_all': 'Tout sélectionner',
 'ui.selected': 'Sélectionné',
 'ui.set_password': 'Définir le mot de passe',
 'ui.show_api_key': 'Afficher la clé API',
 'ui.sign_out': 'Déconnexion',
 'ui.skip_to_content': 'Aller au contenu principal',
 'ui.stay': 'Rester ici',
 'ui.unset': 'Non défini',
 'ui.upsert_queue': 'File de synchronisation',
 'ui.working': 'Traitement…',
 'ui.yes': 'Oui',
 'users.accounts': 'Comptes',
 'users.add_first_profile': 'Ajouter le premier profil',
 'users.add_profile': 'Ajouter un profil',
 'users.add_researcher_provider': 'Ajouter un fournisseur LLM chercheur',
 'users.add_researcher_provider_help': 'Configurez le point de terminaison, découvrez les modèles disponibles, puis '
                                       'choisissez le modèle que les chercheurs pourront utiliser.',
 'users.api_key': 'Clé API',
 'users.api_key_optional_help': 'Facultatif sauf si votre point de terminaison exige une authentification.',
 'users.api_key_placeholder': 'Laisser vide pour conserver la clé stockée',
 'users.api_key_stored_help': 'Une clé est déjà stockée côté serveur. Laisser vide la conserve.',
 'users.assign_existing_profile': 'Attribuer un profil LLM existant',
 'users.assign_existing_profile_help': 'Copie un fournisseur administrateur existant dans l’ensemble des profils '
                                       'approuvés pour les chercheurs. Les secrets restent côté serveur pour les '
                                       'comptes chercheurs.',
 'users.base_url': 'URL de base',
 'users.base_url_help': 'Point de terminaison utilisé par les chercheurs via ce profil côté serveur.',
 'users.choose_existing_profile': 'Choisir un fournisseur configuré…',
 'users.configured_account_many': '{count} comptes configurés',
 'users.configured_account_one': '{count} compte configuré',
 'users.create': 'Créer un utilisateur',
 'users.create_help': 'Chercheur est le rôle non administrateur par défaut. Vous pouvez créer d’autres rôles dans '
                      'Rôles et autorisations.',
 'users.created_toast': 'Compte créé.',
 'users.delete': 'Supprimer',
 'users.delete_help': 'Cette action supprime le compte et toutes ses sessions actives. Les données des tâches RAG '
                      'existantes ne sont pas supprimées automatiquement.',
 'users.deleted_toast': 'Compte supprimé.',
 'users.description': 'Les administrateurs ont accès à tout l’espace du corpus. Les chercheurs peuvent utiliser '
                      'Recherche ainsi que la recherche en lecture seule dans les bases et les œuvres; le texte du '
                      'corpus est résumé côté serveur avec Edmundson.',
 'users.disabled_toast': 'Compte désactivé.',
 'users.discover_models': 'Tester / découvrir les modèles',
 'users.discover_models_help': 'Testez le fournisseur pour découvrir les modèles disponibles.',
 'users.enabled_toast': 'Compte activé.',
 'users.last_login': 'Dernière connexion',
 'users.loading': 'Chargement des utilisateurs…',
 'users.login_count': 'Connexions',
 'users.max_concurrent': 'Requêtes simultanées maximales',
 'users.max_concurrent_help': 'Limite les appels chercheur simultanés via ce profil.',
 'users.model': 'Modèle',
 'users.model_not_set': 'modèle non défini',
 'users.model_placeholder': 'Choisir un modèle découvert ou saisir un ID',
 'users.models_discovered': 'modèles découverts',
 'users.never': 'Jamais',
 'users.new_password': 'Nouveau mot de passe',
 'users.new_provider': 'Nouveau fournisseur',
 'users.no_researcher_profiles': 'Aucun profil LLM chercheur',
 'users.no_researcher_profiles_help': 'Ajoutez un fournisseur approuvé afin que les chercheurs puissent utiliser '
                                      'Recherche sans voir les identifiants administrateur ni une configuration de '
                                      'fournisseur sans restriction.',
 'users.password_help': 'Minimum de 6 caractères.',
 'users.password_saved_toast': 'Mot de passe réinitialisé.',
 'users.profile_id': 'ID du profil',
 'users.profile_id_help': 'Identifiant stable utilisé par les tâches chercheur.',
 'users.profile_id_placeholder': 'recherche-locale',
 'users.profile_name': 'Nom d’affichage',
 'users.profile_name_placeholder': 'Modèle de recherche local',
 'users.profile_required': 'L’identifiant, le nom et le modèle du profil sont requis.',
 'users.profile_save_help': 'Les modifications des cartes existantes sont préparées jusqu’à leur enregistrement.',
 'users.provider_ready': 'Fournisseur prêt',
 'users.provider_type': 'Type de fournisseur',
 'users.provider_unavailable': 'Fournisseur indisponible',
 'users.refresh': 'Actualiser',
 'users.remove_profile_confirm': 'Supprimer ce profil LLM chercheur?',
 'users.researcher_profiles': 'Profils LLM pour chercheurs',
 'users.researcher_profiles_help': 'Seuls ces profils statiques sont offerts aux chercheurs. Les secrets restent côté '
                                   'serveur. Les profils Ollama locaux respectent la concurrence maximale; les '
                                   'requêtes RAG supplémentaires attendent qu’une place se libère.',
 'users.reset_password': 'Réinitialiser le mot de passe',
 'users.role': 'Rôle',
 'users.role_saved_toast': 'Rôle mis à jour.',
 'users.save_profiles': 'Enregistrer les profils',
 'users.temporary_password': 'Mot de passe temporaire',
 'users.title': 'Utilisateurs et rôles',
 'users.use_profile': 'Utiliser le profil',
 'users.username': 'Nom d’utilisateur',
 'vector.advanced': 'Avancé',
 'vector.apply_storage_path': 'Appliquer le chemin de stockage',
 'vector.available_loaded_works': 'Œuvres chargées disponibles',
 'vector.available_works_count': '{count} œuvres dans l’espace de travail du navigateur',
 'vector.backend': 'Moteur',
 'vector.background_build': 'Construction en arrière-plan',
 'vector.background_build_help': 'Après la création, {count} fiches sélectionnées seront placées dans une seule '
                                 'construction serveur en arrière-plan. Vous pouvez continuer à utiliser DerridAI.',
 'vector.browse_works': 'Parcourir les œuvres',
 'vector.browse_works_help': 'Ouvrez une œuvre pour ne parcourir que ses fiches dans cette collection.',
 'vector.build': 'Construction',
 'vector.build_history': 'Historique des constructions ({count})',
 'vector.change_location': 'Changer l’emplacement',
 'vector.change_storage_location': 'Changer l’emplacement des données',
 'vector.change_storage_location_help': 'Paramètre de déploiement avancé. Les collections existantes ne sont pas '
                                        'déplacées automatiquement.',
 'vector.change_storage_path': 'Modifier le chemin de stockage',
 'vector.change_storage_warning': 'La modification de ce chemin fait basculer DerridAI vers un autre répertoire de '
                                  'persistance Chroma. Les collections existantes restent dans leur répertoire '
                                  'd’origine jusqu’à ce que vous y reveniez.',
 'vector.changes_pending': '{count} modifications en attente',
 'vector.checking_path': 'Vérification…',
 'vector.collection': 'Collection',
 'vector.collection_basics': 'Paramètres de base',
 'vector.collection_basics_help': 'Nommez la collection et indiquez comment DerridAI doit l’utiliser.',
 'vector.collection_created': '{name} créée',
 'vector.collection_created_build': '{name} créée; construction en arrière-plan mise en file.',
 'vector.collection_created_sync': '{name} créée; les œuvres sélectionnées sont en cours de synchronisation.',
 'vector.collection_creation_steps': 'Étapes de création de la collection',
 'vector.collection_description': 'Description',
 'vector.collection_description_placeholder': 'Corpus principal multilingue de recherche sur Derrida',
 'vector.collection_name': 'Nom de la collection',
 'vector.collection_name_help': 'Utilisez un nom court et stable. Vous pourrez la parcourir et la rechercher depuis '
                                'les bases vectorielles.',
 'vector.collection_name_required': 'Saisissez un nom de collection',
 'vector.collection_name_rules': 'De 3 à 128 caractères; commencez et terminez par une lettre ou un chiffre; utilisez '
                                 'lettres, chiffres, points, traits de soulignement ou traits d’union.',
 'vector.collection_role': 'Rôle de la collection',
 'vector.collection_role_help': 'Les collections principales constituent la base du corpus; les collections '
                                'linguistiques sont dérivées ou limitées par langue.',
 'vector.collection_switch_help': 'Choisissez une collection à gérer ou à parcourir.',
 'vector.collections': 'Collections',
 'vector.compare_modes': 'Comparer les modes',
 'vector.compare_modes_help': 'Exécute la même requête avec les modes disponibles afin de comparer leur classement.',
 'vector.comparing_modes': 'Comparaison des modes de recherche…',
 'vector.completed_builds': 'constructions achevées',
 'vector.container_path': 'Chemin du conteneur',
 'vector.container_path_help': 'Chemin correspondant à l’intérieur du service DerridAI. Il sert surtout au dépannage '
                               'du déploiement.',
 'vector.create_and_build': 'Créer et construire',
 'vector.create_and_sync': 'Créer et synchroniser les œuvres sélectionnées',
 'vector.create_collection': 'Créer une collection',
 'vector.create_collection_help': 'Configurez d’abord la collection, puis synchronisez éventuellement les œuvres '
                                  'chargées.',
 'vector.create_empty': 'Créer une collection vide',
 'vector.create_failed': 'Impossible de créer la collection',
 'vector.create_first_collection': 'Créer la première collection',
 'vector.create_large_sync_help': 'Comme cette sélection contient {count} fiches, DerridAI la synchronisera par lots '
                                  'au premier plan après la création. Gardez cet onglet ouvert jusqu’à la fin.',
 'vector.create_step_basics': 'Collection',
 'vector.create_step_embedding': 'Vectorisation',
 'vector.create_step_retrieval': 'Recherche',
 'vector.create_step_review': 'Réviser et construire',
 'vector.create_step_source': 'Source',
 'vector.create_step_sync': 'Synchroniser les œuvres',
 'vector.created_with': 'Créée avec',
 'vector.creating_collection': 'Création de la collection…',
 'vector.creation_steps': 'Étapes de création de la collection',
 'vector.current': 'À jour',
 'vector.current_build': 'Construction courante',
 'vector.current_container_path': 'Chemin actuel dans le conteneur',
 'vector.default': 'par défaut',
 'vector.delete_collection': 'Supprimer la collection',
 'vector.deletion_protection': 'Protection contre la suppression',
 'vector.deletion_protection_help': 'Empêche la suppression accidentelle jusqu’à ce que la protection soit '
                                    'explicitement désactivée.',
 'vector.dimension_auto': 'Détectée automatiquement',
 'vector.dimension_optional': 'Facultatif jusqu’au premier vecteur',
 'vector.disable_protection': 'Désactiver la protection',
 'vector.disable_protection_before_delete': 'Désactivez la protection avant de supprimer cette collection.',
 'vector.distance': 'Distance',
 'vector.distance_metric': 'Métrique de distance',
 'vector.download_current_work': 'Télécharger l’œuvre actuelle',
 'vector.download_db_jsonl': 'Télécharger le JSONL complet de la collection',
 'vector.embedding_configuration': 'Configuration des vecteurs',
 'vector.embedding_dimension': 'Dimension vectorielle',
 'vector.embedding_dimension_help': 'DerridAI sonde automatiquement les intégrations générées et refuse les dimensions '
                                    'incompatibles avant d’écrire des fiches.',
 'vector.embedding_edit_help': 'Choisissez comment DerridAI crée les vecteurs de cette collection.',
 'vector.embedding_locked_help': 'Les paramètres de vectorisation sont verrouillés après l’ajout de fiches. Créez une '
                                 'nouvelle collection vide pour les modifier.',
 'vector.embedding_model': 'Modèle de vectorisation',
 'vector.embedding_model_help': 'Ce paramètre est verrouillé dès que la collection contient des fiches.',
 'vector.embedding_model_required': 'Choisissez un modèle d’intégration Ollama',
 'vector.embedding_provider': 'Fournisseur de vecteurs',
 'vector.embedding_setup': 'Configuration des vecteurs',
 'vector.embedding_setup_help': 'Choisissez comment les nouvelles fiches de cette collection recevront leurs vecteurs.',
 'vector.empty_help': 'Une collection vectorielle fournit à DerridAI une base de corpus persistante pour la recherche '
                      'sémantique, la navigation des chercheurs et le RAG. Configurez-la, puis synchronisez '
                      'éventuellement les œuvres déjà chargées.',
 'vector.empty_kicker': 'Bases vectorielles',
 'vector.empty_manifest_help': 'La collection vide conservera tout de même son contrat d’intégration validé et son '
                               'manifeste.',
 'vector.empty_title': 'Créez votre première collection de corpus',
 'vector.enable_protection': 'Activer la protection',
 'vector.english_collection': 'Collection anglaise',
 'vector.english_collection_help': 'Reçoit les fiches acheminées comme étant en anglais.',
 'vector.enter_query': 'Saisissez une requête pour comparer les modes de recherche.',
 'vector.enter_storage_path': 'Saisissez un chemin de stockage Chroma',
 'vector.export_from_collection': 'Exporter depuis la collection',
 'vector.filter_collections': 'Rechercher des collections…',
 'vector.french_collection': 'Collection française',
 'vector.french_collection_help': 'Reçoit les fiches acheminées comme étant en français.',
 'vector.generate_language_collections': 'Générer les collections EN / FR',
 'vector.host_path': 'Dossier hôte',
 'vector.host_path_help': 'Dossier persistant sur la machine qui exécute DerridAI. Sauvegardez ce dossier pour '
                          'préserver les collections.',
 'vector.hybrid': 'Hybride',
 'vector.hybrid_help': 'La recherche hybride fusionne les résultats sémantiques et lexicaux exacts afin que noms, '
                       'citations, néologismes et termes multilingues aient une voie indépendante des intégrations.',
 'vector.hybrid_recommended': 'Hybride — recommandé',
 'vector.hybrid_score': 'Hybride',
 'vector.import_export': 'Importer et exporter des fiches',
 'vector.import_export_help': 'Synchronisez les fiches JSONL chargées vers cette collection, ou exportez les fiches de '
                              'la collection vers un JSONL propre. L’export ne modifie pas la collection.',
 'vector.language_collections': 'Collections linguistiques',
 'vector.language_derive_help': 'Créez des collections anglaise et française séparées en acheminant les fiches selon '
                                'les métadonnées document_language.',
 'vector.language_source_help': 'La collection source demeure inchangée. Les collections cibles existantes sont mises '
                                'à jour selon les règles de routage actuelles.',
 'vector.language_tags': 'Étiquettes de langue',
 'vector.language_tags_help': 'Étiquettes descriptives facultatives. Laissez les deux décochées pour une collection '
                              'multilingue.',
 'vector.language_tags_scope_help': 'Portée descriptive et de filtrage seulement; une collection principale '
                                    'multilingue est préférable à des bases physiques dupliquées par langue.',
 'vector.last_build_error': 'Dernière erreur de construction',
 'vector.last_synced': 'Dernière synchro',
 'vector.lexical': 'Lexical (BM25)',
 'vector.lexical_only': 'Lexical seulement',
 'vector.load_jsonl_any_first': 'Chargez d’abord au moins un onglet JSONL.',
 'vector.load_jsonl_first': 'Chargez et sélectionnez d’abord un onglet JSONL.',
 'vector.manage_collections': 'Gérer les collections',
 'vector.manage_collections_help': 'Créez une collection ou actualisez la liste après des modifications effectuées '
                                   'ailleurs.',
 'vector.manifest_builds': 'Manifeste et constructions',
 'vector.manifest_builds_help': 'Consultez le contrat de recherche reproductible, l’instantané source et l’historique '
                                'récent des constructions achevées.',
 'vector.model_not_used': 'Ce fournisseur n’utilise pas de nom de modèle Ollama.',
 'vector.never_synced': 'Pas encore synchronisée',
 'vector.new_collection': 'Nouvelle collection vectorielle',
 'vector.new_collection_short': 'Nouvelle',
 'vector.new_container_path': 'Nouveau chemin du conteneur',
 'vector.new_container_path_help': 'Saisissez le répertoire de persistance Chroma côté serveur. Ne le modifiez que si '
                                   'vous comprenez la correspondance du déploiement.',
 'vector.new_direction_build': 'Créer une collection de recherche reproductible',
 'vector.new_direction_build_help': 'Choisissez la source, validez le contrat de recherche, puis créez une collection '
                                    'avec manifeste sans bloquer l’espace de travail.',
 'vector.no_build': 'Aucune construction',
 'vector.no_build_history': 'Aucune construction de synchronisation achevée n’a encore été enregistrée.',
 'vector.no_collection_matches': 'Aucune collection ne correspond à cette recherche.',
 'vector.no_loaded_works': 'Aucune œuvre JSONL chargée n’est disponible pour la synchronisation.',
 'vector.no_results': 'Aucun résultat',
 'vector.no_unsynced_changes': 'Aucune modification locale non synchronisée confirmée.',
 'vector.no_unsynced_changes_help': 'DerridAI n’a trouvé aucune fiche chargée modifiée depuis sa dernière '
                                    'synchronisation ni confirmée absente de cette collection.',
 'vector.open_current_page': 'Ouvrir la page actuelle du tableau en JSONL',
 'vector.open_current_work': 'Ouvrir l’œuvre actuelle en JSONL',
 'vector.open_db_jsonl': 'Ouvrir toute la collection dans un onglet JSONL',
 'vector.open_work_records': 'Ouvrir les fiches',
 'vector.page_export_help': 'Ouvrez uniquement les fiches visibles sur cette page paginée dans un onglet JSONL '
                            'temporaire. Il ne s’agit pas d’un export complet de la collection.',
 'vector.page_export_title': 'Page actuelle du tableau',
 'vector.page_help': 'Créez, synchronisez, parcourez, recherchez et exportez les collections Chroma persistantes '
                     'utilisées par DerridAI.',
 'vector.persistent_storage': 'Stockage persistant',
 'vector.precomputed_search_help': 'Les collections à vecteurs précalculés peuvent utiliser la recherche lexicale et '
                                   'le volet lexical de la recherche hybride. Les recherches sémantique et MMR exigent '
                                   'une fonction d’intégration de requête.',
 'vector.preflight_and_review': 'Prévalider et réviser',
 'vector.preflight_failed': 'Échec de la prévalidation des intégrations',
 'vector.preflight_passed': 'Prévalidation des intégrations réussie',
 'vector.preflight_ready': 'Prêt à créer',
 'vector.protected': 'Protégée',
 'vector.protection_disabled': 'Protection contre la suppression désactivée',
 'vector.protection_enabled': 'Protection contre la suppression activée',
 'vector.protection_failed': 'Impossible de modifier la protection contre la suppression',
 'vector.provider_chroma': 'Chroma par défaut',
 'vector.provider_chroma_help': 'Laisser Chroma utiliser sa fonction de vectorisation par défaut.',
 'vector.provider_ollama': 'Ollama',
 'vector.provider_ollama_help': 'Générer les vecteurs avec un modèle Ollama local configuré.',
 'vector.provider_precomputed': 'Pré-calculés',
 'vector.provider_precomputed_help': 'Les fiches doivent déjà contenir des vecteurs; la recherche sémantique par '
                                     'requête n’est pas disponible.',
 'vector.query_embedding': 'Intégration de la requête',
 'vector.record_inspector': 'Inspecteur de fiche',
 'vector.retrieval_contract': 'Définir le contrat de recherche',
 'vector.retrieval_contract_help': 'L’identité du modèle d’intégration, la dimension, la métrique de distance et le '
                                   'mode de recherche forment un contrat durable validé avant la création.',
 'vector.retrieval_mode': 'Mode de recherche',
 'vector.retrieval_search_placeholder': 'Rechercher dans cette collection…',
 'vector.review_build': 'Réviser la construction',
 'vector.review_build_help': 'La création est stricte : DerridAI ne réutilise jamais silencieusement une collection '
                             'existante. Le contrat résolu et l’instantané source font partie du manifeste.',
 'vector.role_general': 'Générale',
 'vector.role_language': 'Spécifique à une langue',
 'vector.role_language_help': 'Le rôle et les étiquettes de langue décrivent l’utilisation prévue de cette base.',
 'vector.role_language_title': 'Rôle et langue',
 'vector.role_primary': 'Principale',
 'vector.running_preflight': 'Prévalidation en cours…',
 'vector.search_method': 'Méthode de recherche',
 'vector.search_results_empty': 'Les résultats de recherche apparaîtront ici.',
 'vector.select_collection': 'Sélectionnez une collection',
 'vector.select_collection_help': 'Choisissez une collection dans la liste pour gérer ses paramètres, synchroniser des '
                                  'fiches, effectuer des recherches ou parcourir son contenu.',
 'vector.selected_collection': 'Collection sélectionnée',
 'vector.selected_works_label': '{count} œuvres sélectionnées',
 'vector.semantic': 'Sémantique',
 'vector.semantic_only': 'Sémantique seulement',
 'vector.semantic_precomputed_help': 'La recherche sémantique est indisponible car cette collection contient des '
                                     'vecteurs pré-calculés sans fonction de vectorisation des requêtes.',
 'vector.semantic_search': 'Recherche sémantique',
 'vector.semantic_search_help': 'Trouvez des fiches par leur sens à l’aide du fournisseur de vectorisation configuré '
                                'pour cette collection.',
 'vector.semantic_search_placeholder': 'Rechercher cette collection par le sens…',
 'vector.source': 'Source',
 'vector.source_dataset': 'Choisir le jeu de données source',
 'vector.source_dataset_help': 'Définissez la collection logique et le corpus que cette construction représentera. La '
                               'sélection source est inscrite dans le manifeste.',
 'vector.source_records': 'Fiches source',
 'vector.source_snapshot': 'Instantané source',
 'vector.source_unrecorded': 'Non consignée',
 'vector.status': 'État',
 'vector.storage_change_caution': 'Changer l’emplacement de stockage ne déplace pas les collections existantes.',
 'vector.storage_change_caution_help': 'DerridAI commencera à utiliser le nouveau répertoire. Les collections '
                                       'existantes restent dans le répertoire actuel jusqu’à ce que vous y reveniez ou '
                                       'les déplaciez hors de l’application.',
 'vector.storage_change_failed': 'Impossible de modifier le stockage Chroma : {message}',
 'vector.storage_changed': 'Stockage Chroma modifié vers {path}',
 'vector.storage_help': 'Chroma conserve sa base dans un répertoire côté serveur. Le chemin du conteneur est celui que '
                        'DerridAI voit; le dossier hôte est le dossier mappé sur la machine qui exécute DerridAI, qui '
                        'survit aux redémarrages du conteneur et peut être sauvegardé normalement.',
 'vector.storage_settings': 'Paramètres de stockage',
 'vector.storage_settings_help': 'Consultez l’emplacement des données Chroma. La plupart des installations devraient '
                                 'conserver ces paramètres tels quels.',
 'vector.summary': 'Résumé des bases vectorielles',
 'vector.sync': 'Synchroniser',
 'vector.sync_active_jsonl': 'Synchroniser le JSONL actif',
 'vector.sync_all_loaded': 'Synchroniser tous les JSONL chargés',
 'vector.sync_available_works': 'Synchroniser les œuvres disponibles',
 'vector.sync_available_works_help': 'Ajoutez éventuellement les œuvres du corpus déjà chargées juste après la '
                                     'création. Vous pouvez aussi laisser la collection vide.',
 'vector.sync_behavior_help': 'La synchronisation met à jour les fiches correspondantes et insère les nouvelles. Toute '
                              'synchronisation de plus de 500 fiches exige une confirmation, s’exécute au premier plan '
                              'par lots de 500 et bloque les autres actions DerridAI jusqu’à sa fin ou son annulation.',
 'vector.sync_into_collection': 'Synchroniser vers la collection',
 'vector.sync_selected': 'Synchroniser la sélection',
 'vector.sync_state': 'État de synchronisation',
 'vector.synced_at': 'Dernière synchro {time}',
 'vector.system_storage': 'Stockage système',
 'vector.tab_builds': 'Constructions',
 'vector.tab_data': 'Données',
 'vector.tab_overview': 'Aperçu',
 'vector.tab_retrieval': 'Recherche',
 'vector.tab_settings': 'Paramètres',
 'vector.test_retrieval': 'Tester la recherche',
 'vector.test_retrieval_help': 'Comparez la recherche sémantique, lexicale, hybride et diversifiée sur le même corpus '
                               'stocké.',
 'vector.text_field': 'Champ texte',
 'vector.unsynced_changes': 'Modifications locales non synchronisées',
 'vector.unsynced_changes_count': '{count} modifications locales non synchronisées',
 'vector.unsynced_changes_help': 'Il s’agit des fiches de l’espace de travail modifiées depuis leur dernière '
                                 'synchronisation confirmée, ainsi que de celles dont DerridAI a confirmé l’absence '
                                 'dans la collection sélectionnée. Retirer un élément ne masque que sa version '
                                 'actuelle; une modification ultérieure le remettra dans la file.',
 'vector.unsynced_changes_what': 'Que contient cette liste?',
 'vector.workspace_actions': 'Espace des collections',
 'vector.workspace_sections': 'Sections de la collection',
 'works.add_jsonl': 'Ajouter un fichier JSONL',
 'works.add_jsonl_help': 'Ouvrez une autre source de corpus et ajoutez ses œuvres à cet espace de travail.',
 'works.all_records_label': 'fiches de toutes les œuvres',
 'works.apply_metadata': 'Appliquer les métadonnées',
 'works.apply_metadata_confirm': 'Appliquer les métadonnées de l’œuvre ?',
 'works.apply_metadata_confirm_help': 'Appliquer les métadonnées sélectionnées à {works} œuvre(s) et {records} fiches '
                                      'associées ?',
 'works.apply_selected_metadata': 'Appliquer les métadonnées sélectionnées',
 'works.applying_metadata': 'Application des métadonnées…',
 'works.auto_improve': 'Améliorer les signalements',
 'works.background_operation': 'Opération en arrière-plan',
 'works.background_operation_help': 'Vous pouvez quitter la page Œuvres. Ouvrez l’opération terminée pour vérifier et '
                                    'appliquer les modifications proposées.',
 'works.browse_records': 'Parcourir les fiches',
 'works.catalog_source': 'Source du catalogue',
 'works.catalogue_selected': 'Correspondance de catalogue bibliographique public sélectionnée par le LLM.',
 'works.checking_database': 'Vérification de la base vectorielle…',
 'works.concurrent_requests': 'requête(s) simultanée(s) max.',
 'works.cover_alt': 'Couverture de {work}',
 'works.cover_of': 'Couverture de {title}',
 'works.current_value': 'Actuel',
 'works.database_context': 'Base de synchronisation des œuvres',
 'works.database_context_help': 'L’état de synchronisation et les actions Synchroniser de cette page concernent la '
                                'base de corpus sélectionnée. La changer ne modifie pas vos fichiers JSONL chargés.',
 'works.edit_metadata': 'Modifier les métadonnées',
 'works.field': 'Champ',
 'works.files': 'fichiers',
 'works.filter_title': 'Filtrer les œuvres par titre',
 'works.indexed_patterns': 'Motifs indexés dans cette œuvre',
 'works.inspect_mixed_aria': 'Consulter les {count} valeurs uniques pour {field}',
 'works.leave_metadata_help': 'Cela fermera le flux de métadonnées et ouvrira les fournisseurs LLM. La recherche n’a '
                              'pas encore commencé.',
 'works.leave_metadata_title': 'Ouvrir les profils de fournisseurs?',
 'works.loading': 'Chargement des œuvres',
 'works.loading_cards': 'Chargement de {count} cartes d’œuvres',
 'works.lookup_scope': 'Portée de la recherche',
 'works.lookup_scope_help': 'Obtenir les métadonnées bibliographiques de {count} œuvre(s).',
 'works.metadata_applied': '{records} fiches mises à jour · {fields} modifications de champs suivies',
 'works.metadata_fields_help': 'Les propositions peuvent inclure l’éditeur, l’année/le lieu de publication, l’édition, '
                               'le traducteur, l’ISBN, la langue, la citation et la couverture.',
 'works.metadata_lookup_failed': 'Impossible de lancer la recherche de métadonnées',
 'works.metadata_lookup_started': 'Recherche de métadonnées lancée pour {count} œuvre(s).',
 'works.metadata_no_match_count': '{count} œuvre(s) n’ont pas de correspondance exploitable ou ont renvoyé une erreur.',
 'works.metadata_variants': 'Variantes des métadonnées',
 'works.metadata_workflow_kicker': 'Enrichissement bibliographique',
 'works.mixed': 'Mixte',
 'works.mixed_across_records': 'Valeurs mixtes selon les fiches',
 'works.mixed_values_help': 'Voici les valeurs distinctes présentes dans les fiches de cette œuvre. Les nombres '
                            'permettent de distinguer une valeur dominante d’une incohérence isolée avant une '
                            'modification en lot.',
 'works.need_review': 'à examiner',
 'works.no_catalogue_match': 'Aucune correspondance de catalogue',
 'works.no_indexed_values': 'Aucune valeur indexée dans les fiches chargées.',
 'works.no_metadata_changes': 'Aucune modification de métadonnées n’a été proposée.',
 'works.no_provider_profiles': 'Aucun profil fournisseur LLM n’est configuré',
 'works.no_provider_profiles_help': 'Créez un profil fournisseur LLM avant de renseigner les métadonnées des œuvres.',
 'works.no_work_metadata_rows': 'Aucune fiche d’œuvre n’est disponible pour la recherche de métadonnées.',
 'works.no_works_to_populate': 'Aucune œuvre n’est disponible à renseigner.',
 'works.open_overview': 'Ouvrir l’aperçu de l’œuvre',
 'works.open_providers': 'Ouvrir les fournisseurs',
 'works.open_records_for_work': 'Ouvrir les {count} fiches de {work}',
 'works.open_review_records_for_work': 'Ouvrir les {count} fiches à réviser de {work}',
 'works.other_values': 'Autres',
 'works.overview': 'Aperçu de l’œuvre',
 'works.populate_all_metadata': 'Renseigner toutes les métadonnées avec le LLM',
 'works.populate_all_metadata_label': 'Renseigner les métadonnées · {count} œuvres',
 'works.populate_metadata_help': 'DerridAI interroge des sources bibliographiques publiques adaptées au format (Open '
                                 'Library, Google Books et Crossref), demande au LLM sélectionné d’identifier la '
                                 'meilleure correspondance, puis renvoie des modifications proposées à vérifier. Rien '
                                 'n’est appliqué automatiquement.',
 'works.populate_metadata_llm': 'Renseigner les métadonnées avec le LLM',
 'works.proposal_edit_help': 'Modifiez les valeurs proposées si nécessaire, puis appliquez les champs sélectionnés à '
                             'toutes les fiches chargées appartenant à cette œuvre.',
 'works.proposed_field_changes': 'modifications de champs proposées',
 'works.proposed_value': 'Proposé',
 'works.provider_model_required': 'Le profil fournisseur sélectionné n’a pas de modèle configuré.',
 'works.provider_profile': 'Profil fournisseur',
 'works.provider_profile_help': 'Utilise les mêmes profils fournisseurs configurés que RAG, les outils PDF et la '
                                'révision LLM.',
 'works.provider_required': 'Sélectionnez un profil fournisseur LLM.',
 'works.remove_entire': 'Supprimer toute l’œuvre',
 'works.review_flagged': 'Examiner les signalements ({count})',
 'works.review_metadata_proposals': 'Vérifier les propositions de métadonnées',
 'works.role_occurrences': 'occurrences de rôle',
 'works.search_records': 'Rechercher les fiches',
 'works.select_collection': 'Sélectionnez d’abord une collection de corpus.',
 'works.select_metadata_changes': 'Sélectionnez au moins une modification de métadonnées proposée.',
 'works.separate_jsonl': 'Séparer les œuvres',
 'works.shown': 'affichées',
 'works.source_files': 'fichiers sources',
 'works.source_reason': 'Source / justification',
 'works.start_metadata_lookup': 'Lancer la recherche en arrière-plan',
 'works.starting_metadata_lookup': 'Démarrage…',
 'works.step_provider': 'Profil fournisseur',
 'works.step_review': 'Vérifier les propositions',
 'works.step_scope': 'Œuvres',
 'works.sync': 'Synchroniser',
 'works.sync_all': 'Synchroniser toutes les œuvres',
 'works.translated_by': 'Traduit par',
 'works.unique_values': 'valeurs',
 'works.unknown_author': 'Auteur inconnu',
 'works.unknown_source': 'Source inconnue',
 'works.unmatched_works': 'Œuvres sans correspondance / en échec',
 'works.untitled': 'Œuvre sans titre',
 'works.view_annotations': 'Annotations ({count})',
 'works.work_insights': 'Aperçu de l’œuvre',
 'works.work_insights_help': 'Les nombres sont calculés à partir des fiches actuellement chargées et utilisent '
                             'directement les champs de métadonnées du corpus.',
 'pdf_corpus.bulk_metadata_title': 'Modifier les métadonnées des notices en lot',
 'pdf_corpus.bulk_metadata_help': 'Seuls les champs cochés sont modifiés. Les valeurs existantes de tous les autres champs restent inchangées.',
 'pdf_corpus.bulk_metadata_all_records': 'Appliquer aux {count} notices plutôt qu’aux {selected} notices sélectionnées',
 'pdf_corpus.bulk_value_for': 'Valeur pour {field}',
 'pdf_corpus.bulk_scope_all': 'Mettra à jour les {count} notices',
 'pdf_corpus.bulk_scope_selected': 'Mettra à jour {count} notices sélectionnées',
 'pdf_corpus.apply_bulk_metadata': 'Appliquer les modifications de métadonnées',
 'pdf_corpus.bulk_edit_metadata': 'Modifier les métadonnées en lot',
 'pdf_corpus.bulk_metadata_applied': 'Métadonnées mises à jour pour {count} notice(s).',
 'pdf_corpus.manifest_identity_group': 'Identité de l’œuvre',
 'pdf_corpus.manifest_publication_group': 'Publication',
 'pdf_corpus.manifest_language_group': 'Langue et traduction',
 'pdf_corpus.manifest_structure_group': 'Structure du document',
 'pdf_corpus.manifest_unsaved': 'Modifications non enregistrées aux métadonnées du document',
 'pdf_corpus.manifest_no_changes': 'Aucune modification non enregistrée',
 'pdf_corpus.inherited_metadata_section': 'Métadonnées héritées du document',
 'pdf_corpus.inherited_metadata_help': 'Ces valeurs proviennent de la fiche du document. Modifiez les métadonnées du document ci-dessous pour changer la valeur par défaut des notices qui en héritent, ou remplacez volontairement un champ pour cette notice.',
 'pdf_corpus.override_value': 'Remplacer',
 'pdf_corpus.start_new_build': 'Démarrer une nouvelle construction',
 'pdf_corpus.collaborative_review_title': 'La révision humaine et l’enrichissement travaillent ensemble',
 'pdf_corpus.collaborative_review_active': 'Vous pouvez modifier cette notice maintenant. Les champs pris en charge par une personne ont priorité; l’enrichissement en arrière-plan ignorera ou préservera vos décisions.',
 'pdf_corpus.collaborative_review_settled': 'Cette notice est stabilisée pendant que l’enrichissement se poursuit pour les autres notices.',
 'pdf_corpus.document_metadata_live_help': 'Les métadonnées bibliographiques du document peuvent être corrigées pendant l’enrichissement. Les changements humains deviennent la référence pour les champs hérités; les changements structurels aux limites de pages attendent la fin du traitement en arrière-plan.',
 'pdf_corpus.start_concurrent_build': 'Démarrer une autre construction',
 'pdf_corpus.source_issue_help_v48': 'La couche de texte du PDF peut contenir des défauts d’extraction. Vous pouvez les corriger ici : inspectez la source, corrigez le texte révisé de la notice, puis marquez le problème de source comme résolu au moment d’enregistrer. Réextrayez le PDF seulement si la source est trop endommagée pour être corrigée de façon fiable.',
 'pdf_corpus.inspect_source': 'Inspecter la source',
 'pdf_corpus.correct_reviewed_text': 'Corriger le texte révisé',
 'pdf_corpus.source_resolution_step_1': 'Comparez le texte révisé avec le PDF et les blocs sources.',
 'pdf_corpus.source_resolution_step_2': 'Corrigez uniquement les erreurs d’extraction dans le texte révisé de la notice.',
 'pdf_corpus.source_resolution_step_3': 'Au moment d’enregistrer, choisissez « Marquer le problème de source comme résolu » lorsque le texte corrigé est fiable.',
 'pdf_corpus.document_metadata_dialog_help': 'Modifiez une seule fois les valeurs par défaut du document. Les notices en héritent, sauf lorsqu’elles comportent un remplacement humain explicite.',
 'pdf_corpus.initializing_workspace': 'Préparation de l’espace de travail des notices',
 'pdf_corpus.initialization_title': 'Construction de la base modifiable du corpus',
 'pdf_corpus.initialization_help': 'DerridAI analyse la structure du document et finalise les limites des notices. Dès que la segmentation est enregistrée, cette fenêtre se ferme et l’espace de révision des notices s’ouvre pendant que l’enrichissement des métadonnées se poursuit en arrière-plan.',
 'pdf_corpus.bulk_metadata_help_v48': 'Choisissez seulement les champs que vous voulez modifier. Les champs non sélectionnés ne sont jamais envoyés ni écrasés.',
 'pdf_corpus.bulk_group_identity': 'Identité et publication',
 'pdf_corpus.bulk_group_discourse': 'Discours et attribution',
 'pdf_corpus.bulk_group_indexing': 'Indexation sémantique',
 'pdf_corpus.bulk_apply_all': 'Appliquer à toutes les notices',
 'pdf_corpus.bulk_scope_description': '{selected} sélectionnée(s) · {total} notices au total',
 'pdf_corpus.bulk_search_fields': 'Rechercher des champs de métadonnées…',
 'pdf_corpus.bulk_list_hint': 'Valeurs séparées par des virgules ou des sauts de ligne',
 'pdf_corpus.bulk_no_fields': 'Aucun champ de métadonnées ne correspond à cette recherche.',
 'pdf_corpus.bulk_changes_count': '{count} champ(s) seront modifiés',
 'pdf_corpus.metadata_inline_help_v48': 'Révisez et modifiez directement les métadonnées qui seront écrites dans le JSONL. Les valeurs enregistrées par une personne restent prioritaires pendant l’enrichissement en arrière-plan.',
 'pdf_corpus.llm_suggestion_selected': 'Suggestion du LLM présélectionnée',
 'pdf_corpus.llm_suggestion_low_confidence': 'Suggestion du LLM — à réviser avant de la sélectionner',
 'pdf_corpus.confidence_not_reported': 'Indice de confiance non fourni',
 'pdf_corpus.confidence_percent': 'Confiance : {percent} %',
 'pdf_corpus.decision_saved_editable': 'Enregistré — vous pouvez continuer à modifier cette valeur',
 'pdf_corpus.choose_pdf_before_build': 'Choisissez ou chargez un PDF source avant de démarrer la construction du corpus.',
 'pdf_corpus.accept_clean_none_changed': 'Aucune notice n’a été modifiée. Les notices restantes exigent une révision ou ont déjà reçu une décision.',
 'pdf_corpus.document_metadata_defaults': 'Valeurs par défaut des métadonnées du document',
 'pdf_corpus.document_metadata_defaults_help': 'Modifiez les valeurs bibliographiques héritées dans un espace dédié. Les remplacements propres à une notice restent inchangés.',
 'pdf_corpus.human_reviewed': 'Révisé par une personne',
 'pdf_corpus.mark_text_reviewed': 'Marquer comme révisé',
 'pdf_corpus.text_save_hint': 'L’enregistrement confirme que vous avez révisé le texte de cette notice.',
 'pdf_corpus.save_and_mark_reviewed': 'Enregistrer et marquer comme révisé',
 'pdf_corpus.metadata_enrichment_pending': 'Enrichissement par LLM en attente',
 'pdf_corpus.metadata_enrichment_pending_help': 'Cette notice est modifiable maintenant, mais l’enrichissement de ses métadonnées par LLM n’est pas encore terminé. Les indices de confiance et les suggestions apparaîtront à mesure que chaque famille de métadonnées sera traitée.',
 'pdf_corpus.llm_suggestion_selected_short': 'Suggestion du LLM sélectionnée par défaut',
 'pdf_corpus.bulk_edit_eyebrow': 'Métadonnées des notices',
 'pdf_corpus.bulk_metadata_help_v481': 'Sélectionnez les champs à modifier, puis choisissez une valeur déjà présente dans le corpus ou saisissez-en une nouvelle. Les champs non sélectionnés restent inchangés.',
 'pdf_corpus.bulk_scope': 'Portée',
 'pdf_corpus.bulk_selected_records': 'Notices sélectionnées',
 'pdf_corpus.bulk_selected_count': '{count} sélectionnée(s)',
 'pdf_corpus.bulk_total_count': '{count} notices au total',
 'pdf_corpus.bulk_find_field': 'Trouver un champ',
 'pdf_corpus.bulk_value_placeholder': 'Choisissez une valeur existante ou saisissez-en une nouvelle',
 'pdf_corpus.bulk_existing_values': '{count} valeur(s) existante(s) offerte(s) pour la saisie semi-automatique',
 'pdf_corpus.metadata_streamlined_help': 'Les suggestions valides du LLM sont préremplies. Des règles déterministes règlent les relations évidentes; révisez les exceptions restantes et enregistrez seulement ce qui exige votre jugement.',
 'pdf_corpus.deterministic_suggestion': 'Règle déterministe',
 'pdf_corpus.constraint_non_primary_region': 'Ce type de région ne peut pas être du texte principal; « Texte principal » est donc réglé à Non.',
 'pdf_corpus.constraint_main_text_primary': 'Le texte principal fait partie du contenu substantiel; « Texte principal » est donc réglé à Oui.',
 'pdf_corpus.llm_suggestion_prefilled': 'Suggestion du LLM préremplie — vérifiez-la avant d’enregistrer',
 'pdf_corpus.text_cleanup_eyebrow': 'Texte révisé',
 'pdf_corpus.text_cleanup_title': 'Nettoyer le texte extrait',
 'pdf_corpus.text_cleanup_help': 'Prévisualisez un nettoyage réversible du bruit d’extraction courant. Le texte source extrait immuable n’est jamais modifié.',
 'pdf_corpus.cleanup_rules': 'Options de nettoyage',
 'pdf_corpus.cleanup_page_numbers': 'Retirer les numéros de page isolés',
 'pdf_corpus.cleanup_page_numbers_help': 'Retire les lignes qui contiennent seulement un numéro de page ou un numéro de page en chiffres romains.',
 'pdf_corpus.cleanup_repeated_lines': 'Retirer les en-têtes et pieds de page courts récurrents',
 'pdf_corpus.cleanup_repeated_lines_help': 'Retire les courtes lignes répétées dans plusieurs notices actuellement chargées, par exemple un titre courant de chapitre ou d’œuvre.',
 'pdf_corpus.cleanup_hyphenation': 'Réunir les mots coupés en fin de ligne',
 'pdf_corpus.cleanup_hyphenation_help': 'Réunit les mots séparés uniquement parce qu’une ligne se termine par un trait d’union.',
 'pdf_corpus.cleanup_whitespace': 'Normaliser les espaces issus de l’extraction',
 'pdf_corpus.cleanup_whitespace_help': 'Réduit les espaces et lignes vides excessifs sans modifier la provenance de la source.',
 'pdf_corpus.cleanup_change_count': '{count} modification(s) de nettoyage détectée(s)',
 'pdf_corpus.cleanup_removed_count': '{count} ligne(s) répétée(s) ou numéro(s) de page seraient retirés',
 'pdf_corpus.cleanup_before': 'Avant',
 'pdf_corpus.cleanup_after': 'Après',
 'pdf_corpus.cleanup_removed_lines': 'Lignes retirées',
 'pdf_corpus.cleanup_source_preserved': 'Le texte extrait d’origine demeure préservé aux fins d’audit et de comparaison.',
 'pdf_corpus.apply_cleanup': 'Appliquer au texte révisé',
 'pdf_corpus.clean_text': 'Nettoyer le texte',
 'pdf_corpus.cleanup_applied_draft': 'Le nettoyage a été appliqué au brouillon du texte révisé. Enregistrez-le pour le conserver.',
 'pdf_corpus.llm_suggestions_ready': '{count} suggestion(s) du LLM prête(s)',
 'pdf_corpus.llm_suggestions_ready_help': 'Les suggestions sont déjà remplies dans leurs contrôles. Confirmez-les une à une ou enregistrez toutes les suggestions actuelles en une seule fois.',
 'pdf_corpus.accept_all_suggestions': 'Enregistrer toutes les suggestions',
 'pdf_corpus.llm_suggestions_saved': '{count} suggestion(s) du LLM enregistrée(s) comme métadonnées confirmées par une personne.',
 'pdf_corpus.cleanup_paragraph_lines': 'Retirer les sauts de ligne inutiles',
 'pdf_corpus.cleanup_paragraph_lines_help': 'Réunit les retours à la ligne qui semblent provenir de la mise en page du PDF à l’intérieur des paragraphes, tout en préservant les titres, listes, citations et fins de phrase.',
 'pdf_corpus.cleanup_empty_lines': 'Réduire les lignes vides excédentaires',
 'pdf_corpus.cleanup_empty_lines_help': 'Réduit les séries de lignes vides tout en conservant une séparation de paragraphe.',
 'pdf_corpus.live_enrichment': 'Enrichissement en cours',
 'pdf_corpus.enrichment_profile': 'Profil d’enrichissement',
 'pdf_corpus.enrichment_profile_help': 'Le changement de profil s’applique aux nouvelles tâches de métadonnées. Les requêtes déjà en cours se terminent avec le modèle qui les a commencées.',
 'pdf_corpus.provider_history': 'Historique des profils',
 'pdf_corpus.profile_switched_after_records': 'après {count} notice(s) enrichie(s)',
 'pdf_corpus.profile_switched': 'Les nouvelles tâches de métadonnées utiliseront {profile}. Les requêtes déjà en cours se poursuivent sans changement.',
 'pdf_corpus.editorial_examples_used': 'Exemples confirmés par une personne réutilisés',
 'pdf_corpus.manifest_identity_help': 'Identifiez l’œuvre et les personnes responsables de cette édition.',
 'pdf_corpus.manifest_publication_help': 'Renseignements bibliographiques propres à l’édition utilisés par les métadonnées héritées et les citations.',
 'pdf_corpus.manifest_language_help': 'Les renseignements linguistiques servent aux citations, à la traduction et aux métadonnées du corpus.',
 'pdf_corpus.manifest_structure_help': 'Les limites des pages physiques du PDF aident à distinguer le texte principal des pages liminaires et finales.',
 'pdf_corpus.document_defaults': 'Valeurs par défaut du document',
 'pdf_corpus.document_defaults_title': 'Une seule modification, héritée de façon cohérente',
 'pdf_corpus.document_defaults_records': '{count} notices héritent des valeurs par défaut du document',
 'pdf_corpus.manifest_changes_count': '{count} modification(s) non enregistrée(s)',
 'pdf_corpus.manifest_propagation_preview': 'L’enregistrement met à jour les valeurs héritées pour un maximum de {count} notices; les remplacements explicites au niveau des notices demeurent inchangés.',
 'pdf_corpus.save_manifest_changes': 'Enregistrer les modifications du document',
 'pdf_corpus.llm_effectiveness_waiting': 'En attente des contributions du modèle',
 'pdf_corpus.llm_effectiveness_useful': '{count} champ(s) utile(s) fourni(s) par le modèle',
 'pdf_corpus.llm_effectiveness_none': 'Aucun champ utile fourni par le modèle pour l’instant',
 'pdf_corpus.llm_effectiveness_title': 'Efficacité de l’automatisation',
 'pdf_corpus.llm_effectiveness_summary': '{calls} appel(s) de famille · {minutes} min de temps modèle',
 'pdf_corpus.llm_effectiveness_help': 'Ces mesures évaluent ce que l’automatisation a réellement apporté, et non seulement si les requêtes se sont terminées.',
 'pdf_corpus.useful_fields_per_minute': 'champs utiles/min',

 'pdf_corpus.auto_clean_all_records': 'Nettoyer tous les textes des notices avant l’enrichissement',
 'pdf_corpus.auto_clean_all_records_help': 'Recommandé. Retire les en-têtes répétés et les numéros de page, répare les retours de ligne dans la prose, réduit les lignes vides et retire les artéfacts OCR évidents tout en préservant le texte extrait immuable aux fins d’audit.',
 'pdf_corpus.cleanup_ocr_artifacts': 'Retirer les artéfacts OCR évidents',
 'pdf_corpus.cleanup_ocr_artifacts_help': 'Retire les caractères de remplacement, le bruit de caractères de contrôle, les séries de symboles parasites et les autres débris OCR détectés avec grande confiance.',
 'pdf_corpus.focus_navigation': 'Navigation de la révision ciblée',
 'pdf_corpus.corpus_builder': 'Générateur de corpus',
 'pdf_corpus.previous_record': 'Notice précédente',
 'pdf_corpus.next_record': 'Notice suivante',
 'pdf_corpus.audit_trail': 'Piste d’audit',
 'pdf_corpus.revision_history': 'Historique des révisions',
 'pdf_corpus.history_auto_cleanup': 'Nettoyage automatique du texte',
 'pdf_corpus.history_text_edit': 'Modification du texte révisé',
 'pdf_corpus.history_diff_available': 'Différence textuelle enregistrée',
 'pdf_corpus.history_metadata_change': 'Métadonnée : {field}',
 'pdf_corpus.history_source.human': 'Confirmation humaine',
 'pdf_corpus.history_source.human_override': 'Remplacement humain',
 'pdf_corpus.history_source.human_bulk': 'Modification humaine en lot',
 'pdf_corpus.history_source.human_bulk_override': 'Remplacement humain en lot',
 'pdf_corpus.history_source.deterministic_constraint': 'Contrainte déterministe',
 'pdf_corpus.no_revision_history': 'Aucune révision humaine ni aucun nettoyage n’a encore été enregistré.',
 'pdf_corpus.cleanup_pre_enrichment_summary': 'Nettoyage de {records} notice(s) avant l’enrichissement des métadonnées · {changes} modification(s) · {removed} ligne(s) répétée(s) ou parasite(s) retirée(s).',
 'pdf_corpus.adaptive_routing': 'Routage adaptatif',
 'pdf_corpus.adaptive_routing_help': 'En mode rapide, DerridAI peut suspendre une famille de métadonnées à faible rendement lorsque les résultats de cette construction montrent qu’elle n’aide pas. Les relances explicites restent possibles.',

 'pdf_corpus.automatic_text_cleanup': 'Nettoyage automatique du texte',
 'pdf_corpus.cleanup_disabled_summary': 'Le nettoyage automatique était désactivé pour cette construction. Le nettoyage au niveau de chaque notice demeure disponible pendant la révision.',
 'pdf_corpus.cleanup_applied': 'Nettoyage appliqué',
 'pdf_corpus.cleanup_not_applied': 'Non appliqué',
 'pdf_corpus.readiness_blocker.required_document_metadata': 'Des métadonnées requises du document sont manquantes',
 'pdf_corpus.calls': 'appels',
 'pdf_corpus.proposed_fields': 'proposés',
 'pdf_corpus.corrected': 'corrigés',
 'pdf_corpus.workflow.load': 'Charger le PDF',
 'pdf_corpus.workflow.configure': 'Configurer',
 'pdf_corpus.workflow.initialize': 'Initialiser',
 'pdf_corpus.workflow.segment': 'Segmenter',
 'pdf_corpus.workflow.resolve': 'Résoudre les exceptions',
}
