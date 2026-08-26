# CONFIGURATION
EMBEDDING_MODEL   = "bge-m3:latest" #"nomic-embed-text"
CHAT_MODEL        = "phi4:14b" # great
#CHAT_MODEL        = "qwen3:4b-instruct" # not bad
#CHAT_MODEL        = "qwen2.5:7b-instruct" # not great
#CHAT_MODEL        = "mistral-small3.1:24b" # bad
#CHAT_MODEL        = "gemma3:12b" # unknown quality
CHAT_TEMPERATURE  = 0.4
OLLAMA_BASE_URL   = "http://localhost:11434"

DB_PATH           = "./chroma_db_local7"
SOURCE_TEXT       = "./data/derrida7_ids.jsonl"

BATCH_SIZE        = 1000          # Prevents Ollama tokenizer OOM crashes
K_VALUE           = 64
FETCH_K_VALUE     = 500
LAMBDA_MULT_VALUE = 0.7           # Lower = more diversity; higher = more query relevance
RERANK_COUNT      = 8 #int(K_VALUE // 6)

RESPONSE_MIN_SENTENCES = 150
RESPONSE_MAX_SENTENCES = 500

keys = {
  "en_us": {
    "abolition": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "abolitionism": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "Abraham": [
      "derrida-the_gift_of_death-1995"
    ],
    "actuality": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "aesthetics": [
      "derrida-the_truth_in_painting-1987",
      "derrida-acts_of_literature-1992"
    ],
    "alterity": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-of_hospitality-2000",
      "derrida-writing_and_difference-1978",
      "derrida-the_gift_of_death-1995"
    ],
    "anarchivic": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "aneconomic": [
      "derrida-given_time_i_counterfeit_money"
    ],
    "aneconomy": [
      "derrida-given_time_i_counterfeit_money"
    ],
    "animal": [
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "animality": [
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "aporia": [
      "derrida-aporias-1993-dutoit",
      "derrida-the_gift_of_death-1995",
      "derrida-of_hospitality-2000",
      "derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes"
    ],
    "aporias": [
      "derrida-aporias-1993-dutoit"
    ],
    "arche-writing": [
      "derrida-de_la_grammatologie-1967"
    ],
    "archive": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-cinders-2014-lukacher"
    ],
    "archiviolithic": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "arrivant": [
      "derrida-aporias-1993-dutoit",
      "derrida-of_hospitality-2000",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "art": [
      "derrida-the_truth_in_painting-1987"
    ],
    "Artaud": [
      "derrida-writing_and_difference-1978",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "artifactuality": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "ash": [
      "derrida-cinders-2014-lukacher"
    ],
    "Austin": [
      "derrida-limited_inc-1988",
      "derrida-margins_of_philosophy-1982"
    ],
    "auto-affection": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "auto-immunity": [
      "derrida-acts_of_religion-2002"
    ],
    "autoaffection": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "autobiography": [
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985",
      "derrida-glas-1986"
    ],
    "autochthony": [
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "autoimmune": [
      "derrida-acts_of_religion-2002"
    ],
    "autoimmunity": [
      "derrida-acts_of_religion-2002",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "Bataille": [
      "derrida-writing_and_difference-1978",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "beast": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "Blanchot": [
      "derrida-acts_of_literature-1992",
      "derrida-writing_and_difference-1978"
    ],
    "border": [
      "derrida-aporias-1993-dutoit",
      "derrida-of_hospitality-2000"
    ],
    "brotherhood": [
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "castration": [
      "derrida-glas-1986",
      "derrida-glas-1974"
    ],
    "cat": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "Celan": [
      "derrida-sovereignties_in_question-2005",
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "chora": [
      "derrida-acts_of_religion-2002"
    ],
    "cinder": [
      "derrida-cinders-2014-lukacher"
    ],
    "citation": [
      "derrida-limited_inc-1988"
    ],
    "colonialism": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "communication": [
      "derrida-limited_inc-1988",
      "derrida-margins_of_philosophy-1982"
    ],
    "Condillac": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "context": [
      "derrida-margins_of_philosophy-1982",
      "derrida-limited_inc-1988"
    ],
    "cosmopolitanism": [
      "derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes",
      "derrida-of_hospitality-2000"
    ],
    "cruelty": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "death": [
      "derrida-aporias-1993-dutoit",
      "derrida-the_gift_of_death-1995",
      "derrida-the_work_of_mourning-2001",
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg",
      "derrida-life_death-2020-brault_naas"
    ],
    "debt": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "decision": [
      "derrida-the_gift_of_death-1995",
      "derrida-aporias-1993-dutoit",
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "deconstruction": [
      "derrida-writing_and_difference-1978",
      "derrida-margins_of_philosophy-1982",
      "derrida-limited_inc-1988",
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "democracy": [
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "democracy-to-come": [
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "destination": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "destinerrance": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "destinerrancy": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "dialectic": [
      "derrida-glas-1986",
      "derrida-glas-1974"
    ],
    "differance": [
      "derrida-margins_of_philosophy-1982",
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "difference": [
      "derrida-writing_and_difference-1978",
      "derrida-margins_of_philosophy-1982"
    ],
    "différance": [
      "derrida-margins_of_philosophy-1982",
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-writing_and_difference-1978"
    ],
    "dissemination": [
      "derrida-dissemination-1981",
      "derrida-la_dissemination-1972"
    ],
    "economy": [
      "derrida-given_time_i_counterfeit_money"
    ],
    "education": [
      "derrida-whos_afraid_of_philosophy_right_to_philosophy_1-2002",
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-l_universite_sans_condition-2001"
    ],
    "empiricism": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "enemy": [
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "enlightenment": [
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "enmity": [
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "ethics": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-the_gift_of_death-1995",
      "derrida-of_hospitality-2000",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "eulogy": [
      "derrida-the_work_of_mourning-2001"
    ],
    "event": [
      "derrida-limited_inc-1988",
      "derrida-a_certain_impossible_possibility_of_saying_the_event-2007-walker",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "exception": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "execution": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "fable": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "faith": [
      "derrida-acts_of_religion-2002",
      "derrida-the_gift_of_death-1995"
    ],
    "family": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "fiction": [
      "derrida-acts_of_literature-1992"
    ],
    "filiation": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "fire": [
      "derrida-cinders-2014-lukacher",
      "derrida-foi_et_savoir-2000"
    ],
    "foreigner": [
      "derrida-of_hospitality-2000"
    ],
    "forgiveness": [
      "derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes",
      "derrida-acts_of_religion-2002"
    ],
    "fort-da": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "Foucault": [
      "derrida-writing_and_difference-1978",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "frame": [
      "derrida-the_truth_in_painting-1987"
    ],
    "framing": [
      "derrida-the_truth_in_painting-1987"
    ],
    "fraternity": [
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "Freud": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "friendship": [
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-the_work_of_mourning-2001"
    ],
    "gaze": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "Geist": [
      "derrida-of_spirit_heidegger_and_the_question-1989"
    ],
    "gender": [
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "genesis": [
      "derrida-the_problem_of_genesis_in_husserls_philosophy",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ],
    "Genet": [
      "derrida-glas-1986",
      "derrida-glas-1974"
    ],
    "genre": [
      "derrida-acts_of_literature-1992",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "geometry": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "gift": [
      "derrida-given_time_i_counterfeit_money",
      "derrida-the_gift_of_death-1995"
    ],
    "globalization": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "gram": [
      "derrida-margins_of_philosophy-1982",
      "derrida-dissemination-1981"
    ],
    "guest": [
      "derrida-of_hospitality-2000"
    ],
    "hauntological": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "hauntology": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-spectres_de_marx-1993"
    ],
    "hearing-oneself-speak": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "Hegel": [
      "derrida-glas-1986",
      "derrida-writing_and_difference-1978",
      "derrida-margins_of_philosophy-1982"
    ],
    "Heidegger": [
      "derrida-of_spirit_heidegger_and_the_question-1989",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "historicity": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ],
    "hospitality": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-of_hospitality-2000",
      "derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "host": [
      "derrida-of_hospitality-2000"
    ],
    "hostipitality": [
      "derrida-of_hospitality-2000"
    ],
    "human": [
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "Husserl": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-the_problem_of_genesis_in_husserls_philosophy",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ],
    "hymen": [
      "derrida-dissemination-1981",
      "derrida-la_dissemination-1972"
    ],
    "hypomnesis": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "identity": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "idiom": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "impossible": [
      "derrida-aporias-1993-dutoit",
      "derrida-given_time_i_counterfeit_money",
      "derrida-of_hospitality-2000",
      "derrida-a_certain_impossible_possibility_of_saying_the_event-2007-walker"
    ],
    "inheritance": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "institution": [
      "derrida-whos_afraid_of_philosophy_right_to_philosophy_1-2002",
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-l_universite_sans_condition-2001"
    ],
    "interviews": [
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "invention": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "ipseity": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "island": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "iterability": [
      "derrida-margins_of_philosophy-1982",
      "derrida-limited_inc-1988",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "iterable": [
      "derrida-margins_of_philosophy-1982",
      "derrida-limited_inc-1988"
    ],
    "justice": [
      "derrida-acts_of_religion-2002",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_gift_of_death-1995"
    ],
    "Kant": [
      "derrida-the_truth_in_painting-1987"
    ],
    "khora": [
      "derrida-acts_of_religion-2002"
    ],
    "knowledge": [
      "derrida-acts_of_religion-2002"
    ],
    "Lacan": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "language": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998",
      "derrida-the_archeology_of_the_frivolous_reading_condillac",
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985"
    ],
    "law": [
      "derrida-acts_of_literature-1992",
      "derrida-acts_of_religion-2002",
      "derrida-of_hospitality-2000",
      "derrida-whos_afraid_of_philosophy_right_to_philosophy_1-2002",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-the_death_penalty_volume_i-2014-kamuf"
    ],
    "Levinas": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-writing_and_difference-1978"
    ],
    "liberalism": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "life": [
      "derrida-life_death-2020-brault_naas",
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-cinders-2014-lukacher"
    ],
    "limit": [
      "derrida-aporias-1993-dutoit",
      "derrida-of_hospitality-2000"
    ],
    "literature": [
      "derrida-acts_of_literature-1992",
      "derrida-writing_and_difference-1978",
      "derrida-dissemination-1981"
    ],
    "logo-centric": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "logo-centrism": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "logocentric": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "logocentrism": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "Mallarmé": [
      "derrida-dissemination-1981",
      "derrida-la_dissemination-1972"
    ],
    "Marx": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-spectres_de_marx-1993"
    ],
    "media": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek",
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "memory": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-the_work_of_mourning-2001",
      "derrida-cinders-2014-lukacher"
    ],
    "messianic": [
      "derrida-acts_of_religion-2002",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "messianicity": [
      "derrida-acts_of_religion-2002",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "messianism": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-acts_of_religion-2002"
    ],
    "metaphor": [
      "derrida-margins_of_philosophy-1982"
    ],
    "metaphysics": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982",
      "derrida-writing_and_difference-1978",
      "derrida-of_spirit_heidegger_and_the_question-1989"
    ],
    "mondialization": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "monolingualism": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998",
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "mourning": [
      "derrida-the_work_of_mourning-2001",
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-signature_derrida-2013-multiple_translators",
      "derrida-cinders-2014-lukacher"
    ],
    "nakedness": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "Nietzsche": [
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985",
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "origin": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction",
      "derrida-the_problem_of_genesis_in_husserls_philosophy",
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "other": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-of_hospitality-2000",
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998",
      "derrida-the_gift_of_death-1995"
    ],
    "otobiographies": [
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985"
    ],
    "otobiography": [
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985",
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "painting": [
      "derrida-the_truth_in_painting-1987"
    ],
    "parergon": [
      "derrida-the_truth_in_painting-1987"
    ],
    "passage": [
      "derrida-aporias-1993-dutoit"
    ],
    "performative": [
      "derrida-limited_inc-1988"
    ],
    "perhaps": [
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallo-centric": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallo-centrism": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallo-logocentric": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallo-logocentrism": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallocentric": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallocentrism": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallogocentric": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "phallogocentrism": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "pharmacon": [
      "derrida-dissemination-1981"
    ],
    "pharmakon": [
      "derrida-dissemination-1981",
      "derrida-la_dissemination-1972"
    ],
    "phenomenology": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-the_problem_of_genesis_in_husserls_philosophy",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ],
    "philosophy": [
      "derrida-whos_afraid_of_philosophy_right_to_philosophy_1-2002",
      "derrida-margins_of_philosophy-1982"
    ],
    "phono-centric": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "phono-centrism": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "phonocentric": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "phonocentrism": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-de_la_grammatologie-1967"
    ],
    "Plato": [
      "derrida-dissemination-1981",
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "poem": [
      "derrida-sovereignties_in_question-2005",
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "poetry": [
      "derrida-acts_of_literature-1992",
      "derrida-sovereignties_in_question-2005"
    ],
    "politics": [
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "possibility": [
      "derrida-a_certain_impossible_possibility_of_saying_the_event-2007-walker",
      "derrida-aporias-1993-dutoit",
      "derrida-the_gift_of_death-1995"
    ],
    "postal": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "postcard": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "presence": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "promise": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "prosthesis": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998",
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "psychoanalysis": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "punishment": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "reaction": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "reason": [
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "religion": [
      "derrida-acts_of_religion-2002",
      "derrida-the_gift_of_death-1995"
    ],
    "remains": [
      "derrida-cinders-2014-lukacher",
      "derrida-glas-1986",
      "derrida-dissemination-1981"
    ],
    "response": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "responsibility": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-the_gift_of_death-1995",
      "derrida-acts_of_religion-2002",
      "derrida-of_hospitality-2000"
    ],
    "restitution": [
      "derrida-the_truth_in_painting-1987"
    ],
    "Rousseau": [
      "derrida-de_la_grammatologie-1967"
    ],
    "sacrifice": [
      "derrida-the_gift_of_death-1995",
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-acts_of_religion-2002"
    ],
    "Saussure": [
      "derrida-signature_derrida-2013-multiple_translators",
      "derrida-de_la_grammatologie-1967"
    ],
    "Schmitt": [
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "Searle": [
      "derrida-limited_inc-1988"
    ],
    "secret": [
      "derrida-the_gift_of_death-1995",
      "derrida-acts_of_literature-1992",
      "derrida-acts_of_religion-2002"
    ],
    "sexuality": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins",
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "shame": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "sign": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac",
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "signature": [
      "derrida-margins_of_philosophy-1982",
      "derrida-limited_inc-1988",
      "derrida-glas-1986",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "solitude": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "sovereignty": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "spacing": [
      "derrida-margins_of_philosophy-1982"
    ],
    "specter": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-cinders-2014-lukacher"
    ],
    "spectrality": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "spectre": [
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "speech": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982"
    ],
    "speech-act": [
      "derrida-limited_inc-1988"
    ],
    "spirit": [
      "derrida-of_spirit_heidegger_and_the_question-1989",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "state": [
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "stranger": [
      "derrida-of_hospitality-2000"
    ],
    "structuralism": [
      "derrida-writing_and_difference-1978"
    ],
    "structure": [
      "derrida-writing_and_difference-1978"
    ],
    "supplement": [
      "derrida-dissemination-1981",
      "derrida-de_la_grammatologie-1967"
    ],
    "survival": [
      "derrida-the_work_of_mourning-2001"
    ],
    "teaching": [
      "derrida-whos_afraid_of_philosophy_right_to_philosophy_1-2002"
    ],
    "technics": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "technology": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek",
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "telepathy": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987",
      "derrida-cinders-2014-lukacher"
    ],
    "teletechnologies": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "teletechnology": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "television": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "temporality": [
      "derrida-the_problem_of_genesis_in_husserls_philosophy",
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982",
      "derrida-given_time_i_counterfeit_money"
    ],
    "terrorism": [
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "testimony": [
      "derrida-acts_of_religion-2002"
    ],
    "theologico-political": [
      "derrida-the_death_penalty_volume_i-2014-kamuf",
      "derrida-the_death_penalty_volume_ii-2017-rottenberg"
    ],
    "time": [
      "derrida-given_time_i_counterfeit_money",
      "derrida-margins_of_philosophy-1982",
      "derrida-life_death-2020-brault_naas",
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973"
    ],
    "to-come": [
      "derrida-acts_of_religion-2002",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "trace": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-margins_of_philosophy-1982",
      "derrida-cinders-2014-lukacher"
    ],
    "tradition": [
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ],
    "transference": [
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985"
    ],
    "translation": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998",
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985",
      "derrida-signature_derrida-2013-multiple_translators",
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "truth": [
      "derrida-the_truth_in_painting-1987"
    ],
    "tympanum": [
      "derrida-margins_of_philosophy-1982"
    ],
    "unconditionality": [
      "derrida-of_hospitality-2000"
    ],
    "undecidability": [
      "derrida-dissemination-1981",
      "derrida-aporias-1993-dutoit",
      "derrida-the_gift_of_death-1995",
      "derrida-of_hospitality-2000"
    ],
    "undecidable": [
      "derrida-dissemination-1981"
    ],
    "university": [
      "derrida-whos_afraid_of_philosophy_right_to_philosophy_1-2002",
      "derrida-l_universite_sans_condition-2001",
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "untranslatability": [
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998",
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985"
    ],
    "violence": [
      "derrida-writing_and_difference-1978"
    ],
    "voice": [
      "derrida-speech_and_phenomena_and_other_essays_on_husserls_theory_of_signs-1973",
      "derrida-cinders-2014-lukacher"
    ],
    "war": [
      "derrida-rogues_two_essays_on_reason-2005-brault-naas",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "welcome": [
      "derrida-adieu_to_emmanuel_levinas-1999",
      "derrida-of_hospitality-2000"
    ],
    "wolf": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "woman": [
      "derrida-glas-1986",
      "derrida-the_politics_of_friendship-2005-collins"
    ],
    "world": [
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington",
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "writing": [
      "derrida-writing_and_difference-1978",
      "derrida-dissemination-1981",
      "derrida-margins_of_philosophy-1982",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ]
  },
  "fr_fr": {
    "abolition": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "abolitionnisme": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "accueil": [
      "derrida-adieu_a_emmanuel_levinas-1997"
    ],
    "acte-de-langage": [
      "derrida-limited_inc-1988"
    ],
    "altérité": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-psyche_inventions_de_l_autre-1987",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "amitié": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "animal": [
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "animalité": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-signature_derrida-2013-multiple_translators",
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "anéconomie": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991"
    ],
    "aporie": [
      "derrida-aporias-1993-dutoit"
    ],
    "apories": [
      "derrida-aporias-1993-dutoit"
    ],
    "appartenance": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "archi-écriture": [
      "derrida-de_la_grammatologie-1967",
      "derrida-positions-1972"
    ],
    "archive": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "archiécriture": [
      "derrida-de_la_grammatologie-1967"
    ],
    "arrivant": [
      "derrida-spectres_de_marx-1993",
      "derrida-aporias-1993-dutoit"
    ],
    "Artaud": [
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-writing_and_difference-1978"
    ],
    "Austin": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-limited_inc-1988"
    ],
    "auto-affection": [
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "auto-immunité": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-foi_et_savoir-2000"
    ],
    "autoaffection": [
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "autobiographie": [
      "derrida-glas-1974",
      "derrida-glas-1986"
    ],
    "autochtonie": [
      "derrida-politiques_de_l_amitie-1994"
    ],
    "autoimmune": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "autoimmunité": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "autre": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-psyche_inventions_de_l_autre-1987",
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "Bataille": [
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-writing_and_difference-1978"
    ],
    "Blanchot": [
      "derrida-parages-1986",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "bête": [
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "cadre": [
      "derrida-the_truth_in_painting-1987"
    ],
    "castration": [
      "derrida-glas-1974",
      "derrida-glas-1986"
    ],
    "Celan": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-sovereignties_in_question-2005"
    ],
    "cendre": [
      "derrida-cinders-2014-lukacher"
    ],
    "citation": [
      "derrida-limited_inc-1988"
    ],
    "colonialisme": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "communication": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-limited_inc-1988"
    ],
    "Condillac": [
      "derrida-the_archeology_of_the_frivolous_reading_condillac"
    ],
    "contexte": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-limited_inc-1988"
    ],
    "cosmopolitisme": [
      "derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes"
    ],
    "cruauté": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "dette": [
      "derrida-spectres_de_marx-1993"
    ],
    "deuil": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-spectres_de_marx-1993"
    ],
    "dialectique": [
      "derrida-glas-1974",
      "derrida-glas-1986"
    ],
    "dialogue": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "differance": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-de_la_grammatologie-1967"
    ],
    "différance": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-de_la_grammatologie-1967",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "différence": [
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-positions-1972",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "dissémination": [
      "derrida-la_dissemination-1972",
      "derrida-dissemination-1981"
    ],
    "distance": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "don": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-given_time_i_counterfeit_money",
      "derrida-donner_la_mort-1999"
    ],
    "droit": [
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-seminaire_la_peine_de_mort_volume_i-2012"
    ],
    "décision": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "déconstruction": [
      "derrida-de_la_grammatologie-1967",
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "démocratie": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-spectres_de_marx-1993"
    ],
    "démocratie-à-venir": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-spectres_de_marx-1993"
    ],
    "ennemi": [
      "derrida-politiques_de_l_amitie-1994"
    ],
    "enseignement": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "entendre": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "entretiens": [
      "derrida-points_interviews_1974_1994-1995-kamuf_et_al"
    ],
    "espacement": [
      "derrida-de_la_grammatologie-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "esprit": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "esthétique": [
      "derrida-the_truth_in_painting-1987"
    ],
    "ethnocentrisme": [
      "derrida-de_la_grammatologie-1967"
    ],
    "exception": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "exécution": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "famille": [
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "femme": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "feu": [
      "derrida-foi_et_savoir-2000",
      "derrida-cinders-2014-lukacher"
    ],
    "filiation": [
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "foi": [
      "derrida-foi_et_savoir-2000",
      "derrida-acts_of_religion-2002"
    ],
    "Foucault": [
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-writing_and_difference-1978"
    ],
    "fraternité": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "Freud": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "frontière": [
      "derrida-aporias-1993-dutoit"
    ],
    "frère": [
      "derrida-politiques_de_l_amitie-1994"
    ],
    "Gadamer": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "Geist": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987"
    ],
    "Genet": [
      "derrida-glas-1974",
      "derrida-glas-1986"
    ],
    "genre": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "genèse": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "Geschlecht": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "globalisation": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "grammatologie": [
      "derrida-de_la_grammatologie-1967"
    ],
    "gramme": [
      "derrida-de_la_grammatologie-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-la_dissemination-1972"
    ],
    "guerre": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington",
      "derrida-the_beast_and_the_sovereign_volume_ii-2011-bennington"
    ],
    "géométrie": [
      "husserl-l_origine_de_la_geometrie-1962-derrida",
      "derrida-edmund_husserls_origin_of_geometry_an_introduction"
    ],
    "hantologie": [
      "derrida-spectres_de_marx-1993",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "hantologique": [
      "derrida-spectres_de_marx-1993"
    ],
    "Hegel": [
      "derrida-glas-1974",
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "Heidegger": [
      "derrida-de_l_esprit_heidegger_et_la_question-1987",
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "historicité": [
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "hospitalité": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "humain": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-the_animal_that_therefore_i_am-2008",
      "derrida-the_beast_and_the_sovereign_volume_1-2009-bennington"
    ],
    "humanités": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "Husserl": [
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "hymen": [
      "derrida-la_dissemination-1972",
      "derrida-dissemination-1981"
    ],
    "héritage": [
      "derrida-spectres_de_marx-1993"
    ],
    "identité": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "idiome": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "impossible": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-aporias-1993-dutoit",
      "derrida-a_certain_impossible_possibility_of_saying_the_event-2007-walker",
      "derrida-of_hospitality-2000"
    ],
    "inconditionnalité": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "indécidabilité": [
      "derrida-la_dissemination-1972",
      "derrida-aporias-1993-dutoit",
      "derrida-donner_la_mort-1999",
      "derrida-of_hospitality-2000"
    ],
    "indécidable": [
      "derrida-la_dissemination-1972"
    ],
    "inimitié": [
      "derrida-politiques_de_l_amitie-1994"
    ],
    "institution": [
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-l_universite_sans_condition-2001"
    ],
    "interruption": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "intraduisibilité": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "invention": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "ipséité": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "itérabilité": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-limited_inc-1988",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "itérable": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-limited_inc-1988"
    ],
    "justice": [
      "derrida-spectres_de_marx-1993",
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-politiques_de_l_amitie-1994",
      "derrida-seminaire_la_peine_de_mort_volume_i-2012"
    ],
    "Lacan": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "langage": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "langue": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-de_la_grammatologie-1967"
    ],
    "Levinas": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "liberalisme": [
      "derrida-spectres_de_marx-1993"
    ],
    "limite": [
      "derrida-aporias-1993-dutoit"
    ],
    "littérature": [
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-la_dissemination-1972",
      "derrida-parages-1986",
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "logo-centrique": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "logo-centrisme": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "logocentrique": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "logocentrisme": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "loi": [
      "derrida-du_droit_a_la_philosophie-1990"
    ],
    "lumières": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "Mallarmé": [
      "derrida-la_dissemination-1972",
      "derrida-dissemination-1981"
    ],
    "Marx": [
      "derrida-spectres_de_marx-1993",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006"
    ],
    "messianicité": [
      "derrida-spectres_de_marx-1993",
      "derrida-foi_et_savoir-2000"
    ],
    "messianique": [
      "derrida-spectres_de_marx-1993"
    ],
    "messianisme": [
      "derrida-spectres_de_marx-1993",
      "derrida-foi_et_savoir-2000"
    ],
    "mondialisation": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "monolinguisme": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "mort": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "médias": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek",
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "mémoire": [
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "métaphore": [
      "derrida-marges_de_la_philosophie-1972"
    ],
    "métaphysique": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-positions-1972",
      "derrida-de_l_esprit_heidegger_et_la_question-1987"
    ],
    "nationalisme": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "nationalité": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "Nietzsche": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-points_de_suspension-1992"
    ],
    "origine": [
      "husserl-l_origine_de_la_geometrie-1962-derrida",
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-de_la_grammatologie-1967",
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996"
    ],
    "otobiographie": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-the_ear_of_the_other_otobiography_transference_translation-1985"
    ],
    "pardon": [
      "derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes"
    ],
    "parergon": [
      "derrida-the_truth_in_painting-1987"
    ],
    "parole": [
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-de_la_grammatologie-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "passage": [
      "derrida-aporias-1993-dutoit"
    ],
    "peine": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "peinture": [
      "derrida-the_truth_in_painting-1987"
    ],
    "perfectibilité": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "performatif": [
      "derrida-l_universite_sans_condition-2001",
      "derrida-limited_inc-1988"
    ],
    "peut-être": [
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallo-centrique": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallo-centrisme": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallo-logocentrique": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallo-logocentrisme": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallocentrique": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallocentrisme": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994",
      "derrida-de_la_grammatologie-1967"
    ],
    "phallogocentrique": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "phallogocentrisme": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "pharmacon": [
      "derrida-la_dissemination-1972"
    ],
    "pharmakon": [
      "derrida-la_dissemination-1972",
      "derrida-dissemination-1981"
    ],
    "philosophie": [
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-positions-1972",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "phono-centrique": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "phono-centrisme": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "phonocentrique": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "phonocentrisme": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "phénoménologie": [
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "Platon": [
      "derrida-la_dissemination-1972",
      "derrida-dissemination-1981",
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "politique": [
      "derrida-politiques_de_l_amitie-1994",
      "derrida-spectres_de_marx-1993",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "possibilité": [
      "derrida-a_certain_impossible_possibility_of_saying_the_event-2007-walker"
    ],
    "postalité": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "poème": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-sovereignties_in_question-2005"
    ],
    "poésie": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003",
      "derrida-sovereignties_in_question-2005"
    ],
    "profession": [
      "derrida-l_universite_sans_condition-2001"
    ],
    "promesse": [
      "derrida-spectres_de_marx-1993",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "prothèse": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998"
    ],
    "présence": [
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-de_la_grammatologie-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "psychanalyse": [
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "psyché": [
      "derrida-psyche_inventions_de_l_autre-1987"
    ],
    "raison": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-rogues_two_essays_on_reason-2005-brault-naas"
    ],
    "religion": [
      "derrida-foi_et_savoir-2000",
      "derrida-acts_of_religion-2002",
      "derrida-donner_la_mort-1999"
    ],
    "responsabilité": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-donner_la_mort-1999",
      "derrida-acts_of_religion-2002",
      "derrida-of_hospitality-2000"
    ],
    "reste": [
      "derrida-glas-1974",
      "derrida-la_dissemination-1972"
    ],
    "Rousseau": [
      "derrida-de_la_grammatologie-1967"
    ],
    "s'entendre-parler": [
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "sacrifice": [
      "derrida-foi_et_savoir-2000",
      "derrida-donner_la_mort-1999",
      "derrida-the_animal_that_therefore_i_am-2008"
    ],
    "Saussure": [
      "derrida-de_la_grammatologie-1967",
      "derrida-signature_derrida-2013-multiple_translators"
    ],
    "Schmitt": [
      "derrida-politiques_de_l_amitie-1994"
    ],
    "Searle": [
      "derrida-limited_inc-1988"
    ],
    "secret": [
      "derrida-donner_la_mort-1999"
    ],
    "sexualité": [
      "derrida-eperons_les_styles_de_nietzsche-1979",
      "derrida-glas-1974",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "signature": [
      "derrida-marges_de_la_philosophie-1972",
      "derrida-glas-1974"
    ],
    "signe": [
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-de_la_grammatologie-1967",
      "derrida-marges_de_la_philosophie-1972"
    ],
    "souveraineté": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "spectralité": [
      "derrida-spectres_de_marx-1993"
    ],
    "spectre": [
      "derrida-spectres_de_marx-1993",
      "derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006",
      "derrida-cinders-2014-lukacher"
    ],
    "structuralisme": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "structure": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "style": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "supplément": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_dissemination-1972"
    ],
    "supplémentarité": [
      "derrida-de_la_grammatologie-1967"
    ],
    "survie": [
      "derrida-beliers_le_dialogue_ininterrompu_entre_deux_infinis_le_poeme-2003"
    ],
    "technique": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek",
      "derrida-archive_fever_a_freudian_impression-1998-prenowitz"
    ],
    "temporalité": [
      "derrida-le_probleme_de_la_genese_dans_la_philosophie_de_husserl-1990",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991"
    ],
    "temps": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-la_voix_et_le_phenomene-1967"
    ],
    "terrorisme": [
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ],
    "théologico-politique": [
      "derrida-seminaire_la_peine_de_mort_volume_i-2012",
      "derrida-seminaire_la_peine_de_mort_volume_ii_2000_2001-2015"
    ],
    "trace": [
      "derrida-de_la_grammatologie-1967",
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-marges_de_la_philosophie-1972",
      "derrida-positions-1972"
    ],
    "tradition": [
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "traduction": [
      "derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996",
      "derrida-points_de_suspension-1992"
    ],
    "tympan": [
      "derrida-marges_de_la_philosophie-1972"
    ],
    "télépathie": [
      "derrida-the_post_card_from_socrates_to_freud_and_beyond-1987"
    ],
    "télévision": [
      "derrida-stiegler-echographies_of_television_filmed_interviews-2002-bajorek"
    ],
    "université": [
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-l_universite_sans_condition-2001"
    ],
    "vie": [
      "derrida-life_death-2020-brault_naas"
    ],
    "violence": [
      "derrida-l_ecriture_et_la_difference-1967"
    ],
    "voile": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "voix": [
      "derrida-la_voix_et_le_phenomene-1967",
      "derrida-de_la_grammatologie-1967"
    ],
    "vérité": [
      "derrida-eperons_les_styles_de_nietzsche-1979"
    ],
    "économie": [
      "derrida-donner_le_temps_1_la_fausse_monnaie-1991"
    ],
    "écoute": [
      "derrida-l_oreille_de_heidegger-1994"
    ],
    "écriture": [
      "derrida-de_la_grammatologie-1967",
      "derrida-l_ecriture_et_la_difference-1967",
      "derrida-la_dissemination-1972",
      "derrida-marges_de_la_philosophie-1972",
      "husserl-l_origine_de_la_geometrie-1962-derrida"
    ],
    "éducation": [
      "derrida-du_droit_a_la_philosophie-1990",
      "derrida-l_universite_sans_condition-2001"
    ],
    "état": [
      "derrida-voyous_deux_essais_sur_la_raison-2003",
      "derrida-spectres_de_marx-1993"
    ],
    "éthique": [
      "derrida-adieu_a_emmanuel_levinas-1997",
      "derrida-politiques_de_l_amitie-1994"
    ],
    "événement": [
      "derrida-psyche_inventions_de_l_autre-1987",
      "derrida-voyous_deux_essais_sur_la_raison-2003"
    ]
  }
}