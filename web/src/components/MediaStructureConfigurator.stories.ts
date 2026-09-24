// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MediaStructureConfigurator from "./MediaStructureConfigurator.vue";

const meta = {
  title: "Corpus Builder/Source/Media Structure",
  component: MediaStructureConfigurator,
  args: {
    filename: "example-source",
    pageCount: 12,
    blockCount: 84,
  },
} satisfies Meta<typeof MediaStructureConfigurator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Audio: Story = {
  args: {
    mediaKind: "audio",
    filename: "interview.wav",
    pageCount: undefined,
    blockCount: 36,
  },
};

export const Image: Story = {
  args: {
    mediaKind: "image",
    filename: "manuscript-page.jpg",
    pageCount: 1,
    blockCount: 9,
  },
};

export const WebText: Story = {
  args: {
    mediaKind: "gutenberg",
    filename: "gutenberg-work.html",
    pageCount: undefined,
    blockCount: 148,
  },
};

export const NarrowViewport: Story = {
  args: {
    mediaKind: "audio",
    filename: "field-recording.mp3",
    pageCount: undefined,
    blockCount: 22,
  },
  decorators: [
    () => ({
      template: '<div style="max-width: 520px"><story /></div>',
    }),
  ],
};
