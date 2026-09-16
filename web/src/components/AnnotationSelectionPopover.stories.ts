import type { Meta, StoryObj } from "@storybook/vue3";
import AnnotationSelectionPopover from "./AnnotationSelectionPopover.vue";
const meta: Meta<typeof AnnotationSelectionPopover>={title:"Annotations/Selection Annotation Popover",component:AnnotationSelectionPopover,args:{recordLabel:"Of Grammatology · p. 23",quote:"The trace is not a presence but the simulacrum of a presence."}};export default meta;type Story=StoryObj<typeof AnnotationSelectionPopover>;export const Default:Story={};
