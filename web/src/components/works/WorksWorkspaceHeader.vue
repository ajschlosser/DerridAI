<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import UiPageHeader from "../ui/UiPageHeader.vue";

const props = withDefaults(
  defineProps<{
    mode?: "admin" | "researcher";
    canManageCorpus?: boolean;
    canPopulate?: boolean;
    canCreateSite?: boolean;
    corpusManageDeniedReason?: string;
    populateDisabledReason?: string;
    createSiteDisabledReason?: string;
  }>(),
  {
    mode: "admin",
    canManageCorpus: true,
    canPopulate: true,
    canCreateSite: true,
    corpusManageDeniedReason: "",
    populateDisabledReason: "",
    createSiteDisabledReason: "",
  },
);

const emit = defineEmits<{
  chooseJsonl: [];
  separate: [];
  populateAll: [];
  createSite: [];
}>();

const i18n = useI18nStore();

// Synchronization is deliberately absent: it changes derived database state, so it lives with the
// corpus-database context rather than among the commands that act on the loaded library.
const items = computed<UiMenuItem[]>(() => [
  {
    id: "separate",
    label: i18n.t("works.separate_jsonl"),
    icon: "filter",
    reason: props.canManageCorpus ? undefined : props.corpusManageDeniedReason,
  },
  {
    id: "populate-all",
    label: i18n.t("works.populate_all_metadata"),
    icon: "spark",
    reason: props.canPopulate ? undefined : props.populateDisabledReason,
  },
  {
    id: "create-site",
    label: i18n.t("site.create_button"),
    icon: "download",
    reason: props.canCreateSite ? undefined : props.createSiteDisabledReason,
  },
]);

function onSelect(id: string) {
  if (id === "separate") emit("separate");
  else if (id === "populate-all") emit("populateAll");
  else if (id === "create-site") emit("createSite");
}
</script>

<template>
  <UiPageHeader
    :kicker="i18n.t('section.corpus')"
    :title="i18n.t('nav.works')"
    title-id="works-page-title"
    :description="mode === 'admin' ? i18n.t('works.page_help') : i18n.t('research.works_menu_help')"
    :actions-label="mode === 'admin' ? i18n.t('works.workspace_actions') : ''"
  >
    <template v-if="mode === 'admin'" #actions>
      <UiButton
        variant="primary"
        size="small"
        icon="upload"
        :label="i18n.t('works.add_files')"
        :disabled="!props.canManageCorpus"
        :disabled-reason="props.corpusManageDeniedReason"
        @click="emit('chooseJsonl')"
      />
      <UiMenu :label="i18n.t('ui.more_actions')" :items="items" align="end" @select="onSelect" />
    </template>
  </UiPageHeader>
</template>
