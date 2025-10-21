<script setup>
import { ref, inject, onMounted } from "vue";
import { storeToRefs } from "pinia";

import { useAdversaryStore } from "@/stores/adversaryStore.js";
import GoalsTable from "@/components/objectives/GoalsTable.vue";

const $api = inject("$api");

const adversaryStore = useAdversaryStore();
const { objectives, selectedObjective } = storeToRefs(adversaryStore);

let isEditingNameDesc = ref(false);
let newObjectiveName = ref("");
let newObjectiveDescription = ref("");

onMounted(async () => {
    await adversaryStore.getObjectives($api);
});

function editNameDesc() {
    newObjectiveName.value = selectedObjective.value.name;
    newObjectiveDescription.value = selectedObjective.value.description;
    isEditingNameDesc.value = true;
}

async function saveObjective() {
    selectedObjective.value.name = newObjectiveName.value;
    selectedObjective.value.description = newObjectiveDescription.value;
    await adversaryStore.saveObjective($api);
    isEditingNameDesc.value = false;
}
</script>

<template lang="pug">
.columns.mb-0
    .column.is-4.m-0.content
        h2.m-0 Objectives
    .column.is-4.m-0
        .is-flex.is-justify-content-center.is-flex-wrap-wrap
            .control.mr-2
                .select
                    select.has-text-centered(v-model="selectedObjective" )
                        option(disabled selected value="") Select an objective 
                        option(v-for="objective in objectives" :value="objective") {{ objective.name }}
            button.button.is-primary.mr-2(type="button" @click="adversaryStore.createObjective($api)") 
                span.icon
                    font-awesome-icon(icon="fas fa-plus") 
                span New Objective
    .column.is-4.m-0
hr.mt-2

.content(v-if="selectedObjective.id")
    div(v-if="!isEditingNameDesc")
        .is-flex
            h3 {{ selectedObjective.name }}
            button.button.ml-3(@click="editNameDesc()")
                span.icon
                    font-awesome-icon(icon="fas fa-pencil-alt")
        p {{ selectedObjective.description }}
    div(v-else)
        .field
            .control
                input.input(type="text" v-model="newObjectiveName" placeholder="Objective name")
        .field
            .control
                textarea.textarea(type="text" v-model="newObjectiveDescription" placeholder="Objective description")
        .buttons
            button.button.is-primary.mr-2(@click="saveObjective()") Save
            button.button.mr-2(@click="isEditingNameDesc = false") Cancel

    .mt-5
        GoalsTable
</template>
