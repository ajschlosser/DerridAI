import type { Meta, StoryObj } from "@storybook/vue3";
import ResearchEvidencePanel from "./ResearchEvidencePanel.vue";

const meta:Meta<typeof ResearchEvidencePanel>={title:"Research/Evidence Panel 0.31",component:ResearchEvidencePanel,parameters:{layout:"padded"}};
export default meta;
type Story=StoryObj<typeof ResearchEvidencePanel>;
export const SelectedEvidence:Story={args:{canRemove:true,selectedEvidence:[
  {key:"db:a:1",record_id:"adieu-0018",work:"Adieu to Emmanuel Levinas",page_start:6,page_end:7,inline_citation:"(Derrida 1999: 6-7)",speaker:"Derrida",position_holder:"Levinas",stance:"analysis",discourse_role:"engagement",text_preview:"Responsibility is articulated through the mortality of the other and the exposure of the face."},
  {key:"db:a:2",record_id:"death-0112",work:"The Death Penalty, Volume I",page_start:118,text_preview:"The death penalty concentrates a set of questions around sovereignty, exception, and the right over life."},
]}};
export const AnswerEvidence:Story={args:{activeIndex:0,resultEvidence:[
  {evidence_id:"E0",inline_citation:"(Derrida 1999: 6-7)",rerank_score:.92,record:{record_id:"adieu-0018",work:"Adieu to Emmanuel Levinas",page_start:6,page_end:7,speaker:"Derrida",position_holder:"Levinas",stance:"analysis",discourse_role:"engagement",text:"Responsibility is articulated here through the mortality of the other and the exposure of the face.",concepts:["responsibility","death","other"]}},
  {evidence_id:"E1",inline_citation:"(Derrida 1999: 3-4)",record:{record_id:"adieu-0012",work:"Adieu to Emmanuel Levinas",page_start:3,page_end:4,text:"The ethical relation is described through an exposure that precedes defensive mastery."}},
]}};
