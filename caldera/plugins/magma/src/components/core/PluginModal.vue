<script setup>
import { ref, inject } from "vue";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { storeToRefs } from "pinia";

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);


async function enablePlugin() {
    try {
        await $api.patch('/api/v2/config/main', {
            value: coreDisplayStore.modals.core.selectedPlugin,
            prop: 'plugin'
        });
    } catch(error) {
        console.error(`Error enabling ${coreDisplayStore.modals.core.selectedPlugin}`);
    }

    coreDisplayStore.modals.core.showPluginPopup = false;
}

</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.core.showPluginPopup }")
    .modal-background(@click="modals.core.showPluginPopup = false")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title Enable Plugin
        .modal-card-body 
            br
            p.block "{{ coreDisplayStore.modals.core.selectedPlugin }}" plugin is currently disabled. Would you like to enable it?
            p Note: Enabling the plugin will require you to restart Caldera
            br

        footer.modal-card-foot.is-flex.is-justify-content-flex-end 
            button.button(@click="modals.core.showPluginPopup = false") Cancel
            button.button.is-primary(@click="enablePlugin") Confirm
    </template>