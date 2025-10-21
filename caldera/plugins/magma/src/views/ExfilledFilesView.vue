<script setup>
import { reactive, ref, inject, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { useCoreStore } from "@/stores/coreStore";
import { useOperationStore } from "@/stores/operationStore";
import { useExfilledStore } from "@/stores/exfilledStore";

const $api = inject("$api");
const coreStore = useCoreStore();
const exfilStore = useExfilledStore();
const operationStore = useOperationStore();
const { mainConfig } = storeToRefs(coreStore);
const { operations } = storeToRefs(operationStore);
const { files, exfilDir, numFiles } = storeToRefs(exfilStore);
const selectedOperationId = ref("");
const selectedFiles = ref([]);
const folderState = reactive({
  exfilDir: false,
});

onMounted(async () => {
  await coreStore.getMainConfig($api);
  exfilStore.setExfilDir(mainConfig.value.exfil_dir);
  await operationStore.getOperations($api);
  exfilStore.loadFiles($api, selectedOperationId.value);
  // Add folders to folder state (open close)
  Object.keys(files).forEach((agentName) => {
    folderState[agentName] = false;
  });
});

function toggleAllFiles() {
  if (selectedFiles.value.length < numFiles.value) {
    Object.keys(files.value).forEach((agentName) => {
      Object.keys(files.value[agentName]).forEach((operation) => {
        Object.keys(files.value[agentName][operation]).forEach((filename) => {
          selectedFiles.value.push(files.value[agentName][operation][filename]);
        });
      });
    });
  } else {
    selectedFiles.value = [];
  }
}

function downloadSelectedFiles() {
  selectedFiles.value.forEach((filePath) => {
    let filename = filePath.split(/[\/\\]/);
    filename = filename[filename.length - 1];
    let uri = `${
      window.location.origin
    }/file/download_exfil?file=${btoa(filePath)}`;
    let downloadAnchorNode = document.createElement("a");
    downloadAnchorNode.setAttribute("href", uri);
    downloadAnchorNode.setAttribute("download", filename);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  });
}
</script>

<template lang="pug">
//- Header
.content
  h2 Exfilled Files
  p Exfilled files are uploaded from an agent on a host to the server during an operation are by default stored on the server at {{ exfilDir }}
    br
    span If an operation has exfilled files, you can view and download the files here
hr

p(v-if="numFiles === 0") The exfill directory ({{ exfilDir }}) is empty.
.buttons(v-else)
  button.button.is-primary.is-small(@click="toggleAllFiles()")
    span(v-text="selectedFiles.length < numFiles ? 'Select' : 'Unselect'")
    | &nbsp;All Files
  button.button.is-primary.is-small(:disabled="!selectedFiles.length" @click="downloadSelectedFiles()")
    span.icon
      font-awesome-icon(icon="fas fa-angle-down" aria-hidden="true")
    span Download
ul.tree(v-if="numFiles !== 0")
  li.root.is-flex.is-align-items-center
    span.icon
      font-awesome-icon(v-if="folderState.exfilDir" icon="fas fa-folder-open" aria-hidden="true")
      font-awesome-icon(v-if="!folderState.exfilDir" icon="fas fa-folder-closed" aria-hidden="true")
    span(v-text="exfilDir")
    span.icon(@click="folderState.exfilDir = !folderState.exfilDir")
      font-awesome-icon(v-if="folderState.exfilDir" icon="fas fa-angle-up" aria-hidden="true")
      font-awesome-icon(v-if="!folderState.exfilDir" icon="fas fa-angle-down" aria-hidden="true")
  template(v-if="folderState.exfilDir" v-for="agentName of Object.keys(files)" :key="agentName")
    li.root-child.is-flex.is-align-items-center
      span.icon
        font-awesome-icon(v-if="folderState[agentName]" icon="fas fa-folder-open" aria-hidden="true")
        font-awesome-icon(v-if="!folderState[agentName]" icon="fas fa-folder-closed" aria-hidden="true")
      span(v-text="agentName")
      span.icon(@click="folderState[agentName] = !folderState[agentName]")
        font-awesome-icon(v-if="folderState[agentName]" icon="fas fa-angle-up" aria-hidden="true")
        font-awesome-icon(v-if="!folderState[agentName]" icon="fas fa-angle-down" aria-hidden="true")
    template(v-if="folderState[agentName]" v-for="operation of Object.keys(files[agentName])" :key="operation")
      ul.tree
        li.agentName-child
          span.icon
            font-awesome-icon(icon="fas fa-dragon" aria-hidden="true")
          span(v-text="operation")
          ul.tree
            template(v-for="filename of Object.keys(files[agentName][operation])" :key="filename")
              li.agent-child
                label.checkbox
                  input(type="checkbox" class="file-checkbox" :value="files[agentName][operation][filename]" v-model="selectedFiles")
                  span.icon
                    font-awesome-icon(icon="fas fa-file" aria-hidden="true")
                  span(v-text="filename")
            li.agent-child(v-show="!Object.keys(files[agentName][operation]).length") (none)
</template>

<style>
#select-operation {
  max-width: 800px;
  margin: 0 auto;
}

ul.tree {
  margin: 0px 0px 0px 20px;
  list-style: none !important;
  line-height: 2em;
  font-family: Arial;
}
ul.tree li {
  font-size: 16px;
  position: relative;
}
ul.tree li:before {
  position: absolute;
  left: -15px;
  top: -10px;
  content: "";
  display: block;
  border-left: 1px solid #ddd;
  height: 1.7em;
  border-bottom: 1px solid #ddd;
  width: 10px;
}
ul.tree li:after {
  position: absolute;
  left: -15px;
  bottom: -7px;
  content: "";
  display: block;
  border-left: 1px solid #ddd;
  height: 100%;
}
ul.tree li.root {
  margin: 0px 0px 0px -20px;
}
ul.tree li.root:before {
  display: none;
}
ul.tree li.root:after {
  display: none;
}
ul.tree li.root-child:last-child:after {
  display: none;
}
ul.tree li.agentName-child:after {
  display: none;
}
ul.tree li.agent-child:nth-last-child(2):after {
  display: none;
}
ul.tree li:last-child:after {
  display: none;
}
</style>
