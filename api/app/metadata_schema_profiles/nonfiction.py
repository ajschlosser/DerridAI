# Copyright 2026 Aaron John Schlosser, PhD.
"""Built-in metadata schema profile for general non-fiction."""

from __future__ import annotations

from ..corpus_metadata import STANCE_VALUES
from ..metadata_schema import MetadataSchema, SchemaGroup
from .common import PROFILE_FOOTER, profile_field

NONFICTION_SCHEMA_ID = "derridai-nonfiction"

_CLAIM_TYPE_VALUES = {
    "empirical": "A claim about observable, measurable, documentary, or otherwise evidentiary facts.",
    "causal": "A claim that one condition, event, or mechanism causes or contributes to another.",
    "interpretive": "A claim that explains the meaning, significance, or reading of evidence, events, texts, or phenomena.",
    "normative": "A claim about what ought to be done, valued, permitted, prohibited, or preferred.",
    "definitional": "A claim that defines, classifies, or specifies the meaning or boundaries of a term or category.",
    "methodological": "A claim about methods, procedures, design choices, or standards of inquiry.",
    "predictive": "A claim about what is expected or projected to occur.",
    "procedural": "An instruction or claim about how to carry out an action or process.",
    "anecdotal": "A claim principally grounded in a personal account or illustrative anecdote.",
    "descriptive": "A claim principally describing a state of affairs without a stronger causal, normative, or interpretive move.",
    "other": "A substantive claim that does not fit the other categories.",
}

_CERTAINTY_VALUES = {
    "direct_assertion": "The position holder presents the proposition without material qualification.",
    "qualified": "The proposition is asserted but explicitly limited, conditioned, or hedged.",
    "tentative": "The proposition is presented as provisional or uncertain.",
    "speculative": "The proposition is offered as conjecture, possibility, or exploratory suggestion.",
    "hypothetical": "The proposition is posed within an if/then, counterfactual, imagined, or test case rather than asserted as actual.",
    "reported_or_attributed": "The record reports another source's proposition without establishing the current speaker's commitment to it.",
    "not_applicable": "No proposition in the record receives a meaningful certainty classification.",
}

_SECTION_FUNCTION_VALUES = {
    "introduction": "Introduces a topic, problem, thesis, or scope.",
    "background": "Provides context, history, prior work, or orientation.",
    "definition": "Defines or specifies a term, category, measure, or concept.",
    "claim": "Primarily advances a substantive proposition.",
    "evidence": "Primarily presents evidence or data in support of a proposition.",
    "analysis": "Interprets, explains, compares, or reasons about claims or evidence.",
    "method": "Describes methods, procedures, materials, design, or analytical approach.",
    "result": "Reports findings, outcomes, measurements, or observed results.",
    "example_case": "Presents an example, case study, anecdote, or illustration.",
    "counterargument": "Presents or responds to an opposing, alternative, or limiting position.",
    "recommendation": "Proposes an action, policy, practice, or next step.",
    "conclusion": "Synthesizes findings, closes an argument, or states resulting implications.",
    "reference": "Primarily consists of bibliographic, citation, note, or reference material.",
    "transition": "Primarily moves between sections or argumentative stages.",
    "other": "A substantive function not represented by the other categories.",
}

_NONFICTION_GENRE_VALUES = {
    "scholarly_article": "A journal-style or conference-style scholarly research article.",
    "monograph": "A book-length non-fiction study organized as a sustained work.",
    "essay": "A non-fiction essay or essay-like reflective or argumentative work.",
    "journalism": "News reporting, feature writing, investigative journalism, or journalistic commentary.",
    "history": "A work principally presenting or interpreting historical events and evidence.",
    "biography": "A non-fiction life of another person.",
    "memoir": "A non-fiction first-person account of the author's own remembered experience.",
    "report": "An institutional, governmental, scientific, technical, or organizational report.",
    "textbook": "An instructional work organized to teach a subject systematically.",
    "reference": "A reference work such as an encyclopedia, handbook, dictionary, or catalogue.",
    "technical_documentation": "Technical documentation, specification, manual, or implementation-oriented guide.",
    "legal_or_policy": "Legal analysis, policy document, regulation, guidance, or policy-oriented work.",
    "speech_or_lecture": "A prepared or transcribed speech, lecture, sermon, testimony, or public address.",
    "correspondence": "Letters, memoranda, email, or other non-fiction correspondence.",
    "other_nonfiction": "A non-fiction genre not represented by the other categories.",
    "mixed_or_uncertain": "The work mixes genres or the available evidence does not support a cleaner classification.",
}


def nonfiction_schema() -> MetadataSchema:
    """Return DerridAI's read-only built-in non-fiction metadata profile."""

    fields = [
        profile_field(
            "nonfiction",
            "nonfiction_genre",
            "Non-fiction genre",
            "choice",
            "work_profile",
            "identifies the work's broad non-fiction genre. Use exactly one of: {values}. Prefer whole-document or paratextual evidence and "
            "choose mixed_or_uncertain when the work genuinely crosses forms.",
            allowed_values=_NONFICTION_GENRE_VALUES,
            strict=True,
            scope="corpus",
        ),
        profile_field(
            "nonfiction",
            "subject_domains",
            "Subject domains",
            "list",
            "work_profile",
            "lists the principal disciplines, subject areas, or professional domains of the work using concise established labels. Use whole-work "
            "evidence; do not promote a single incidental topic into a document-level domain.",
            scope="corpus",
            pos_tags=("ADJ", "NOUN", "PROPN"),
        ),
        profile_field(
            "nonfiction",
            "intended_audience",
            "Intended audience",
            "text",
            "work_profile",
            "describes the intended readership or user community only when the work itself, its paratext, register, or publication context supports it. "
            "Use a concise phrase such as specialist researchers, general readers, or software operators rather than demographic speculation.",
            scope="corpus",
            pos_tags=("ADJ", "NOUN"),
        ),
        profile_field(
            "nonfiction",
            "speaker",
            "Speaker",
            "text",
            "discourse",
            "identifies the textual or grammatical speaker responsible for the wording in this record when that role is distinguishable from the "
            "document author. Use a proper name or concise institutional or role label; return null for ordinary unsigned authorial prose where no "
            "separate speaker needs representation.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON", "ORG", "NORP"),
        ),
        profile_field(
            "nonfiction",
            "position_holder",
            "Position holder",
            "text",
            "discourse",
            "identifies the person, institution, group, or source that holds the principal proposition represented in this record. Distinguish the "
            "position holder from the grammatical speaker and from a person merely mentioned or criticized.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON", "ORG", "NORP"),
        ),
        profile_field(
            "nonfiction",
            "claim",
            "Primary claim",
            "text",
            "discourse",
            "states the record's principal substantive proposition in a concise source-faithful form. Preserve negation, modality, quantities, and "
            "attribution. Do not summarize the whole paragraph when no single proposition dominates; return null for pure headings, lists, raw data, "
            "or reference material.",
        ),
        profile_field(
            "nonfiction",
            "claim_type",
            "Claim type",
            "choice",
            "discourse",
            "classifies the primary claim by its principal function. Use exactly one of: {values}. Choose the type of the proposition itself, not the "
            "subject matter or the kind of evidence used to support it.",
            allowed_values=_CLAIM_TYPE_VALUES,
            strict=True,
        ),
        profile_field(
            "nonfiction",
            "target",
            "Target",
            "text",
            "discourse",
            "identifies the main proposition, policy, interpretation, practice, entity, or concept toward which the position holder's stance is directed. "
            "Use a short named entity or noun phrase rather than an explanatory sentence.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("PERSON", "ORG", "NORP", "GPE", "LOC", "EVENT", "LAW", "LANGUAGE", "WORK_OF_ART"),
        ),
        profile_field(
            "nonfiction",
            "stance",
            "Stance",
            "choice",
            "discourse",
            "describes the position holder's orientation toward the target or proposition. Prefer one of: {values}. Base the stance on explicit wording "
            "and preserve neutral description when the passage does not endorse or attack the target.",
            allowed_values=STANCE_VALUES,
            strict=False,
        ),
        profile_field(
            "nonfiction",
            "certainty_level",
            "Certainty level",
            "choice",
            "discourse",
            "classifies the modality or epistemic commitment attached to the primary claim. Use exactly one of: {values}. Attend to hedges, conditions, "
            "attribution, probability language, and counterfactual framing.",
            allowed_values=_CERTAINTY_VALUES,
            strict=True,
        ),
        profile_field(
            "nonfiction",
            "claim_scope",
            "Claim scope",
            "text",
            "discourse",
            "describes the population, place, time period, corpus, case, jurisdiction, or other domain to which the primary claim explicitly applies. "
            "Use a concise noun phrase; do not broaden beyond the qualifiers in the source.",
            pos_tags=("ADJ", "NOUN", "PROPN"),
        ),
        profile_field(
            "nonfiction",
            "evidence_types",
            "Evidence types",
            "list",
            "evidence",
            "lists the kinds of support actually used in this record for a substantive proposition, using concise labels such as statistical, documentary, "
            "archival, experimental, observational, testimonial, citation, logical, comparative, or case evidence. Do not label unsupported background "
            "facts as evidence.",
            pos_tags=("ADJ", "NOUN"),
        ),
        profile_field(
            "nonfiction",
            "evidence_items",
            "Evidence items",
            "list",
            "evidence",
            "lists the concrete pieces of support the record presents or invokes, such as a measurement, document, quotation, observation, finding, dataset, "
            "witness account, or cited result. Preserve key numbers and source names when they are material.",
            pos_tags=("NOUN", "PROPN", "NUM"),
        ),
        profile_field(
            "nonfiction",
            "sources_cited",
            "Sources cited",
            "list",
            "evidence",
            "lists named documents, authors, organizations, datasets, reports, studies, archives, or other sources explicitly cited or attributed in this "
            "record. Do not add sources merely implied by subject matter.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("PERSON", "ORG", "WORK_OF_ART", "LAW"),
        ),
        profile_field(
            "nonfiction",
            "statistics",
            "Statistics and quantities",
            "list",
            "evidence",
            "lists material quantitative statements in the record, retaining the quantity, unit, population or denominator, and time frame when present. "
            "Prefer source-faithful compact strings over isolated numbers without context.",
            pos_tags=("NUM", "NOUN"),
            ner_tags=("CARDINAL", "PERCENT", "MONEY", "QUANTITY", "ORDINAL"),
        ),
        profile_field(
            "nonfiction",
            "examples_or_cases",
            "Examples and cases",
            "list",
            "evidence",
            "lists concrete examples, case studies, anecdotes, episodes, or instances used to illustrate or support the record's point. Do not classify the "
            "main subject itself as an example unless the text uses it that way.",
            pos_tags=("NOUN", "PROPN"),
            ner_tags=("PERSON", "ORG", "GPE", "LOC", "EVENT"),
        ),
        profile_field(
            "nonfiction",
            "methods_or_procedures",
            "Methods and procedures",
            "list",
            "evidence",
            "lists research methods, analytical procedures, experimental steps, documentary methods, technical procedures, or operational instructions "
            "explicitly described in the record. Use concise method names or action phrases and do not infer unstated methodology.",
            pos_tags=("NOUN", "VERB"),
        ),
        profile_field(
            "nonfiction",
            "topics",
            "Topics",
            "list",
            "entities",
            "lists the record's materially developed topics using short precise noun phrases. Prefer substantive coverage over keyword frequency and exclude "
            "incidental mentions.",
            pos_tags=("ADJ", "NOUN", "PROPN"),
            ner_tags=("EVENT", "GPE", "LOC", "NORP", "ORG", "LANGUAGE", "LAW"),
        ),
        profile_field(
            "nonfiction",
            "persons",
            "Persons",
            "list",
            "entities",
            "lists people materially discussed, quoted, studied, or otherwise relevant in this record. Use canonical names when the text supports them; "
            "exclude purely grammatical pronouns whose referent cannot be resolved.",
            pos_tags=("PROPN",),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "nonfiction",
            "organizations",
            "Organizations",
            "list",
            "entities",
            "lists organizations, institutions, companies, agencies, movements, or organized bodies materially relevant in this record. Do not treat generic "
            "institutional nouns as named organizations.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("ORG", "NORP"),
        ),
        profile_field(
            "nonfiction",
            "places",
            "Places",
            "list",
            "entities",
            "lists geographic, geopolitical, or facility locations materially relevant in this record. Prefer the most specific text-supported place name and "
            "exclude places used only in incidental examples or publication addresses unless substantively relevant.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("GPE", "LOC", "FAC"),
        ),
        profile_field(
            "nonfiction",
            "dates",
            "Dates and periods",
            "list",
            "entities",
            "lists dates, years, eras, periods, or time intervals that materially anchor claims, events, evidence, or chronology in this record. Keep the "
            "source's precision; do not turn approximate periods into exact dates.",
            pos_tags=("NUM", "NOUN", "PROPN"),
            ner_tags=("DATE", "TIME"),
        ),
        profile_field(
            "nonfiction",
            "events",
            "Events",
            "list",
            "entities",
            "lists named or clearly delimited real-world events materially discussed in this record. Use concise canonical labels when available and do not "
            "convert every action into an event entity.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("EVENT",),
        ),
        profile_field(
            "nonfiction",
            "works_referenced",
            "Works referenced",
            "list",
            "entities",
            "lists books, articles, reports, laws, media works, titled datasets, or other identifiable works materially referenced in this record. Prefer the "
            "title as given and do not invent bibliographic details.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("WORK_OF_ART", "LAW"),
        ),
        profile_field(
            "nonfiction",
            "laws_or_policies",
            "Laws and policies",
            "list",
            "entities",
            "lists named laws, regulations, court decisions, standards, treaties, policies, programs, or formal rules materially discussed in this record. "
            "Use the source's name and jurisdiction when available; do not infer legal authority from ordinary recommendations.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("LAW", "ORG"),
        ),
        profile_field(
            "nonfiction",
            "section_function",
            "Section function",
            "choice",
            "structure",
            "classifies the record's principal rhetorical or documentary function within the surrounding non-fiction work. Use exactly one of: {values}. "
            "Choose what the record primarily does, not merely what topic it contains.",
            allowed_values=_SECTION_FUNCTION_VALUES,
            strict=True,
        ),
        profile_field(
            "nonfiction",
            "terms_defined",
            "Terms defined",
            "list",
            "structure",
            "lists terms, categories, measures, or concepts that the record explicitly defines, stipulates, operationalizes, or materially clarifies. Return "
            "the term or a short term-definition pair; do not treat ordinary descriptive wording as a definition.",
            pos_tags=("NOUN", "PROPN"),
        ),
        profile_field(
            "nonfiction",
            "questions_addressed",
            "Questions addressed",
            "list",
            "structure",
            "lists explicit or clearly framed research questions, practical questions, problems, or issues that this record asks or directly addresses. "
            "Preserve question scope and do not invent a question merely because the passage has a topic.",
        ),
        profile_field(
            "nonfiction",
            "counterpositions",
            "Counterpositions",
            "list",
            "structure",
            "lists opposing, alternative, or limiting positions that the record materially presents, attributes, or responds to. State each counterposition "
            "concisely and preserve its holder when identified.",
            pos_tags=("NOUN", "PROPN"),
            ner_tags=("PERSON", "ORG", "NORP"),
        ),
        profile_field(
            "nonfiction",
            "recommendations",
            "Recommendations",
            "list",
            "structure",
            "lists concrete actions, policies, practices, or next steps that the record explicitly recommends, advises, requires, or proposes. Preserve "
            "conditions and intended actors where stated; do not turn descriptive findings into recommendations.",
            pos_tags=("VERB", "NOUN"),
        ),
        profile_field(
            "nonfiction",
            "conclusions",
            "Conclusions",
            "list",
            "structure",
            "lists conclusions or implications that the record explicitly draws from prior reasoning or evidence. Use concise source-faithful propositions and "
            "distinguish a conclusion from a premise, raw result, or recommendation.",
        ),
    ]
    return MetadataSchema(
        id=NONFICTION_SCHEMA_ID,
        schema_version="1.0.0",
        name="Non-fiction",
        description=(
            "Claims, attribution, evidence, sources, statistics, methods, entities, rhetorical structure, "
            "recommendations, and conclusions for general non-fiction."
        ),
        groups=[
            SchemaGroup(
                key="discourse",
                label="Claims and attribution",
                intro=(
                    "Infer ONLY claim, attribution, stance, scope, and certainty metadata for one non-fiction record. Distinguish document author, "
                    "grammatical speaker, position holder, source being reported, and target. Reconstruct propositions conservatively and preserve "
                    "negation, modality, quantities, and attribution."
                ),
                notes=[
                    "A record may contain no claim at all; headings, raw tables, references, and purely structural text should not be forced into proposition metadata.",
                    "For the locked discourse_role, choose the closest supported general role and use claim_type and section_function for the more specific non-fiction classification.",
                ],
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="evidence",
                label="Evidence and methods",
                intro=(
                    "Infer ONLY evidence, source, quantitative, example or case, and method metadata for this non-fiction record. Capture concrete support "
                    "actually used or described by the passage; do not treat every factual statement as evidence for an unstated claim."
                ),
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="entities",
                label="Topics and entities",
                intro=(
                    "Infer conservative semantic indexing for this non-fiction record: topics, people, organizations, places, dates, events, works, laws, "
                    "and policies. Return only entities and topics materially relevant to the record, not every named token."
                ),
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="structure",
                label="Rhetorical and documentary structure",
                intro=(
                    "Infer ONLY the record's document or rhetorical function plus explicit definitions, questions, counterpositions, recommendations, and "
                    "conclusions. Distinguish what the passage does in the document from the subject matter it discusses."
                ),
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="work_profile",
                label="Work-level non-fiction profile",
                intro=(
                    "Infer ONLY work-level non-fiction genre, subject-domain, and intended-audience metadata. These values apply to the corpus as a whole. "
                    "Prefer title-page, publication, preface, table-of-contents, or repeated whole-document evidence over a single local passage."
                ),
                footer=PROFILE_FOOTER,
            ),
        ],
        fields=fields,
    )
