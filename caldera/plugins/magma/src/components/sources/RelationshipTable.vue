<script setup>
import { ref, inject } from "vue";
import { storeToRefs } from "pinia";

import { useSourceStore } from "@/stores/sourceStore.js";

const $api = inject("$api");

const sourceStore = useSourceStore();
const { selectedSource } = storeToRefs(sourceStore);

let relationshipIndexToEdit = ref(-1);

function addRelationship() {
    selectedSource.value.relationships.push({
        edge: "",
        source: {
            trait: ""
        },
        target: {
            trait: ""
        }
    });
    relationshipIndexToEdit.value = selectedSource.value.relationships.length - 1;
}

function removeRelationship(relationshipIndex) {
    selectedSource.value.relationships.splice(relationshipIndex, 1);
    saveRelationships();
}

async function saveRelationships() {
    relationshipIndexToEdit.value = -1;
    await sourceStore.saveSource($api);
}
</script>

<template lang="pug">
.buttons.m-0
    button.button(@click="addRelationship()")
        span.icon
            font-awesome-icon(icon="fas fa-plus")
        span Add Relationship

table.table.is-striped.is-fullwidth
    thead
        tr
            th Source
            th Edge
            th Target
            th
    tbody
        tr(v-for="(relationship, index) of selectedSource.relationships")
            td 
                input.input(v-if="relationshipIndexToEdit === index" v-model="relationship.source.trait" placeholder="Relationship source")
                span(v-else) {{ relationship.source.trait }}
            td 
                input.input(v-if="relationshipIndexToEdit === index" v-model="relationship.edge" placeholder="Relationship edge")
                span(v-else) {{ relationship.edge }}
            td 
                input.input(v-if="relationshipIndexToEdit === index" v-model="relationship.target.trait" placeholder="Relationship target")
                span(v-else) {{ relationship.target.trait }}
            td
                .buttons
                    button.button.is-primary(
                            v-if="relationshipIndexToEdit === index" @click="saveRelationships()"
                            :disabled="!relationship.source.trait || !relationship.edge || !relationship.target.trait"
                            )
                        span.icon
                            font-awesome-icon(icon="fa-save")
                    button.button(v-else @click="relationshipIndexToEdit = index")
                        span.icon
                            font-awesome-icon(icon="fa-pencil-alt")
                    button.button.is-danger.is-outlined(@click="removeRelationship(index)")
                        span.icon
                            font-awesome-icon(icon="fa-trash")

</template>
