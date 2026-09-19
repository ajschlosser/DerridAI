export type MetadataControl = 'enum'|'combobox'|'multi-combobox'|'boolean'|'number'|'text';
export interface MetadataFieldSpec { control:MetadataControl; allowedValues?:string[]; suggestionFields?:string[]; allowCustom?:boolean }

const SPEAKER_FIELDS=['speaker','position_holder','region_author','document_author','translator','quoted_speaker','quoted_author','quoted_position_holder'];
const TARGET_FIELDS=['target','quoted_addressee','quoted_referent'];

// Closed semantic vocabularies belong here. Open scholarly identifiers remain
// editable comboboxes even when the application can suggest known values.
export const PROPOSITION_STATUS_VALUES=[
  'asserted','affirmed','rejected','criticized','questioned','qualified',
  'hypothetical','attributed','reported','conceded','suspended'
];
export const STANCE_VALUES=[
  'affirm','reject','criticize','question','qualify','suspend','neutral','describe'
];

export const STANCE_ALIASES:Record<string,string>={
  affirmed:'affirm',
  rejected:'reject',
  criticized:'criticize',
  questioned:'question',
  qualified:'qualify',
  suspended:'suspend',
  descriptive:'describe',
};

export function normalizeMetadataFieldValue(field:string,value:unknown):unknown{
  if(field!=='stance'||typeof value!=='string')return value;
  const normalized=value.trim().toLowerCase();
  if(STANCE_VALUES.includes(normalized))return normalized;
  return STANCE_ALIASES[normalized]??value;
}

export function metadataFieldSpec(field:string, regionTypes:string[], discourseRoles:string[]):MetadataFieldSpec{
  if(field==='region_type') return {control:'enum',allowedValues:regionTypes};
  if(field==='discourse_role') return {control:'enum',allowedValues:discourseRoles};
  if(field==='proposition_status') return {control:'enum',allowedValues:PROPOSITION_STATUS_VALUES};
  if(field==='stance') return {control:'enum',allowedValues:STANCE_VALUES};
  if(field==='claim_scope') return {control:'combobox',suggestionFields:[field],allowCustom:true};
  if(field==='primary_text'||field==='document_is_translation'||field==='is_direct_quote') return {control:'boolean'};
  if(field==='year'||field==='publication_year') return {control:'number'};
  if(['semantic_function','quoted_speaker','quoted_author','quoted_work','quoted_position_holder','quoted_addressee','quoted_referent','quotation_chain','topics','concepts','persons','works_referenced','document_language','original_language'].includes(field)){
    const suggestions=field.includes('quoted_')?SPEAKER_FIELDS:['topics','concepts','persons','works_referenced',...SPEAKER_FIELDS,...TARGET_FIELDS];
    return {control:'multi-combobox',suggestionFields:suggestions,allowCustom:true};
  }
  if(SPEAKER_FIELDS.includes(field)) return {control:'combobox',suggestionFields:SPEAKER_FIELDS,allowCustom:true};
  if(TARGET_FIELDS.includes(field)) return {control:'combobox',suggestionFields:TARGET_FIELDS,allowCustom:true};
  if(['work','document_title','short_title','original_title','edition','publisher','publication_place','isbn'].includes(field)) return {control:'combobox',suggestionFields:[field],allowCustom:true};
  return {control:'text',allowCustom:true};
}

export function metadataSuggestions(record:Record<string,unknown>, fields:string[]=[]):string[]{
  const out=new Set<string>();
  for(const field of fields){
    const value=record[field];
    if(typeof value==='string'&&value.trim()) out.add(value.trim());
    if(Array.isArray(value)) for(const item of value) if(typeof item==='string'&&item.trim()) out.add(item.trim());
  }
  return [...out].sort((a,b)=>a.localeCompare(b));
}
