import type { Meta, StoryObj } from "@storybook/vue3-vite";
import FieldEvidenceList from "./FieldEvidenceList.vue";
const evidence={position_holder:{block_ids:["p00031-b0004","p00031-b0005"],confidence:.94,reason:"The passage explicitly attributes the proposition to Heidegger."},stance:{block_ids:["p00031-b0007"],confidence:.82,reason:"Derrida marks a qualification of the reported position."}};
const meta={title:"PDF Corpus Builder/Field Evidence",component:FieldEvidenceList,args:{evidence,selectedField:"position_holder"}} satisfies Meta<typeof FieldEvidenceList>;
export default meta;type Story=StoryObj<typeof meta>;export const Selected:Story={};export const Empty:Story={args:{evidence:{},selectedField:""}};
