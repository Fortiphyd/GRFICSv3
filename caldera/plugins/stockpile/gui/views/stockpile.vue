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

const stockpileAbilities = computed(() => abilities.value.filter((ability) => ability.plugin === "stockpile"));
const stockpileAdversaries = computed(() => adversaries.value.filter((adversary) => adversary.plugin === "stockpile"));
</script>

<template lang="pug">
.content    
    h2 Stockpile
    p The stockpile plugin contains a collection of TTPs (abilities), adversary profiles, data sources and planners. These can be used to construct dynamic operations against targeted hosts.
hr

.is-flex.is-align-items-center.is-justify-content-center
    .card.is-flex.is-flex-direction-column.is-align-items-center.p-4.m-4
        h1.is-size-1.mb-0 {{ stockpileAbilities.length || "---" }}
        p abilities
        router-link.button.is-primary.mt-4(to="/abilities?plugin=stockpile") 
            span View Abilities
            span.icon
                font-awesome-icon(icon="fas fa-angle-right")
    .card.is-flex.is-flex-direction-column.is-align-items-center.p-4.m-4
        h1.is-size-1.mb-0 {{ stockpileAdversaries.length || "---" }}
        p adversaries
        router-link.button.is-primary.mt-4(to="/adversaries") 
            span View Adversaries
            span.icon
                font-awesome-icon(icon="fas fa-angle-right")
</template>