import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordProvenance from "./RecordProvenance.vue";
const meta={title:"Record Workspace/Provenance",component:RecordProvenance,args:{record:{speaker:"Derrida",position_holder:"Levinas",stance:"qualified endorsement",target:"Heidegger",discourse_role:"analysis",proposition_status:"attributed claim",claim_scope:"ethics and mortality"}}} satisfies Meta<typeof RecordProvenance>;
export default meta;type Story=StoryObj<typeof meta>;
export const StructuredAttribution:Story={};
export const Empty:Story={args:{record:{}}};
