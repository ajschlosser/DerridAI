/* Copyright 2026 Aaron John Schlosser, PhD. */

export interface NlpTagOption {
  value: string;
  label: string;
}

export const UNIVERSAL_POS_TAG_OPTIONS: NlpTagOption[] = [
  { value: "ADJ", label: "Adjective" },
  { value: "ADP", label: "Adposition" },
  { value: "ADV", label: "Adverb" },
  { value: "AUX", label: "Auxiliary" },
  { value: "CCONJ", label: "Coordinating conjunction" },
  { value: "DET", label: "Determiner" },
  { value: "INTJ", label: "Interjection" },
  { value: "NOUN", label: "Common noun" },
  { value: "NUM", label: "Number" },
  { value: "PART", label: "Particle" },
  { value: "PRON", label: "Pronoun" },
  { value: "PROPN", label: "Proper noun" },
  { value: "PUNCT", label: "Punctuation" },
  { value: "SCONJ", label: "Subordinating conjunction" },
  { value: "SYM", label: "Symbol" },
  { value: "VERB", label: "Verb" },
  { value: "X", label: "Other" },
];

export const NER_TAG_OPTIONS: NlpTagOption[] = [
  { value: "CARDINAL", label: "Cardinal number" },
  { value: "DATE", label: "Date" },
  { value: "EVENT", label: "Named event" },
  { value: "FAC", label: "Facility" },
  { value: "GPE", label: "Geopolitical entity" },
  { value: "LANGUAGE", label: "Language" },
  { value: "LAW", label: "Legal document" },
  { value: "LOC", label: "Location" },
  { value: "MONEY", label: "Monetary value" },
  { value: "NORP", label: "National/religious group" },
  { value: "ORDINAL", label: "Ordinal number" },
  { value: "ORG", label: "Organization" },
  { value: "PERCENT", label: "Percentage" },
  { value: "PERSON", label: "Person" },
  { value: "PRODUCT", label: "Product" },
  { value: "QUANTITY", label: "Measurement" },
  { value: "TIME", label: "Time" },
  { value: "WORK_OF_ART", label: "Creative work" },
];
