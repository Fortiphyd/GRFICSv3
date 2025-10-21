<script setup>
import { inject, onMounted } from "vue";
import { useCoreStore } from "../stores/coreStore";
import { storeToRefs } from "pinia";

const $api = inject("$api");

const coreStore = useCoreStore();
const { contacts } = storeToRefs(coreStore);
const { availableContacts } = storeToRefs(coreStore);

onMounted(async () => {
  await coreStore.getContacts($api);
  await coreStore.getAvailableContacts($api);
});

async function downloadReport(contact) {
  await coreStore.downloadContactReport($api, contact);
}
</script>

<template lang="pug">
.content
    h2 Contacts
    p #[strong Contacts are touch points for agents.] A contact is a connection point on the server for agents to communicate through. 
      | Agents can be custom written against one (or multiple) contacts. Each contact logs all agent connections - and all commands it hands out. Download a report for any contact below.

hr

table.table.is-striped.is-fullwidth
    tbody
        template(v-for="(contact) of contacts" :key="contact.name")
            tr
                th {{ contact.name }}
                td {{ contact.description }}
                td
                    template(v-if="!availableContacts.includes(contact.name.toUpperCase())")
                        button.button.is-small(disabled) No report available
                    template(v-else)
                        button.button.is-small.is-primary(@click="downloadReport(contact.name)")
                            span.icon
                              font-awesome-icon(icon="fas fa-download")
                            span Download Report

</template>
