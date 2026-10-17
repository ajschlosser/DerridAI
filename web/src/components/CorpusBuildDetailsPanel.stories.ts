// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { ref } from 'vue';
import CorpusBuildDetailsPanel from './CorpusBuildDetailsPanel.vue';
const meta={title:'Corpus Builder/Workflow/Build Details',component:CorpusBuildDetailsPanel,args:{buildId:'b1',sourceFilename:'La Prisonnière.pdf',warningCount:100},render:args=>({components:{CorpusBuildDetailsPanel},setup:()=>({args}),template:'<CorpusBuildDetailsPanel v-bind="args"><template #activity><p>973 / 1110</p></template><template #issues><p>structured_output_invalid</p></template><template #settings><p>Ollama · auto</p></template></CorpusBuildDetailsPanel>'})} satisfies Meta<typeof CorpusBuildDetailsPanel>;
export default meta;
type Story=StoryObj<typeof meta>;
export const WithWarnings:Story={};
export const NoWarnings:Story={args:{warningCount:0}};
export const LongSource:Story={args:{sourceFilename:'À la recherche du temps perdu — La Prisonnière — édition française.pdf'}};
export const Docked:Story={render:args=>({components:{CorpusBuildDetailsPanel},setup(){return {args,target:ref<HTMLElement|null>(null)}},template:'<div style="display:grid;grid-template-columns:minmax(0,1fr) 440px;min-height:600px"><CorpusBuildDetailsPanel v-bind="args" :dock-target="target"><template #activity><p>973 / 1110</p></template><template #issues><p>structured_output_invalid</p></template><template #settings><p>Ollama · auto</p></template></CorpusBuildDetailsPanel><div ref="target"></div></div>'})};
