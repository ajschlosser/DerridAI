/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
