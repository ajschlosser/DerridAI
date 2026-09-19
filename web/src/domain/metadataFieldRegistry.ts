export type MetadataControl = 'enum'|'combobox'|'multi-combobox'|'boolean'|'number'|'text';
export interface MetadataFieldSpec { control:MetadataControl; allowedValues?:string[]; suggestionFields?:string[]; allowCustom?:boolean }

const SPEAKER_FIELDS=['speaker','position_holder','region_author','document_author','translator','quoted_speaker','quoted_author','quoted_position_holder'];
const TARGET_FIELDS=['target','quoted_addressee','quoted_referent'];

export function metadataFieldSpec(field:string, regionTypes:string[], discourseRoles:string[]):MetadataFieldSpec{
  if(field==='region_type') return {control:'enum',allowedValues:regionTypes};
  if(field==='discourse_role') return {control:'enum',allowedValues:discourseRoles};
  if(['proposition_status','stance','claim_scope'].includes(field)) return {control:'combobox',suggestionFields:[field],allowCustom:true};
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
