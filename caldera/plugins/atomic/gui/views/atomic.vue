<script setup>
import { inject, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { useAbilityStore } from '@/stores/abilityStore.js';
import { useAdversaryStore } from '@/stores/adversaryStore.js';

const $api = inject("$api");

const abilityStore = useAbilityStore();
const { abilities } = storeToRefs(abilityStore);
const adversaryStore = useAdversaryStore();
const { adversaries } = storeToRefs(adversaryStore);

onMounted(async () => {
    await abilityStore.getAbilities($api);
    await adversaryStore.getAdversaries($api);
});

const atomicAbilities = computed(() => abilities.value.filter((ability) => ability.plugin === "atomic"));
</script>

<template lang="pug">
.content    
    h2 Atomic
    p The collection of abilities in the Red Canary Atomic test project.
hr

.is-flex.is-align-items-center.is-justify-content-center
    .card.is-flex.is-flex-direction-column.is-align-items-center.p-4.m-4
        h1.is-size-1.mb-0 {{ atomicAbilities.length || "---" }}
        p abilities
        router-link.button.is-primary.mt-4(to="/abilities?plugin=atomic") 
            span View Abilities
            span.icon
                font-awesome-icon(icon="fas fa-angle-right")

</template>