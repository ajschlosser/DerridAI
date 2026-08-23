# CONFIGURATION
EMBEDDING_MODEL   = "bge-m3:latest" #"nomic-embed-text"
CHAT_MODEL        = "gpt-oss:20b"
CHAT_TEMPERATURE  = 0.4
OLLAMA_BASE_URL   = "http://localhost:11434"

DB_PATH           = "./chroma_db_local-tuned6_multilang"
SOURCE_TEXT       = "./data/derrida6_multi.jsonl"

BATCH_SIZE        = 1000          # Prevents Ollama tokenizer OOM crashes
K_VALUE           = 15
FETCH_K_VALUE     = 500
LAMBDA_MULT_VALUE = 0.7           # Lower = more diversity; higher = more query relevance

keys = {
  "en_us": {
    "abolition": [
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "animality": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "aporia": [
      "derrida-aporias-1993-dutoit"
    ],
    "archive": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "autoimmunity": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "beast": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "border": [
      "derrida-aporias-1993-dutoit"
    ],
    "death": [
      "derrida-aporias-1993-dutoit"
    ],
    "death penalty": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "deconstruction": [
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al",
      "derrida-positions-1972"
    ],
    "democracy": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "democracy to come": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "difference": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "différance": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "dissemination": [
      "derrida-la_dissemination-1972"
    ],
    "ear": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "economy": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money"
    ],
    "event": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "fraternity": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "friendship": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-the_work_of_mourning-2001"
    ],
    "genesis": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-the_problem_of_genesis_in_husserls_philosophy"
    ],
    "gift": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money"
    ],
    "hauntology": [
      "derrida-spectres_de_marx-1993"
    ],
    "Heidegger": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987",
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "historicity": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "hospitality": [
      "derrida-adieu_a_emmanuel_levinas-1997"
    ],
    "Husserl": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-the_problem_of_genesis_in_husserls_philosophy"
    ],
    "ideal objectivity": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "inheritance": [
      "derrida-spectres_de_marx-1993"
    ],
    "institution": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "invention": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "iterability": [
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "language": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "listening": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "monolingualism": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "mourning": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-glas-1974",
      "derrida-the_work_of_mourning-2001"
    ],
    "origin": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "other": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "pharmakon": [
      "derrida-la_dissemination-1972"
    ],
    "philosophy": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "poem": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "politics": [
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "presence": [
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "profession": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "proper name": [
      "derrida-glas-1974"
    ],
    "prosthesis": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "question": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987"
    ],
    "repetition": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "responsibility": [
      "derrida-adieu_a_emmanuel_levinas-1997"
    ],
    "right": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "sign": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "signature": [
      "derrida-glas-1974",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "solitude": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "sovereignty": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "specter": [
      "derrida-spectres_de_marx-1993"
    ],
    "spectrality": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "spirit": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987"
    ],
    "structure": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "style": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "supplement": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_dissemination-1972",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "survival": [
      "derrida-the_work_of_mourning-2001"
    ],
    "technics": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "television": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "temporality": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-the_problem_of_genesis_in_husserls_philosophy"
    ],
    "theologico-political": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-the_death_penalty_volume_i-2014-kamuf"
    ],
    "time": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money"
    ],
    "trace": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "truth": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "unconditionality": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "university": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "voice": [
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "woman": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "world": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "writing": [
      "derrida-de_la_grammatologie-1967",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al",
      "derrida-positions-1972",
      "derrida-signature_derrida-2013-multiple_translators",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ]
  },
  "fr_fr": {
    "abolition": [
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "amitié": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-the_work_of_mourning-2001"
    ],
    "animalité": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "aporie": [
      "derrida-aporias-1993-dutoit"
    ],
    "archive": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "auto-immunité": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "autre": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "bête": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "déconstruction": [
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al",
      "derrida-positions-1972"
    ],
    "démocratie": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "démocratie à venir": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "deuil": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-glas-1974",
      "derrida-the_work_of_mourning-2001"
    ],
    "différance": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "différence": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "dissémination": [
      "derrida-la_dissemination-1972"
    ],
    "don": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money"
    ],
    "droit": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "économie": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money"
    ],
    "écriture": [
      "derrida-de_la_grammatologie-1967",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al",
      "derrida-positions-1972",
      "derrida-signature_derrida-2013-multiple_translators",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "écoute": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "esprit": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987"
    ],
    "événement": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "femme": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "fraternité": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "frontière": [
      "derrida-aporias-1993-dutoit"
    ],
    "genèse": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-the_problem_of_genesis_in_husserls_philosophy"
    ],
    "hantologie": [
      "derrida-spectres_de_marx-1993"
    ],
    "Heidegger": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987",
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "héritage": [
      "derrida-spectres_de_marx-1993"
    ],
    "historicité": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "hospitalité": [
      "derrida-adieu_a_emmanuel_levinas-1997"
    ],
    "Husserl": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-the_problem_of_genesis_in_husserls_philosophy"
    ],
    "inconditionnalité": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "institution": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "invention": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "itérabilité": [
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "langage": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "langue": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "monde": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "monolinguisme": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "mort": [
      "derrida-aporias-1993-dutoit"
    ],
    "nom propre": [
      "derrida-glas-1974"
    ],
    "objectivité idéale": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "oreille": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "origine": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "peine de mort": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "pharmakon": [
      "derrida-la_dissemination-1972"
    ],
    "philosophie": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "poème": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "politique": [
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "présence": [
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "profession": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "prothèse": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "question": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987"
    ],
    "répétition": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "responsabilité": [
      "derrida-adieu_a_emmanuel_levinas-1997"
    ],
    "signature": [
      "derrida-glas-1974",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "signe": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "solitude": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "souveraineté": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "spectralité": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "spectre": [
      "derrida-spectres_de_marx-1993"
    ],
    "structure": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "style": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "supplément": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_dissemination-1972",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "survie": [
      "derrida-the_work_of_mourning-2001"
    ],
    "technique": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "télévision": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "temporalité": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-the_problem_of_genesis_in_husserls_philosophy"
    ],
    "temps": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money"
    ],
    "théologico-politique": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-the_death_penalty_volume_i-2014-kamuf"
    ],
    "trace": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "université": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "vérité": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "voix": [
      "derrida-la_voix_et_le_phenomene-1967"
    ]
  }
}