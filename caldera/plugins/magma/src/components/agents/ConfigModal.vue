<script setup>
import { ref, reactive, inject} from "vue";
import { useAgentStore } from "../../stores/agentStore";
import { useAbilityStore } from "../../stores/abilityStore";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { storeToRefs } from "pinia";



const $api = inject("$api");

const agentStore = useAgentStore();
const { agentConfig } = storeToRefs(agentStore);
const abilityStore = useAbilityStore();
const { abilities } = storeToRefs(abilityStore);
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

let isAddingBootstrapAbility = ref(false);
let isAddingDeadmanAbility = ref(false);
let abilitySearchQuery = ref("");
let abilitySearchResults = ref([]);

let validation = reactive({
    beaconTimer: "",
    watchdogTimer: "",
    untrustedTimer: "",
    implantName: ""
});

function validateAndSave() {
    // Validate beacon timers
    if (agentConfig.value.sleep_min > agentConfig.value.sleep_max) {
        validation.beaconTimer = "Beacon min must be less than or equal to beacon max";
    } else if (agentConfig.value.sleep_min < 0) {
        validation.beaconTimer = "Beacon min must be greater than or equal to 0";
    } else if (agentConfig.value.sleep_max < 0) {
        validation.beaconTimer = "Beacon max must be greater than or equal to 0";
    } else if (!agentConfig.value.sleep_min || !agentConfig.value.sleep_max) {
        validation.beaconTimer = "Beacon min and max cannot be empty";
    } else {
        validation.beaconTimer = "";
    }
    // Validate watchdog
    if ((agentConfig.value.watchdog !== 0 && !agentConfig.value.watchdog) || agentConfig.value.watchdog < 0) {
        validation.watchdogTimer = "Watchdog timer must be greater than or equal to 0";
    } else {
        validation.watchdogTimer = "";
    }
    // Validate untrusted
    if ((agentConfig.value.untrusted_timer !== 0 && !agentConfig.value.untrusted_timer) || agentConfig.value.untrusted_timer < 0) {
        validation.untrustedTimer = "Untrusted timer must be greater than or equal to 0";
    } else {
        validation.untrustedTimer = "";
    }
    // Implant name
    if (!agentConfig.value.implant_name) {
        validation.implantName = "Implant name cannot be empty";
    } else {
        validation.implantName = "";
    }

    // If there are no errors in inputs, save
    if (!validation.beaconTimer && !validation.watchdogTimer && !validation.untrustedTimer && !validation.implantName) {
        agentStore.saveConfig($api);
        modals.value.agents.showConfig = false;
    }
}

function getAbilityName(id) {
    let ability = abilities.value.find((ab) => ab.ability_id === id);
    return (id && abilities.value.length && ability) ? ability.name : '[unknown]';
}

function searchAbilitiesByName(searchTerm, limit = 10) {
    if (!searchTerm) return [];
    if (searchTerm.includes('"') || searchTerm.includes("'")){
        let newSearchTerm = searchTerm.replace(/"/g, '').replace(/'/g, '')
        return abilities.value
        .filter((ability) => ability.name.toLowerCase().startsWith(newSearchTerm.toLowerCase()))
        .splice(0, limit);
    } else{
        return abilities.value
        .filter((ability) => ability.name.toLowerCase().includes(searchTerm.toLowerCase()))
        .splice(0, limit);
    }
}

function addBootstrapAbility(id) {
    agentConfig.value.bootstrap_abilities.push(id);
    abilitySearchQuery.value = "";
    abilitySearchResults.value = [];
    isAddingBootstrapAbility.value = false;
}

function addDeadmanAbility(id) {
    if (!agentConfig.value.deadman_abilities) {
        agentConfig.value.deadman_abilities = [];
    }
    agentConfig.value.deadman_abilities.push(id);
    abilitySearchQuery.value = "";
    abilitySearchResults.value = [];
    isAddingDeadmanAbility.value = false;
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.agents.showConfig }")
    .modal-background(@click="modals.agents.showConfig = false")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title Agent Configuration
        .modal-card-body 
            table
                col(width="35%")
                col(width="65%")
                tbody
                    tr
                        th Beacon Timers (sec)
                        td
                            .is-flex.is-align-items-center 
                                label.mr-3 min
                                input.input.mr-4(v-model="agentConfig.sleep_min" type="number" placeholder="30" min="0" :max="agentConfig.sleep_max" :class="{ 'is-danger': validation.beaconTimer }")
                                label.mr-3 max
                                input.input(v-model="agentConfig.sleep_max" type="number" placeholder="60" :min="agentConfig.sleep_min" :class="{ 'is-danger': validation.beaconTimer }")
                            p.help.has-text-danger(v-if="validation.beaconTimer") {{ validation.beaconTimer }}
                    tr
                        th Watchdog Timer (sec)
                        td
                            input.input(v-model="agentConfig.watchdog" type="number" placeholder="0" min="0" :class="{ 'is-danger': validation.watchdogTimer }")
                            p.help.has-text-danger(v-if="validation.watchdogTimer") {{ validation.watchdogTimer }}
                    tr
                        th Untrusted Timer (sec) *
                        td
                            input.input(v-model="agentConfig.untrusted_timer" type="number" placeholder="90" min="0" :class="{ 'is-danger': validation.untrustedTimer }")
                            p.help.has-text-danger(v-if="validation.untrustedTimer") {{ validation.untrustedTimer }}
                    tr
                        th Implant Name
                        td
                            input.input(v-model="agentConfig.implant_name" type="text" placeholder="splunkd" :class="{ 'is-danger': validation.implantName }")
                            p.help.has-text-danger(v-if="validation.implantName") {{ validation.implantName }}
                    tr
                        th Bootstrap Abilities 
                                    img(src="../../assets/img/info-icon.png" alt="info-icon" style="width:10%; margin-left:10px;" title="For exact search start your search query with \"")
                        td
                            .field.is-grouped.is-grouped-multiline
                                .control(v-for="(abilityId, index) of agentConfig.bootstrap_abilities")
                                    .tags.has-addons
                                        a.tag.is-info {{ getAbilityName(abilityId) }}
                                        a.tag.is-delete(@click="agentConfig.bootstrap_abilities.splice(index, 1)")
                                .control 
                                    .tag.p-0
                                        a.tag.is-primary(v-if="!isAddingBootstrapAbility" @click="isAddingBootstrapAbility = true; isAddingDeadmanAbility = false;")
                                            span.icon 
                                                font-awesome-icon(icon="fas fa-plus")
                            .field.has-addons(v-if="isAddingBootstrapAbility")
                                .control.is-expanded.auto-complete()
                                    input.input(v-model="abilitySearchQuery" placeholder="Search for an ability..." @keyup="abilitySearchResults = searchAbilitiesByName(abilitySearchQuery)")
                                    .search-results.is-size-7(v-if="abilitySearchResults")
                                        p(v-for="result of abilitySearchResults" :key="result.ability_id" @click="addBootstrapAbility(result.ability_id)") {{ result.name }}
                                .control 
                                    a.button(@click="isAddingBootstrapAbility = false") Cancel
                    tr
                        th Deadman Abilities
                            img(src="../../assets/img/info-icon.png" alt="info-icon" style="width:10%; margin-left:10px;" title="For exact search start your search query with \"")
                        td
                            .field.is-grouped.is-grouped-multiline
                                .control(v-for="(abilityId, index) of agentConfig.deadman_abilities")
                                    .tags.has-addons
                                        a.tag.is-info {{ getAbilityName(abilityId) }}
                                        a.tag.is-delete(@click="agentConfig.deadman_abilities.splice(index, 1)")
                                .control 
                                    .tag.p-0
                                        a.tag.is-primary(v-if="!isAddingDeadmanAbility" @click="isAddingDeadmanAbility = true; isAddingBootstrapAbility = false;")
                                            span.icon 
                                                font-awesome-icon(icon="fas fa-plus")
                            .field.has-addons(v-if="isAddingDeadmanAbility")
                                .control.is-expanded.auto-complete()
                                    input.input(v-model="abilitySearchQuery" placeholder="Search for an ability..." @keyup="abilitySearchResults = searchAbilitiesByName(abilitySearchQuery)")
                                    .search-results.is-size-7(v-if="abilitySearchResults")
                                        p(v-for="result of abilitySearchResults" :key="result.ability_id" @click="addDeadmanAbility(result.ability_id)") {{ result.name }}
                                .control 
                                    a.button(@click="isAddingDeadmanAbility = false") Cancel
            p.help * A global setting that will effect any new or existing agents.
        footer.modal-card-foot.is-flex.is-justify-content-flex-end 
            button.button(@click="modals.agents.showConfig = false") Close
            button.button.is-primary(@click="validateAndSave()")
                span.icon 
                    font-awesome-icon(icon="fas fa-save") 
                span Save
</template>

<style scoped>
table {
    border-collapse: separate;
    border-spacing: 10px;
}

.auto-complete:active .search-results, .auto-complete:focus-within .search-results {
    border-top: 1px solid #363636 !important;
    border: 1px solid var(--primary-color);
}

.search-results {
    overflow-y: scroll;
    max-height: 400%;
    background-color: #262626;
    position: absolute;
    z-index: 5;
    width: 100%;
    border-top: none;
    margin-top: -2px;
    border-radius: 0;
}
.search-results p {
    margin-bottom: 0 !important;
    padding: 5px;
    cursor: pointer !important;
}
.search-results p:hover {
    background-color: #484848;
}
</style>
