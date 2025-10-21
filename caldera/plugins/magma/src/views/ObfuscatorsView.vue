<script setup>
import { storeToRefs } from "pinia";
import { inject, onMounted } from "vue";
import { useCoreStore } from "../stores/coreStore";

const coreStore = useCoreStore();
const { obfuscators } = storeToRefs(coreStore);

const $api = inject("$api");

onMounted(async () => {
    await coreStore.getObfuscators($api);
});
</script>

<template lang="pug">
.content
    h2 Obfuscators
    p Obfuscators are designed for evasion When running an operation, you can select an obfuscator. By default, plain-text is
        | selected. During the operation, before the agent collects an instruction, the server will wrap it
        | with the obfuscation technique chosen - including instructions for how to unpack it
        | before execution.
hr

.is-flex.is-justify-content-center
    #obfuscators.content
        .card.block.p-4(v-for="obfuscator in obfuscators")
            h3 {{ obfuscator.name }}
            p {{ obfuscator.description }}


</template>

<style scoped>
#obfuscators {
    max-width: 800px;
}
</style>
