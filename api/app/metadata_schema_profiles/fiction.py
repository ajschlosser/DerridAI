# Copyright 2026 Aaron John Schlosser, PhD.
"""Built-in metadata schema profile for fiction."""

from __future__ import annotations

from ..metadata_schema import MetadataSchema, SchemaGroup
from .common import PROFILE_FOOTER, profile_field

FICTION_SCHEMA_ID = "derridai-fiction"

_FICTION_FORM_VALUES = {
    "novel": "A book-length prose fiction organized as a novel.",
    "novella": "A prose fiction longer than a short story but substantially shorter than a typical novel.",
    "short_story": "A short prose fiction intended to stand as one story.",
    "story_cycle": "A set of linked stories that form a larger fictional whole.",
    "drama": "A fictional work primarily written for staged dramatic performance.",
    "narrative_poetry": "A fictional narrative principally composed in verse.",
    "other_fiction": "A fictional form not represented by the other categories.",
    "mixed_or_uncertain": "The work mixes forms or the available evidence does not support a cleaner classification.",
}

_POINT_OF_VIEW_VALUES = {
    "first_person": "The narration primarily uses an I/we narrator who participates in or witnesses the story.",
    "second_person": "The narration primarily addresses or constructs the protagonist as you.",
    "third_person_limited": "Third-person narration is substantially restricted to one character's knowledge or perception.",
    "third_person_omniscient": "Third-person narration can move beyond any one character's knowledge or interiority.",
    "third_person_objective": "Third-person narration presents externally observable action with little or no privileged interior access.",
    "mixed_or_shifting": "The record materially shifts among more than one point-of-view regime.",
    "indeterminate": "The available record does not support a reliable point-of-view classification.",
}

_TEMPORAL_RELATION_VALUES = {
    "chronological": "The passage advances the story in its current chronological sequence.",
    "analepsis_flashback": "The passage moves back to events earlier than the current story point.",
    "prolepsis_flashforward": "The passage anticipates events later than the current story point.",
    "iterative_or_habitual": "The passage summarizes repeated, habitual, or recurring events rather than one bounded occurrence.",
    "simultaneous_or_present": "The narration is organized around an ongoing or narratively present event.",
    "mixed": "More than one temporal relation materially structures the record.",
    "indeterminate": "The temporal relation cannot be determined reliably from this record.",
}


def fiction_schema() -> MetadataSchema:
    """Return DerridAI's read-only built-in fiction metadata profile."""

    fields = [
        profile_field(
            "fiction",
            "fiction_form",
            "Fiction form",
            "choice",
            "work_profile",
            "identifies the broad literary form of the work. Use exactly one of: {values}. "
            "Base this on whole-work or paratextual evidence when available; do not infer a work's form from one incidental passage.",
            allowed_values=_FICTION_FORM_VALUES,
            strict=True,
            scope="corpus",
        ),
        profile_field(
            "fiction",
            "fiction_genres",
            "Genres and subgenres",
            "list",
            "work_profile",
            "lists materially supported genre or subgenre labels, such as gothic, detective fiction, romance, historical fiction, "
            "science fiction, fantasy, satire, or bildungsroman. Prefer established concise labels and avoid inferring a work-wide genre "
            "from one isolated motif.",
            scope="corpus",
            pos_tags=("ADJ", "NOUN", "PROPN"),
        ),
        profile_field(
            "fiction",
            "narrator",
            "Narrator",
            "text",
            "discourse",
            "identifies the narrating voice responsible for this record. Use a proper name when textually identifiable; otherwise use a "
            "concise role phrase such as unnamed first-person narrator. Distinguish narrator from document author, focalizer, and characters "
            "who merely speak or appear. Return null when no narrating voice applies.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "point_of_view",
            "Point of view",
            "choice",
            "discourse",
            "classifies the narrative point of view operating in this record. Use exactly one of: {values}. Classify the local passage rather "
            "than the work in general and choose indeterminate when the evidence is insufficient.",
            allowed_values=_POINT_OF_VIEW_VALUES,
            strict=True,
        ),
        profile_field(
            "fiction",
            "focalizers",
            "Focalizers",
            "list",
            "discourse",
            "lists the character or consciousness through whose perception, knowledge, or evaluative perspective the scene is presented. "
            "Do not equate focalizer with narrator automatically; include only locally supported focalizers.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "narrative_functions",
            "Narrative functions",
            "list",
            "discourse",
            "lists the main narrative functions materially operating in the record using short labels, for example scene narration, "
            "description, exposition, dialogue, interior monologue, free indirect discourse, summary, reflection, or transition.",
            pos_tags=("NOUN",),
        ),
        profile_field(
            "fiction",
            "temporal_relation",
            "Temporal relation",
            "choice",
            "discourse",
            "classifies how this record relates temporally to the surrounding story sequence. Use exactly one of: {values}. "
            "Do not call a memory a flashback unless the narration actually shifts to an earlier story time.",
            allowed_values=_TEMPORAL_RELATION_VALUES,
            strict=True,
        ),
        profile_field(
            "fiction",
            "characters_present",
            "Characters present",
            "list",
            "storyworld",
            "lists named or clearly identifiable fictional characters who participate in, perceive, or are physically present in the scene "
            "represented by this record. Do not add merely mentioned off-scene figures.",
            pos_tags=("PROPN", "PRON", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "characters_mentioned",
            "Characters mentioned",
            "list",
            "storyworld",
            "lists fictional characters referred to in the record who are not participating in the represented scene. Prefer names or stable "
            "role labels and avoid duplicating characters already captured as present unless the text genuinely blurs the distinction.",
            pos_tags=("PROPN", "PRON", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "character_relationships",
            "Character relationships",
            "list",
            "storyworld",
            "records relationships this passage itself establishes or materially invokes. Use concise relation strings such as "
            "Jane Bennet — sister of — Elizabeth Bennet. Do not infer relationships from outside knowledge.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "locations",
            "Locations",
            "list",
            "storyworld",
            "lists locations that materially situate the action or narrated setting in this record. Use the most specific text-supported place "
            "names or concise fictional-place labels; exclude places that are only incidental comparisons.",
            pos_tags=("PROPN", "NOUN"),
            ner_tags=("GPE", "LOC", "FAC"),
        ),
        profile_field(
            "fiction",
            "setting_time",
            "Setting time",
            "list",
            "storyworld",
            "lists explicit or reliably inferable temporal settings for the represented action, such as a date, historical period, season, "
            "time of day, age, reign, or relative story time. Do not convert vague atmosphere into a precise date.",
            pos_tags=("NUM", "NOUN", "PROPN"),
            ner_tags=("DATE", "TIME", "EVENT"),
        ),
        profile_field(
            "fiction",
            "events",
            "Events",
            "list",
            "storyworld",
            "lists the principal fictional events represented or reported in this record as concise actor-action phrases. Preserve negation and "
            "uncertainty, and avoid breaking one event into trivial micro-actions.",
            pos_tags=("VERB", "NOUN", "PROPN"),
            ner_tags=("EVENT",),
        ),
        profile_field(
            "fiction",
            "objects_of_significance",
            "Significant objects",
            "list",
            "storyworld",
            "lists objects that are narratively salient because characters act on them, they organize the scene, recur, or carry evident "
            "symbolic or plot importance. Do not list every concrete noun.",
            pos_tags=("NOUN", "PROPN"),
            ner_tags=("PRODUCT", "WORK_OF_ART"),
        ),
        profile_field(
            "fiction",
            "direct_speech",
            "Direct speech",
            "boolean",
            "dialogue",
            "is true only when the record contains words directly represented as a character's or narrator's utterance. It is false for merely "
            "reported or summarized speech and null only when extraction or segmentation prevents a reliable decision.",
        ),
        profile_field(
            "fiction",
            "dialogue_speakers",
            "Dialogue speakers",
            "list",
            "dialogue",
            "lists the fictional speakers of directly represented speech. Resolve pronouns only when local context supports the identity; "
            "do not substitute the document author for an unidentified character speaker.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "dialogue_addressees",
            "Dialogue addressees",
            "list",
            "dialogue",
            "lists the characters or groups being directly addressed by speech when the addressee is textually supported. Return [] rather "
            "than guessing an implied listener.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "reported_speech_sources",
            "Reported speech sources",
            "list",
            "dialogue",
            "lists characters or narrating sources whose speech, thought, letter, message, or prior utterance is indirectly reported or "
            "paraphrased rather than directly quoted in this record.",
            pos_tags=("PRON", "PROPN", "NOUN"),
            ner_tags=("PERSON",),
        ),
        profile_field(
            "fiction",
            "themes",
            "Themes",
            "list",
            "literary",
            "lists broad ideas or problems that the record substantively develops, not merely nouns that appear. Use concise thematic phrases "
            "and require local textual support; do not assign work-wide themes from generic or transitional language.",
            pos_tags=("ADJ", "NOUN", "PROPN"),
        ),
        profile_field(
            "fiction",
            "motifs",
            "Motifs",
            "list",
            "literary",
            "lists recurring images, situations, phrases, objects, or patterns that this record materially instantiates as a literary motif. "
            "Do not treat a one-off detail as a motif unless recurrence is supported by available context or reviewed precedent.",
            pos_tags=("ADJ", "NOUN", "PROPN"),
        ),
        profile_field(
            "fiction",
            "symbols",
            "Symbols",
            "list",
            "literary",
            "lists objects, images, places, gestures, or figures that the passage gives a supported symbolic function beyond literal reference. "
            "Be conservative: a salient object is not automatically a symbol.",
            pos_tags=("NOUN", "PROPN"),
        ),
        profile_field(
            "fiction",
            "tone",
            "Tone",
            "list",
            "literary",
            "lists one or two concise labels for the narrator's or passage's textual attitude or tonal register, such as ironic, elegiac, comic, "
            "menacing, detached, or tender. Base labels on linguistic evidence rather than the reader's emotional reaction.",
            pos_tags=("ADJ", "NOUN"),
        ),
        profile_field(
            "fiction",
            "literary_devices",
            "Literary devices",
            "list",
            "literary",
            "lists literary techniques materially used in this record, such as irony, foreshadowing, metaphor, simile, free indirect discourse, "
            "unreliable narration, stream of consciousness, or dramatic irony. Prefer established concise terms and avoid speculative over-labeling.",
            pos_tags=("NOUN", "ADJ"),
        ),
    ]
    return MetadataSchema(
        id=FICTION_SCHEMA_ID,
        schema_version="1.0.0",
        name="Fiction",
        description=(
            "Narrative voice, point of view, characters, storyworld, dialogue, temporal structure, "
            "themes, motifs, symbols, tone, and literary technique for fiction research."
        ),
        groups=[
            SchemaGroup(
                key="discourse",
                label="Narrative voice and perspective",
                intro=(
                    "Infer ONLY narrative voice, perspective, and temporal-presentation metadata for one fiction record. Treat document author, "
                    "narrator, focalizer, and character speaker as distinct roles. The locked core fields remain cross-domain structural metadata; "
                    "choose the closest supported general discourse role without forcing argumentative semantics into fiction, and use the "
                    "domain-specific narrative fields below for narratological classification."
                ),
                notes=[
                    "Preserve ambiguity between narrator and focalizer; do not collapse them merely because the same character may occupy both roles.",
                    "Use null or [] when the passage does not support a field rather than carrying work-level knowledge into a local record.",
                ],
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="storyworld",
                label="Characters, setting, and events",
                intro=(
                    "Infer ONLY storyworld metadata grounded in this fiction record. Distinguish scene participants from off-scene references, "
                    "and distinguish narrated events from background facts or comparisons. Do not import character or plot knowledge from outside "
                    "the supplied context."
                ),
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="dialogue",
                label="Dialogue and reported speech",
                intro=(
                    "Infer ONLY speech-relation metadata for this fiction record. Distinguish direct speech from indirect or reported speech, "
                    "and identify speakers or addressees only when the local text or supplied neighbouring context supports them."
                ),
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="literary",
                label="Literary interpretation",
                intro=(
                    "Infer conservative literary-indexing metadata for this fiction record. Themes, motifs, symbols, tone, and devices are "
                    "interpretive assertions, so keep labels concise, bind them to the passage, and prefer omission over generic literary vocabulary."
                ),
                footer=PROFILE_FOOTER,
            ),
            SchemaGroup(
                key="work_profile",
                label="Work-level fiction profile",
                intro=(
                    "Infer ONLY work-level fiction form and genre metadata. These values apply to the corpus as a whole. Prefer title-page, publication, "
                    "table-of-contents, preface, or repeated whole-work evidence over a single local passage."
                ),
                footer=PROFILE_FOOTER,
            ),
        ],
        fields=fields,
    )
