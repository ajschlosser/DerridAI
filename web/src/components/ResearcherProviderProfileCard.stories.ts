import type { Meta, StoryObj } from "@storybook/vue3";
import ResearcherProviderProfileCard from "./ResearcherProviderProfileCard.vue";
const meta: Meta<typeof ResearcherProviderProfileCard> = {title:"Users/Researcher Provider Profile Card",component:ResearcherProviderProfileCard,args:{profile:{id:"research-local",name:"Local research model",type:"ollama",model:"qwen3:8b",base_url:"http://localhost:11434",max_concurrent_requests:1},models:[{name:"qwen3:8b"},{name:"gemma3:4b"}]}};export default meta;type Story=StoryObj<typeof ResearcherProviderProfileCard>;export const Default:Story={};
