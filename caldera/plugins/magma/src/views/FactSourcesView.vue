<script setup>
import { ref, inject, onMounted } from "vue";
import { storeToRefs } from "pinia";

import { useSourceStore } from "@/stores/sourceStore.js";
import FactTable from "@/components/sources/FactTable.vue";
import RelationshipTable from "@/components/sources/RelationshipTable.vue";
import RuleTable from "@/components/sources/RuleTable.vue";

const $api = inject("$api");

const sourceStore = useSourceStore();
const { sources, selectedSource } = storeToRefs(sourceStore);

let isEditingName = ref(false);
let newSourceName = ref("");

onMounted(() => {
  sourceStore.getSources($api);
});

function saveSource() {
  selectedSource.value.name = newSourceName.value;
  sourceStore.saveSource($api, selectedSource);
  isEditingName.value = false;
}

async function createSource(duplicate) {
  const newSource = await sourceStore.createSource($api, duplicate);
  selectedSource.value = newSource;
}

async function deleteSource() {
  await sourceStore.deleteSource($api);
  selectedSource.value = {};
}

function downloadSource() {
  $api.get(`/api/v2/sources/${selectedSource.value.id}`)
    .then((res) => {
      const dataURL = `data:text/json;charset=utf-8,${encodeURIComponent(
        JSON.stringify(res, null, 2)
      )}`;
      const fileName = `${selectedSource.value.name}.json`;
      const elem = document.createElement("a");
      elem.setAttribute("href", dataURL);
      elem.setAttribute("download", fileName);
      elem.click();
      elem.remove();
    })
    .catch((error) => {
      console.error(error);
    });
}
</script>

<template lang="pug">
//- Header
.columns.mb-0
    .column.is-4.m-0.content
        h2.m-0 Fact Sources
    .column.is-4.m-0
        .is-flex.is-justify-content-center.is-flex-wrap-wrap
            .control.mr-2
                .select
                    select.has-text-centered(v-model="selectedSource")
                        option(disabled selected value="") Select a source 
                        option(v-for="source in sources" :value="source") {{ source.name }}
            button.button.is-primary.mr-2(type="button" @click="createSource(false)") 
                span.icon
                    font-awesome-icon(icon="fas fa-plus") 
                span New Source
    .column.is-4.m-0
        .buttons.is-justify-content-right(v-if="selectedSource.id")
            button.button.mr-2(@click="downloadSource" type="button")
                span.icon
                    font-awesome-icon(icon="fas fa-save")
                span Download Report
            button.button.mr-2(type="button" @click="createSource(true)")
                span.icon
                    font-awesome-icon(icon="far fa-copy")
                span Duplicate Source
            button.button.is-danger.is-outlined(type="button" @click="deleteSource()")
                span.icon
                    font-awesome-icon(icon="fas fa-trash")
                span Delete Source
hr.mt-2

.content(v-if="selectedSource.id")
    .is-flex(v-if="!isEditingName")
        h3 {{ selectedSource.name }}
        button.button.ml-3(@click="newSourceName = selectedSource.name; isEditingName = true;")
            span.icon
                font-awesome-icon(icon="fas fa-pencil-alt")
    .is-flex(v-else)
        .field.mr-2
            .control
                input.input(type="text" v-model="newSourceName")
        button.button.is-primary.mr-2(@click="saveSource()") Save
        button.button.mr-2(@click="isEditingName = false") Cancel

    .tile.is-ancestor.is-flex-wrap-wrap
        .tile.is-parent
            article.tile.is-child
                .box.content
                    h3 Facts
                    FactTable
        .tile.is-parent
            article.tile.is-child
                .box.content
                    h3 Rules
                    RuleTable
        .tile.is-parent
            article.tile.is-child
                .box.content
                    h3 Relationships
                    RelationshipTable

</template>
