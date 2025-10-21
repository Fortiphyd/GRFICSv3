<script setup>
import { inject, ref } from "vue";
import { storeToRefs } from "pinia";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { useOperationStore } from "../../stores/operationStore";
const $api = inject("$api");
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
const operationStore = useOperationStore();
let reportType = ref(1);
let isAgentOutput = ref(false);

async function downloadOperation() {
  await operationStore.downloadOperationInfo(
    $api,
    reportType.value,
    operationStore.selectedOperationID,
    isAgentOutput.value
  );
  modals.value.operations.showDownload = false;
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.operations.showDownload }")
    .modal-background(@click="modals.operations.showDownload = false")
    .modal-card
        header.modal-card-head 
            p.modal-card-title Operation Reports
        .modal-card-body
            form(@submit.prevent)
                .field.is-horizontal 
                    label.label.checkbox
                        input(type="checkbox" v-model="isAgentOutput")
                        span.ml-2 Include agent output 
                .field.is-horizontal
                    input.is-checkradio(:checked="reportType == 0 ? true : false" type="radio" id="full" @click="reportType = 0")
                    label.label.ml-3.mt-1(for="full") Full Report
                    input.is-checkradio.ml-3(:checked="reportType == 1 ? true : false" type="radio" id="event" @click="reportType = 1")
                    label.label.ml-3.mt-1(for="event") Event Logs
                    input.is-checkradio.ml-3(:checked="reportType == 2 ? true : false" type="radio" id="csv" @click="reportType = 2")
                    label.label.ml-3.mt-1(for="csv") CSV
        footer.modal-card-foot.has-text-right
            button.button(@click="modals.operations.showDownload = false") Cancel 
            button.button.is-primary(@click="downloadOperation()") 
                span.icon
                    font-awesome-icon(icon="fa-download")
                span Download     
</template>

<style scoped>
.modal-card-foot {
  display: block;
}
</style>
