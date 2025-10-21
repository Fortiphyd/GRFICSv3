<script setup>
import { storeToRefs } from "pinia";
import { ref, inject, onMounted, computed, watch } from "vue";
import { useCoreStore } from "../stores/coreStore";

const coreStore = useCoreStore();
const { mainConfig } = storeToRefs(coreStore);

const $api = inject("$api");

const settings = ref({});

watch(mainConfig, () => {
    let config = JSON.parse(JSON.stringify(mainConfig.value));
    delete config.plugins;
    settings.value = config;
});

onMounted(async () => {
    await coreStore.getMainConfig($api);
});

function isSettingChanged(setting) {
    return settings.value[setting] === mainConfig.value[setting];
}
</script>

<template lang="pug">
.content
    h2 Settings
hr

.is-flex.is-justify-content-center
    table
        tbody
            tr(v-for="setting in Object.keys(settings)")
                td.has-text-right.pt-3
                    span {{ setting }}
                td
                    .field.has-addons
                        .control
                            input.input(v-model="settings[setting]")
                        .control
                            button.button(@click="settings[setting] = mainConfig[setting]" v-tooltip="'Reset'" :disabled="isSettingChanged(setting)")
                                span.icon 
                                    font-awesome-icon(icon="fas fa-undo")
                        .control
                            button.button.is-primary(@click="coreStore.updateMainConfigSetting($api, setting, settings[setting])" :disabled="isSettingChanged(setting)") Update
</template>

<style scoped>
table {
    background-color: hsl(0deg, 0%, 14%);
    border-radius: 8px;
}

td {
    padding: 10px 25px;
}
</style>
