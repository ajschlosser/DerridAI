import type { Meta, StoryObj } from '@storybook/vue3-vite';
import LlmExecutionControl from './LlmExecutionControl.vue';
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const profiles:any[]=[{id:'primary',name:'Scholarly local',type:'ollama',model:'gemma-4-26B',max_concurrent_requests:2},{id:'second',name:'Second reader',type:'ollama',model:'qwen3',max_concurrent_requests:1},{id:'openai',name:'OpenAI',type:'openai',model:'gpt-5.6'}];
const meta={title:'Corpus Builder/LLM/Execution Control',component:LlmExecutionControl,args:{modelValue:'primary',modelOverride:'gemma-4-26B',profiles,task:'This model will propose metadata without changing source text.'}} satisfies Meta<typeof LlmExecutionControl>;
export default meta; type Story=StoryObj<typeof meta>;
export const Default:Story={};
export const OllamaAtCapacity:Story={args:{concurrencyRisk:true,activeRequests:2,concurrencyLimit:2}};
export const OpenAiProfile:Story={args:{modelValue:'openai',modelOverride:'gpt-5.6'}};
export const NoProfiles:Story={args:{modelValue:'',profiles:[]}};
