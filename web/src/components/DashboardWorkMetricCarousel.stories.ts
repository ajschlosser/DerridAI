import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DashboardWorkMetricCarousel from "./DashboardWorkMetricCarousel.vue";
const slides=[
  {id:"average",title:"Top 5 Works by Average Record Length",items:[{label:"Of Grammatology",value:1482},{label:"Dissemination",value:1247},{label:"Writing and Difference",value:1036}]},
  {id:"words",title:"Top 5 Works by Total Words",items:[{label:"Specters of Marx",value:840000,formatted:"840K"},{label:"Of Grammatology",value:790000,formatted:"790K"}]},
  {id:"records",title:"Top 5 Works by Number of Records",items:[{label:"Specters of Marx",value:2048},{label:"Of Grammatology",value:1892}]},
];
const meta={title:"Dashboard/Work Metric Carousel",component:DashboardWorkMetricCarousel,args:{slides}} satisfies Meta<typeof DashboardWorkMetricCarousel>;export default meta;type Story=StoryObj<typeof meta>;export const Default:Story={};
