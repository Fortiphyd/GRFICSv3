<script setup>
import { ref, inject, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { useOperationStore } from '../../stores/operationStore';
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
const operationStore = useOperationStore();
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.operations.showDetails }")
    .modal-background(@click="modals.operations.showDetails = false")
    .modal-card
        header.modal-card-head 
            p.modal-card-title Operation Details
        .modal-card-body(v-if="operationStore.selectedOperationID")
            table.table.is-fullwidth.is-striped
                tbody
                    tr
                        th Name
                        td {{`${operationStore.operations[operationStore.selectedOperationID].name}`}}
                    tr
                        th Adversary
                        td {{`${operationStore.operations[operationStore.selectedOperationID].adversary.name}`}}
                    tr
                        th Fact Source
                        td {{`${operationStore.operations[operationStore.selectedOperationID].source.name}`}}
                    tr
                        th Group
                        td {{operationStore.operations[operationStore.selectedOperationID].group || "all"}}
                    tr
                        th Planner
                        td {{`${operationStore.operations[operationStore.selectedOperationID].planner.name}`}}
                    tr
                        th Obfuscator
                        td {{`${operationStore.operations[operationStore.selectedOperationID].obfuscator}`}}
                    tr
                        th Autonomous
                        td {{operationStore.operations[operationStore.selectedOperationID].autonomous ? "autonomous" : "manual"}}
                    tr
                        th Parser
                        td {{`${operationStore.operations[operationStore.selectedOperationID].use_learning_parsers}`}}
                    tr
                        th Auto Close
                        td {{`${operationStore.operations[operationStore.selectedOperationID].auto_close}`}}
                    tr
                        th Jitter
                        td {{`${operationStore.operations[operationStore.selectedOperationID].jitter}`}}
        footer.modal-card-foot.is-justify-content-right
            button.button(@click="modals.operations.showDetails = false") Close 
            
</template>
