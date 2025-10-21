<script setup>
import { inject, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";

import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import UploadModal from "@/components/payloads/UploadModal.vue";
import { useAbilityStore } from "@/stores/abilityStore";

const $api = inject("$api");

const abilityStore = useAbilityStore();
const coreDisplayStore = useCoreDisplayStore();
const { payloads } = storeToRefs(abilityStore);
const { modals } = storeToRefs(coreDisplayStore);

const structuredPayloads = computed(() => {
  const regex = /^(?:plugins\/([^/]+)|data)?\/payloads\/(.+)$/;
  return payloads.value.map(payload => {
    const match = payload.match(regex);
    if (!match) {
      console.error(`Payload path "${payload}" does not match the expected format.`);
      return null;
    }
    let belongsToAPlugin = match[1] !== undefined;
    return {
      fullPath: payload,
      belongsToAPlugin: match[1] !== undefined,
      pluginName: match[1] || null,
      fileName: match[2],
    };
  }).filter(Boolean);  // Remove null values
});

const pluginStructuredPayloads = computed(() => {
  return structuredPayloads.value.filter(payload => payload.belongsToAPlugin);
});

const nonPluginStructuredPayloads = computed(() => {
  return structuredPayloads.value.filter(payload => !payload.belongsToAPlugin);
});

onMounted(async () => {
    await abilityStore.getPayloads($api, true, false, true);
});

</script>

<template lang="pug">
.content
    h2 Payloads
    p
        | Payloads are any files that you can reference in ability executors.
        | They are transferred to an agent which can then use them.<br/>
        | You can only add or delete local payloads, not plugin ones.
hr

.content
    h2 Local Payloads
    .columns.mb-4
        .column.is-one-quarter.is-flex.buttons.mb-0
            button.button(@click="modals.payloads.showUpload = true")
                span.icon
                    font-awesome-icon(icon="fas fa-file-import")
                span Upload a payload
        .column.is-half.is-flex.is-justify-content-center
            span.tag.is-medium.m-0
                span.has-text-success
                strong
                    | {{ nonPluginStructuredPayloads.length }}
                    | payload{{ nonPluginStructuredPayloads.length === 0 || nonPluginStructuredPayloads.length > 1 ? 's' : '' }}
    table.table.is-striped.is-fullwidth.is-narrow
        thead
            tr
                th File name
                th File path
                th
        tbody
            tr.pointer(v-for="(payload, index) in nonPluginStructuredPayloads")
                td {{ payload.fileName }}
                td.is-four-fifths {{ payload.fullPath }}
                td.has-text-centered
                    button.delete.is-white(@click.stop="abilityStore.deletePayload($api, payload.fileName, true)")

.content
    h2 Plugin Payloads
    .columns.mb-4
        .column.is-full.is-flex.is-justify-content-center
            span.tag.is-medium.m-0
                span.has-text-success
                strong
                    | {{ pluginStructuredPayloads.length }}
                    | payload{{ pluginStructuredPayloads.length === 0 || pluginStructuredPayloads.length > 1 ? 's' : '' }}
    table.table.is-striped.is-fullwidth.is-narrow
        thead
            tr
                th File name
                th File path
                th Plugin Name
        tbody
            tr.pointer(v-for="payload in pluginStructuredPayloads")
                td {{ payload.fileName }}
                td.is-four-fifths {{ payload.fullPath }}
                td {{ payload.pluginName }}
UploadModal
</template>

<style scoped>
tr {
    cursor: pointer;
}

td.has-text-centered {
    width: 40px;
}
</style>
