<script setup>
import { storeToRefs } from "pinia";
import { inject, onMounted } from "vue";
import { useCoreStore } from "../stores/coreStore";

const coreStore = useCoreStore();
const { planners } = storeToRefs(coreStore);

const $api = inject("$api");

onMounted(async () => {
    await coreStore.getPlanners($api);
});
</script>

<template lang="pug">
.content
    h2 Planners
    p A planner is a module which contains logic for how a running operation should make decisions about 
        | which abilities to use and in what order. Specifically, a planner's logic contains the decision making 
        | to execute a single phase of an operation.
hr

.is-flex.is-justify-content-center
    #planners.content
        .card.block.p-4(v-for="planner in planners")
            h3 {{ planner.name }}
            p {{ planner.description }}


</template>

<style scoped>
#planners {
    max-width: 800px;
}
</style>
