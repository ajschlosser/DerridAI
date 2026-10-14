/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
