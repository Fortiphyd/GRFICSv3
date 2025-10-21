<script setup>
import { storeToRefs } from "pinia";
import { reactive, ref, inject, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { useAbilityStore } from "@/stores/abilityStore";
import { getAbilityPlatforms } from "@/utils/abilityUtil.js";
import CreateEditAbility from "@/components/abilities/CreateEditAbility.vue";

const $api = inject("$api");
const route = useRoute();

const abilityStore = useAbilityStore();
const { abilities, tactics, techniques, plugins, platforms } = storeToRefs(abilityStore);

let filters = reactive({
    searchQuery: "",
    tactic: "",
    technique: "",
    plugin: "",
    platform: ""
});

let isCreatingAbility = ref(false);
let showAbilityModal = ref(false);
let selectedAbility = ref({});

const filteredAbilities = computed(() => {
    return abilities.value.filter((ability) => (
        (ability.name.toLowerCase().includes(filters.searchQuery.toLowerCase()))
        && (!filters.tactic || ability.tactic === filters.tactic)
        && (!filters.technique || `${ability.technique_id} | ${ability.technique_name}` === filters.technique)
        && (!filters.plugin || ability.plugin === filters.plugin)
        && (!filters.platform || getAbilityPlatforms(ability).indexOf(filters.platform) >= 0)
    ));
});

onMounted(async () => {
    await abilityStore.getAbilities($api);
    filters.plugin = route.query.plugin || "";
});

function clearFilters() {
    Object.keys(filters).forEach((k) => filters[k] = "");
}


function selectAbility(ability, creating) {
    selectedAbility.value = ability;
    isCreatingAbility.value = creating;
    showAbilityModal.value = true;
}
</script>

<template lang="pug">
//- Header
.content
    h2 Abilities
    p An ability is a specific ATT&CK tactic/technique implementation which can be executed on running agents. Abilities will include the command(s) to run, the platforms / executors the commands can run on (ex: Windows / PowerShell), payloads to include, and a reference to a module to parse the output on the Caldera server.
hr

.columns
    .column.is-2.m-0
        button.button.is-primary.is-fullwidth.mb-4(@click="selectAbility({}, true)")
            span.icon
                font-awesome-icon(icon="fas fa-plus")
            span Create an Ability
        form
            .field
                .control.has-icons-left
                    input.input.is-small(v-model="filters.searchQuery" type="text" placeholder="Find an ability...")
                    span.icon.is-left
                        font-awesome-icon(icon="fas fa-search")
            .field
                label.label Tactic 
                .control
                    .select.is-fullwidth
                        select(v-model="filters.tactic")
                            option(value="") All 
                            option(v-for="tactic in tactics" :value="tactic") {{ tactic }}    
            .field
                label.label Technique 
                .control
                    .select.is-fullwidth
                        select(v-model="filters.technique")
                            option(value="") All 
                            option(v-for="technique in techniques" :value="technique") {{ technique }}   
            .field
                label.label Plugin 
                .control
                    .select.is-fullwidth
                        select(v-model="filters.plugin")
                            option(value="") All 
                            option(v-for="plugin in plugins" :value="plugin") {{ plugin }}   
            .field
                label.label Platform 
                .control
                    .select.is-fullwidth
                        select(v-model="filters.platform")
                            option(value="") All 
                            option(v-for="platform in Object.keys(platforms)" :value="platform") {{ platform }}   
        button.button.is-fullwidth.mt-4(@click="clearFilters()") Clear Filters
        p.mt-2.has-text-centered
            strong {{ filteredAbilities.length }}&nbsp;
            | / {{ abilities.length }} abilities
    .column.is-10.m-0.is-flex.is-flex-wrap-wrap.is-align-content-flex-start
        .box.mb-2.mr-2.p-3.ability(v-for="ability in filteredAbilities" @click="selectAbility(ability, false)" :key="ability.ability_id")
            .is-flex.is-justify-content-space-between.is-align-items-center.mb-1
                .is-flex
                    span.tag.is-small.mr-3 {{ ability.tactic }} 
                p.help.mt-0 {{ ability.technique_id }} - {{ ability.technique_name }}
            strong {{ ability.name }}
            p.help.mb-0 {{ ability.description }}   

//- Modals
CreateEditAbility(:ability="selectedAbility" :active="showAbilityModal" :creating="isCreatingAbility" @close="showAbilityModal = false")
</template>

<style scoped>
@media(max-width: 1200px) {
    .box.ability {
        width: 98%;
    }
}
@media(min-width: 1200px) {
    .box.ability {
        width: 48%;
    }
}
.box.ability {
    position: relative;
    cursor: pointer;
    border: 1px solid transparent;
    background-color: #272727;
}
.box.ability:hover {
    border: 1px solid #474747;
}

.abilities {
    overflow-x: hidden;
}
</style>
