import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
const profiles = [
  { id:"ollama-local", name:"Local Ollama", type:"ollama", model:"qwen3:8b", base_url:"http://localhost:11434", max_concurrent_requests:2 },
  { id:"openai-compatible", name:"OpenAI-compatible", type:"openai", model:"gpt-4.1-mini", base_url:"https://api.example.test/v1", max_concurrent_requests:4 },
] as any;
const meta = { title:"Providers/Inputs/Profile Select", component:ProviderProfileSelect, args:{ modelValue:"ollama-local", profiles, defaultProfileId:"ollama-local" } } satisfies Meta<typeof ProviderProfileSelect>;
export default meta; type Story=StoryObj<typeof meta>; export const Default:Story={}; export const Empty:Story={args:{modelValue:"",profiles:[]}};
