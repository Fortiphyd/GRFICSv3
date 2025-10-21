<script setup>
import { ref, onMounted, inject, reactive } from "vue";
import { useAdversaryStore } from "@/stores/adversaryStore.js";
import { storeToRefs } from "pinia";

const $api = inject("$api");
const selectedAdversaryID = ref("");
const openModal = ref(false);
const adversaryCreated = reactive({
  name: "",
  response: "",
  unmatched_techniques: [],
});
const adversaryStore = useAdversaryStore();

const { adversaries } = storeToRefs(adversaryStore);
onMounted(async () => {
  await adversaryStore.getAdversaries($api);
});

function downloadObjectAsJson(data) {
  let exportName = "layer";
  let dataStr = `data:text/json;charset=utf-8,${encodeURIComponent(
    JSON.stringify(data, null, 2)
  )}`;
  let downloadAnchorNode = document.createElement("a");
  downloadAnchorNode.setAttribute("href", dataStr);
  downloadAnchorNode.setAttribute("download", `${exportName}.json`);
  document.body.appendChild(downloadAnchorNode); // required for firefox
  downloadAnchorNode.click();
  downloadAnchorNode.remove();
}
const generateLayer = async () => {
  const payload = selectedAdversaryID.value
    ? {
        index: "adversary",
        adversary_id: selectedAdversaryID.value,
      }
    : { index: "all" };
  try {
    const res = await $api.post("/plugin/compass/layer", payload);
    downloadObjectAsJson(res.data);
  } catch (err) {
    console.error(err);
  }
};

const uploadAdversaryLayer = async (e) => {
  if (!e || !e.files || !e.files[0].name)
    toast("Error loading layer file", false);

  let formData = new FormData();
  formData.append("file", e.files[0]);
  try {
    const res = await $api.post("/plugin/compass/adversary", formData);
    const data = res.data;
    adversaryCreated.name = data.name;
    adversaryCreated.response = data.description;
    adversaryCreated.unmatched_techniques = data.unmatched_techniques.map(
      (item) => {
        return { technique_id: item.technique_id, tactic: item.tactic };
      }
    );
    openModal.value = true;
  } catch (error) {
    console.error(error);
  }
};
</script>

<template lang="pug">

.content
  h2 Compass
p
  | Generate a layer file for any adversary, which you can overlay on the matrix below 
  b OR 
  | Create an adversary in the matrix, then upload the layer file to generate an adversary to use in an operation
hr
.content
  .is-flex.is-flex-direction-row.mb-4
    .is-flex.is-flex-direction-column
      label.pb-2.is-size-6(for="layer-selection-adversary") Generate Layer
      .is-flex.is-flex-direction-row
        .field.has-addons
          .control
            #layerSelectionAdversary.select.is-small
              select#layer-selection-adversary(v-model="selectedAdversaryID")
                option(value="", selected) Select an Adversary (All)
                option(v-for="adv in adversaries", :value="adv.adversary_id") {{ adv.name }}
          .control
            label(for="generateLayer")
              button#generateLayer.button.is-primary.is-small(type="button", @click="generateLayer")
                i.pr-1.fas.fa-download
                span.has-tooltip-multiline.has-tooltip-bottom(v-tooltip="'In the Navigator, select Open Existing Layer -> Upload from local -> and upload the generated layer file.'") Generate Layer
    .is-flex.is-flex-direction-column.ml-6
      label.pb-2.is-size-6 Generate Adversary
      .is-flex.is-flex-direction-row
        input#generateAdversary(type="file", @change="uploadAdversaryLayer($event.target)", hidden)
        button.button.is-primary.is-small(for="generateAdversary")
          i.pr-1.fas.fa-upload
          span.has-tooltip-multiline.has-tooltip-bottom(v-tooltip="'Select techniques in the ATT&CK matrix below -> download the layer as json -> then upload the Adversary layer file here. You can now use the Adversary profile in Caldera, under the name given the layer file.'")
            label(for="generateAdversary") Create Operation
        input#adversaryLayerInput(type="file", hidden)
div
  iframe.frame(src="https://mitre-attack.github.io/attack-navigator/enterprise/")
template(v-if="openModal")
  .modal.is-active
    .modal-background(@click="openModal = false")
    .modal-card
      header.modal-card-head
        p.modal-card-title Adversary Created
        h3() {{ adversaryCreated.name}}
        h3(x-text="adversaryCreated.response") {{adversaryCreated.response}}
      section.modal-card-body
        div
          table.table.is-striped
            thead
              tr
                th#missing-abilities-tactic.has-text-grey Tactic
                th#missing-abilities-technique.has-text-grey Technique ID
            tbody#missing-abilities-body
              // Pug iteration for unmatched techniques
              template(v-for="(index, item) in adversaryCreated.unmatched_techniques", :key="index")
                tr
                td {{item.tactic}}
                td {{item.technique_id}}
          p.has-text-centered An adversary is only as good as its abilities. APT layers will cover the same tactics and techniques. Procedures that accurately represent an APT only come from proper curation of an adversary.
      footer.modal-card-foot
        nav.level
          .level-left
          .level-right
            .level-item
              button.button.is-small(@click="openModal = false") Close
</template>

<style scoped>
.frame {
  display: flex;
  width: 100%;
  border-radius: 5px;
  overflow: auto;
  height: 900px;
  border: 2px solid #666666;
}
</style>
