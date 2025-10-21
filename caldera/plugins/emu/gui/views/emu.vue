<script setup>
import { inject, ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { useAbilityStore } from "@/stores/abilityStore.js";
import { useAdversaryStore } from "@/stores/adversaryStore.js";

const abilityStore = useAbilityStore();
const { abilities } = storeToRefs(abilityStore);
const adversaryStore = useAdversaryStore();
const { adversaries } = storeToRefs(adversaryStore);
const $api = inject("$api");

onMounted(async () => {
  await abilityStore.getAbilities($api);
  await adversaryStore.getAdversaries($api);
});
const emuAbilities = computed(() =>
  abilities.value.filter((ability) => ability.plugin === "emu")
);
const emuAdversaries = computed(() =>
  adversaries.value.filter((adversary) => adversary.plugin === "emu")
);
</script>

<template lang="pug">
.content    
    h2 Emu
    p The collection of abilities from the CTID Adversary Emulation Plans
hr

.is-flex.is-align-items-center.is-justify-content-center
    .card.is-flex.is-flex-direction-column.is-align-items-center.p-4.m-4
        h1.is-size-1.mb-0 {{ emuAbilities.length || "---" }}
        p abilities
        router-link.button.is-primary.mt-4(to="/abilities?plugin=emu") 
            span View Abilities
            span.icon
                font-awesome-icon(icon="fas fa-angle-right")
.is-flex.is-align-items-center.is-justify-content-center
    .card.is-flex.is-flex-direction-column.is-align-items-center.p-4.m-4
        h1.is-size-1.mb-0 {{ emuAdversaries.length || "---" }}
        p adversaries
        router-link.button.is-primary.mt-4(to="/adversaries?plugin=emu") 
            span View Adversaries
            span.icon
                font-awesome-icon(icon="fas fa-angle-right")

</template>
