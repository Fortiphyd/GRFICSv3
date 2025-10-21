<script setup>
import { ref, inject, onMounted, watch } from "vue";
import { useAgentStore } from '../../stores/agentStore';
import { useAbilityStore } from '../../stores/abilityStore';
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { storeToRefs } from "pinia";
import { toast } from "bulma-toast";

const $api = inject("$api");

const agentStore = useAgentStore();
const { agentConfig } = storeToRefs(agentStore);
const abilityStore = useAbilityStore();
const { abilities } = storeToRefs(abilityStore);
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

let deployableAbilities = ref([]);
let selectedDeployableAbility = ref("");
let platforms = ref([]);
let selectedPlatform = ref("");
let deployCommands = ref([]);
let agentFieldConfig = ref({});
let agentFields = ref([]);
let filteredCommands = ref([]);

onMounted(async () => {
    await abilityStore.getAbilities($api);
});

watch(agentConfig, () => {
    findDeployableAbilities();
});

async function findDeployableAbilities() {
    await abilityStore.getAbilities($api);
    deployableAbilities.value = [];
    if (!agentConfig.value.deployments) return;
    agentConfig.value.deployments.forEach((abilityId) => {
        const match = abilities.value.find((ability) => ability.ability_id === abilityId);
        if (match) deployableAbilities.value.push(match);
    });
}

async function selectDeployableAbility() {
    // selectedDeployableAbility.value = deployableAbilities.value.find((ability) => ability.ability_id === selectedDeployableAbility.value.ability_id);
    platforms.value = [...new Set(selectedDeployableAbility.value.executors.map((executor) => executor.platform))];
    if (!platforms.value.includes(selectedPlatform.value)) {
        selectedPlatform.value = "";
    }

    try {
        const response = await $api.get(`/api/v2/deploy_commands/${selectedDeployableAbility.value.ability_id}`);
        deployCommands.value = response.data.abilities;
        agentFieldConfig.value = response.data.app_config;
        filterAbilityPlatforms();
    } catch(error) {
        console.error("Error loading the agent", error);
    }
}

function filterAbilityPlatforms() {
    filteredCommands.value = (selectedPlatform.value === "all") ? deployCommands.value : deployCommands.value.filter((ability) => ability.platform === selectedPlatform.value);
    let fields = [];
    agentFields.value = [];
    filteredCommands.value.forEach((command) => {
        fields = fields.concat([...command.command.matchAll(/#{(.*?)}/gm)].map((field) => field[1]));
        command.variations.forEach((variation) => {
            fields = fields.concat([...variation.command.matchAll(/#{(.*?)}/gm)].map((field) => field[1]));
        })
    });
    fields = [...new Set(fields)];
    fields.forEach((field) => {
        agentFields.value.push({ name: field, value: agentFieldConfig.value.hasOwnProperty(field) ? agentFieldConfig.value[field] : "" });
    });
}

function changePlatform(platform) {
    selectedPlatform.value = platform;
    filterAbilityPlatforms();
}

function getCommandField(command) {
    agentFields.value.forEach((field) => {
        command = command.replaceAll(`#{${field.name}}`, field.value);
    });
    return command;
}

function isSecureContext() {
    return window.isSecureContext;
}

function copyCommandToClipboard(command) {
    navigator.clipboard.writeText(command.replaceAll('\n', ''));
    toast({
        message: "Copied to clipboard",
        type: "is-success",
        position: "bottom-right",
        duration: 2000,
        dismissible: true,
        pauseOnHover: true,
    });
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.agents.showDeploy }")
    .modal-background(@click="modals.agents.showDeploy = false")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title Deploy an agent 
        .modal-card-body 
            form.has-text-centered
                .field
                    label.label Agent 
                    .control 
                        .select 
                            select(v-model="selectedDeployableAbility" @change="selectDeployableAbility()")
                                option(disabled selected value="") Choose an agent 
                                option(v-for="ability in deployableAbilities" :key="ability.ability_id" :value="ability") {{ `${ability.name} | ${ability.description}` }}
                .field(v-if="selectedDeployableAbility.ability_id")
                    label.label Platform 
                    .control.is-flex.is-justify-content-center
                        .has-text-centered.platform(v-if="selectedPlatform" :class="{ 'selected': selectedPlatform === 'all' }" @click="changePlatform('all')")
                            span.icon.is-large
                                font-awesome-icon(icon="far fa-circle").fa-2x
                            br
                            span all
                        .has-text-centered.platform(v-if="platforms.includes('linux')" :class="{ 'selected': selectedPlatform === 'linux' }" @click="changePlatform('linux')")
                            span.icon.is-large
                                font-awesome-icon(icon="fab fa-linux").fa-2x
                            br
                            span linux
                        .has-text-centered.platform(v-if="platforms.includes('windows')" :class="{ 'selected': selectedPlatform === 'windows' }" @click="changePlatform('windows')")
                            span.icon.is-large
                                font-awesome-icon(icon="fab fa-windows").fa-2x
                            br
                            span windows
                        .has-text-centered.platform(v-if="platforms.includes('darwin')" :class="{ 'selected': selectedPlatform === 'darwin' }" @click="changePlatform('darwin')")
                            span.icon.is-large
                                font-awesome-icon(icon="fab fa-apple").fa-2x
                            br
                            span darwin
            form.mt-4
                div(v-for="field in agentFields" :key="field.name")
                    .field.is-horizontal.mb-2
                        .field-label 
                            label.label {{ field.name }}
                        .field-body
                            .field.has-addons
                                .control.is-expanded
                                    input.input(type="text" v-model="field.value")
                                .control 
                                    a.button.has-tooltip-arrow(title="Reset to default" @click="field.value = agentFieldConfig[field.name]")
                                        span.icon
                                            font-awesome-icon(icon="fas fa-undo")
            hr(v-if="filteredCommands.length")
            .command-container.container(v-for="command in filteredCommands" :key="command.command")
                .tags.are-medium.has-addons.mb-0
                    span.tag.is-black
                        span.icon 
                            font-awesome-icon(v-if="command.platform === 'windows'" icon="fab fa-windows")
                            font-awesome-icon(v-if="command.platform === 'darwin'" icon="fab fa-apple")
                            font-awesome-icon(v-if="command.platform === 'linux'" icon="fab fa-linux")
                        span {{ command.platform }}
                    span.tag {{ command.executor }}
                p.mb-3 {{ command.description }}
                .box.p-0
                    pre.m-0.pt-2.pb-0 {{ getCommandField(command.command) }}
                    a.button.is-outlined.is-fullwidth.cmd-copy-button(v-if="isSecureContext()" @click="copyCommandToClipboard(getCommandField(command.command))")
                        span.icon 
                            font-awesome-icon(icon="far fa-copy").fa-lg
                        span Copy
                p.has-text-centered.mb-4(v-if="command.variations.length") 
                    strong Variations
                .content(v-for="variation in command.variations" :key="variation.command")
                    .tags.are-medium.has-addons.mb-0
                        span.tag.is-black
                            span.icon 
                                font-awesome-icon(v-if="command.platform === 'windows'" icon="fab fa-windows")
                                font-awesome-icon(v-if="command.platform === 'darwin'" icon="fab fa-apple")
                                font-awesome-icon(v-if="command.platform === 'linux'" icon="fab fa-linux")
                            span {{ command.platform }}
                        span.tag {{ command.executor }}
                    p {{ variation.description }}
                    .box.p-0
                        pre.m-0.pt-2.pb-0 {{ getCommandField(variation.command) }}
                        a.button.is-outlined.is-fullwidth.cmd-copy-button(v-if="isSecureContext()" @click="copyCommandToClipboard(getCommandField(variation.command))")
                            span.icon 
                                font-awesome-icon(icon="far fa-copy").fa-lg
                            span Copy
        footer.modal-card-foot.is-flex.is-justify-content-flex-end 
            button.button(@click="modals.agents.showDeploy = false") Close
    </template>

<style scoped>
pre {
    scrollbar-color: #3f3f3f #0000;
    scrollbar-width: thin;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

.command-container {
    border-radius: 2px;
    margin: 30px;
}

.is-white {
    background-color: #636363;
}
.is-white:hover {
    background-color: #505050 !important;
}

.cmd-copy-button {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
}

.modal-card {
    width: 800px;
}

.platform {
    width: 80px;
    border-radius: 4px;
    padding: 5px;
    margin: 5px;
    font-family: monospace;
    border: 1px solid transparent;
}
.platform:hover {
    background-color: #484848;
    cursor: pointer;
}
.platform.selected {
    border: 1px solid white;
}
</style>
