<script setup>
import { inject } from "vue";
import { storeToRefs } from "pinia";

import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { useOperationStore } from '../../stores/operationStore';

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
const operationStore = useOperationStore();

async function deleteOperation() {
    await operationStore.deleteOperation($api, operationStore.selectedOperationID);
    modals.value.operations.showDelete = false;
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.operations.showDelete }")
    .modal-background(@click="modals.operations.showDelete = false")
    .modal-card
        header.modal-card-head 
            p.modal-card-title Delete Operation?
        .modal-card-body(v-if="operationStore.currentOperation")
            p Are you sure you want to delete the operation "{{ operationStore.currentOperation.name }}"? This cannot be undone.
        footer.modal-card-foot.has-text-right
            button.button(@click="modals.operations.showDelete = false") Cancel 
            button.button.is-danger(@click="deleteOperation()") 
                span.icon
                    font-awesome-icon(icon="fa-trash")
                span Delete
            
</template>

<style scoped>
.modal-card-foot {
    display: block;
}
</style>
