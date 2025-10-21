<script setup>
import { inject, computed, watch, ref, onMounted } from "vue";

import { useOperationStore } from '../../stores/operationStore';
import { b64DecodeUnicode } from "@/utils/utils";

const props = defineProps({
    link: Object
});

const $api = inject("$api");

const operationStore = useOperationStore();

const facts = computed(() => props.link.facts);

let stdout = ref("");
let stderr = ref("");

watch(props.link, getLinkOutput);

onMounted(() => {
    getLinkOutput();
});

async function getLinkOutput() {
    if (props.link.output !== "True") return;
    try {
        const response = await $api.get(`/api/v2/operations/${operationStore.selectedOperationID}/links/${props.link.id}/result`);
        const result = JSON.parse(b64DecodeUnicode(response.data.result));
        stdout.value = result.stdout;
        stderr.value = result.stderr;
    } catch (error) {
        console.error("Error getting link results", error);
    }
}
</script>

<template lang="pug">
label.label Facts
.box.p-0(v-if="facts.length")
    table.table.is-fullwidth
        thead
            tr
                th Name
                th Value
                th Score
        tbody
            tr(v-for="fact in facts")
                td {{ fact.name }}
                td {{ fact.value }}
                td {{ fact.score }}
span.is-family-monospace.is-size-7(v-else) No facts collected

label.label.mt-2 Standard Output
.box.p-0(v-if="stdout")
    pre.m-0.pt-2.pb-2 {{ stdout }}
span.is-family-monospace.is-size-7(v-else) Nothing to show

label.label.mt-2 Standard Error
template
.box.p-0(v-if="stderr")
    pre.m-0.pt-2.pb-2 {{ stderr }}
span.is-family-monospace.is-size-7(v-else) Nothing to show
</template>
