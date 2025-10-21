<script setup>
import { ref, inject } from "vue";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { storeToRefs } from "pinia";
import { useAdversaryStore } from "../../stores/adversaryStore";

const $api = inject("$api");

const adversaryStore = useAdversaryStore();
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

let importFile = ref({});
let importFileContent = ref({});

function uploadImportFile(event) {
    let el = event.target;
    if (!el.files || !el.files.length) return;
    importFile.value = el.files[0];
    const reader = new FileReader();
    reader.onload = (event) => importFileContent.value = event.target.result;
    reader.readAsText(importFile.value);
}

function importAdversary() {
    let newProfile = {};
    let lastKey;
    importFileContent.value.split("\n").forEach((line) => {
        // Remove comments
        line = line.split('#')[0];
        // Line has a key-value pair
        let keyValSplit = line.split(':');
        if (keyValSplit.length >= 2) {
            if (keyValSplit[1]) {
                newProfile[keyValSplit[0]] = keyValSplit[1].trim();
            } else {
                lastKey = keyValSplit[0];
                newProfile[lastKey] = [];
            }
        }
        // Line is a list item
        if (line.trim()[0] === '-' && line.trim() !== '---') {
            newProfile[lastKey].push(line.replace('-', '').trim());
        }
    });
    
    adversaryStore.createAdversary($api, newProfile);
    importFile.value = {};
    importFileContent.value = {};
    modals.value.adversaries.showImport = false;
}
</script>
    
<template lang="pug">
.modal(:class="{ 'is-active': modals.adversaries.showImport }")
    .modal-background(@click="modals.adversaries.showImport = false")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title Import Adversary
        .modal-card-body 
            p.block Import an adversary in YAML format. Export any existing adversary to see the required format.
            .file.has-name.is-fullwidth
                label.file-label
                    input.file-input(accept=".yml,.yaml" type="file" @change="uploadImportFile")
                    span.file-cta
                        span.file-icon 
                            font-awesome-icon(icon="fas fa-upload")
                        span.file-label Choose a file...
                    span.file-name {{ importFile ? importFile.name : '' }}
        footer.modal-card-foot.is-flex.is-justify-content-flex-end 
            button.button(@click="modals.adversaries.showImport = false") Close
            button.button.is-primary(@click="importAdversary()")
                span.icon 
                    font-awesome-icon(icon="fas fa-save") 
                span Import
</template>
