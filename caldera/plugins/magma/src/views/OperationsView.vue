<script setup>
import {
  inject,
  ref,
  onMounted,
  onBeforeUnmount,
  computed,
  watch,
  reactive,
} from "vue";
import { storeToRefs } from "pinia";
import { toast } from "bulma-toast";

//Graph imports
import Graph from "@/components/operations/Graph.vue";

import OutputModal from "@/components/operations/OutputModal.vue";
import CreateModal from "@/components/operations/CreateModal.vue";
import DeleteModal from "@/components/operations/DeleteModal.vue";
import DetailsModal from "@/components/operations/DetailsModal.vue";
import DownloadModal from "@/components/operations/DownloadModal.vue";
import AgentDetailsModal from "@/components/operations/AgentDetailsModal.vue";
import CommandPopup from "@/components/operations/CommandPopup.vue";
import OutputPopup from "@/components/operations/OutputPopup.vue";
import AddPotentialLinkModal from "@/components/operations/AddPotentialLinkModal.vue";
import ManualCommand from "@/components/operations/ManualCommand.vue";
import FiltersModal from "@/components/operations/FiltersModal.vue";
import { useOperationStore } from "@/stores/operationStore";
import { useAgentStore } from "@/stores/agentStore";
import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import { useCoreStore } from "@/stores/coreStore";
import {
  getHumanFriendlyTimeISO8601,
  b64DecodeUnicode,
  getReadableTime,
} from "@/utils/utils";
import { getLinkStatus } from "@/utils/operationUtil.js";

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const operationStore = useOperationStore();
const agentStore = useAgentStore();
const coreStore = useCoreStore();
const { modals } = storeToRefs(coreDisplayStore);

let updateInterval = ref();
let showPotentialLinkModal = ref(false);
let selectedOutputLink = ref(null);

// START SORTING AND FILTERING
const tableFilter = reactive({
  sortBy: "",
  sortOrder: "",
  filters: {
    decide: [],
    status: [],
    abilityName: [],
    paw: [],
    tactic: [],
    pid: [],
    host: [],
  },
});
const possibleFilters = reactive({
  abilityName: [],
  tactic: [],
  pid: [],
  paw: [],
  host: [],
});
const updatePossibleFilters = (chain) => {
  possibleFilters.abilityName.splice(0);
  possibleFilters.tactic.splice(0);
  possibleFilters.pid.splice(0);
  possibleFilters.paw.splice(0);
  possibleFilters.host.splice(0);

  chain.forEach((chain) => {
    if (!possibleFilters.abilityName.includes(chain.ability.name)) {
      possibleFilters.abilityName.push(chain.ability.name);
    }
    if (!possibleFilters.tactic.includes(chain.ability.tactic)) {
      possibleFilters.tactic.push(chain.ability.tactic);
    }
    if (!possibleFilters.paw.includes(chain.paw)) {
      possibleFilters.paw.push(chain.paw);
    }
    if (!possibleFilters.pid.includes(chain.pid)) {
      possibleFilters.pid.push(chain.pid);
    }
    if (!possibleFilters.host.includes(chain.host)) {
      possibleFilters.host.push(chain.host);
    }
  });
};

const filteredChain = computed(() => {
  let result = [...operationStore.currentOperation.chain];
  updatePossibleFilters(result);
  // Filter the data
  if (tableFilter.filters) {
    for (let property in tableFilter.filters) {
      if (tableFilter.filters[property].length === 0) {
        continue;
      }
      const filterValues = tableFilter.filters[property];
      if (filterValues && filterValues.length > 0) {
        result = result.filter((row) => {
          if (property === "abilityName") {
            return filterValues.includes(row.ability.name);
          } else if (property === "tactic") {
            return filterValues.includes(row.ability.tactic);
          }
          return filterValues.includes(row[property].toString());
        });
      }
    }
  }

  // Sort the data
  if (tableFilter.sortBy) {
    const sortOrder = tableFilter.sortOrder === "ASC" ? 1 : -1;
    if (tableFilter.sortBy == "abilityName") {
      result.sort((a, b) => {
        if (a.ability.name < b.ability.name) return -1 * sortOrder;
        if (a.ability.name > b.ability.name) return 1 * sortOrder;
        return 0;
      });
      return result;
    } else if (tableFilter.sortBy == "tactic") {
      result.sort((a, b) => {
        if (a.ability.tactic < b.ability.tactic) return -1 * sortOrder;
        if (a.ability.tactic > b.ability.tactic) return 1 * sortOrder;
        return 0;
      });
      return result;
    }
    result.sort((a, b) => {
      if (a[tableFilter.sortBy] < b[tableFilter.sortBy]) return -1 * sortOrder;
      if (a[tableFilter.sortBy] > b[tableFilter.sortBy]) return 1 * sortOrder;
      return 0;
    });
  }
  return result;
});

const handleTableSort = (property) => {
  if (tableFilter.sortBy === property) {
    if (tableFilter.sortOrder == "ASC") {
      tableFilter.sortOrder = "DESC";
    } else {
      tableFilter.sortOrder = "";
      tableFilter.sortBy = "";
    }
  } else {
    tableFilter.sortBy = property;
    tableFilter.sortOrder = "ASC";
  }
};

const getSortIconColor = (property, direction) => {
  if (tableFilter.sortBy === property) {
    if (tableFilter.sortOrder == "ASC" && direction === "up") {
      return "#fff";
    } else if (tableFilter.sortOrder == "DESC" && direction === "down") {
      return "#fff";
    }
  }
  return "grey";
};
//END SORTING AND FILTERING

onMounted(async () => {
  await operationStore.getOperations($api);
  await coreStore.getObfuscators($api);
  await agentStore.getAgents($api);
  agentStore.updateAgentGroups();
  selectOperation();
});

onBeforeUnmount(() => {
  if (updateInterval) clearInterval(updateInterval);
});

const resetFilter = () => {
  tableFilter.sortBy = "";
  tableFilter.sortOrder = "";
  tableFilter.filters.decide = [];
  tableFilter.filters.status = [];
  tableFilter.filters.abilityName = [];
  tableFilter.filters.paw = [];
  tableFilter.filters.tactic = [];
  tableFilter.filters.host = [];
  tableFilter.filters.pid = [];
};

function selectOperation() {
  if (updateInterval) clearInterval(updateInterval);
  if (operationStore.selectedOperationID === "") return;
  resetFilter();
  updateInterval = setInterval(async () => {
    if (operationStore.selectedOperationID !== "" &&
        operationStore.operations[operationStore.selectedOperationID].state !== "finished")
    {
      await operationStore.getOperation($api, operationStore.selectedOperationID);
    } else {
      clearInterval(updateInterval);
    }
  }, "3000");
}

async function updateAuto(event) {
  // operationStore.operations[operationStore.selectedOperationID].autonomous = event.target.checked ? 1 : 0;
  await operationStore.updateOperation(
    $api,
    "autonomous",
    event.target.checked ? 1 : 0
  );
}

function isRerun() {
  return (
    operationStore.operations[operationStore.selectedOperationID].state ===
      "cleanup" ||
    operationStore.operations[operationStore.selectedOperationID].state ===
      "finished"
  );
}

function displayManualCommand() {
  modals.value.operations.showAddManualCommand = true;
  setTimeout(() => {
    document.getElementById("manual-input-command").scrollIntoView({
      behavior: "smooth",
    });
  }, 2);
}

async function addPotentialLinks(links) {
  try {
    if (operationStore.currentOperation.state !== "running") {
      toast({
        message:
          "Operation is currently paused, and new links might not be added.",
        type: "is-warning",
        dismissible: true,
        pauseOnHover: true,
        duration: 2000,
        position: "bottom-right",
      });
    }
    await operationStore.addPotentialLinks($api, links);
    showPotentialLinkModal.value = false;
  } catch (error) {
    console.error("Error adding potential links", error);
  }
}

function highlightLink(linkElement) {
  linkElement.classList.add("highlight-link");
  setTimeout(() => {
    linkElement.classList.remove("highlight-link");
  }, 2000);
}

function handleViewOutput(link) {
  selectedOutputLink.value = link;
  modals.value.operations.showOutput = true;
}
</script>

<template lang="pug">
.columns.mb-0
    .column.is-4.m-0.content
        h2.m-0 Operations
    .column.is-4.m-0
        .is-flex.is-justify-content-center
            .control.mr-2
                .select
                    select.has-text-centered(v-model="operationStore.selectedOperationID" @change="selectOperation()")
                        option(disabled selected value="") Select an operation 
                        option(v-for="operation in operationStore.operations" :key="operation.id" :value="operation.id") {{ `${operation.name} - ${operation.chain.length} decisions | ${getHumanFriendlyTimeISO8601(operation.start)}` }}
            button.button.is-primary.mr-2(@click="modals.operations.showCreate = true" type="button") 
                span.icon
                    font-awesome-icon(icon="fas fa-plus") 
                span New Operation
    .column.is-4.m-0
        .buttons.is-justify-content-right(v-if="operationStore.operations[operationStore.selectedOperationID]")
            button.button.mr-2(@click="modals.operations.showDownload = true" type="button")
                span.icon
                    font-awesome-icon(icon="fas fa-save")
                span Download Report
            button.button.is-danger.is-outlined(@click="modals.operations.showDelete = true" type="button")
                span.icon
                    font-awesome-icon(icon="fas fa-trash")
                span Delete Operation
hr.mt-2

Graph(@scroll="highlightLink")
//- Control Panel
.control-panel.p-0.mb-4(v-if="operationStore.selectedOperationID")
    .columns.m-0.p-1
        .column.is-4.pt-0.pb-0.is-flex
            .buttons
                button.button(v-if="operationStore.isOperationRunning()" @click="displayManualCommand()")
                    span.icon
                        font-awesome-icon.fa(icon="fas fa-plus")
                    span Manual Command
                button.button(v-if="operationStore.isOperationRunning()" @click="showPotentialLinkModal = true")
                    span.icon
                        font-awesome-icon.fa(icon="fas fa-plus")
                    span Potential Link
                button.button(@click="modals.operations.showDetails = true" type="button") Operation Details
                button.button(@click="modals.operations.showFilters = true" type="button")
                  span.icon
                    font-awesome-icon(icon="fas fa-filter")
                  span Filters
        .column.is-4.pt-0.pb-0
            span.has-text-success.is-flex.is-justify-content-center {{ operationStore.operations[operationStore.selectedOperationID].state }}
            .is-flex.is-justify-content-center.is-align-items-center.pb-2
                a.icon.is-medium.ml-3.mr-3(v-if="!isRerun()" @click="operationStore.updateOperation($api, 'state', 'cleanup')" v-tooltip="'Stop'")
                    font-awesome-icon.fa-2x(icon="fas fa-stop")
                a.icon.is-medium.ml-3.mr-3(v-if="!isRerun() && operationStore.operations[operationStore.selectedOperationID].state === 'paused' || operationStore.operations[operationStore.selectedOperationID].state === 'run_one_link'" @click="operationStore.updateOperation($api, 'state', 'running')" v-tooltip="'Play'")
                    font-awesome-icon.fa-2x(icon="fas fa-play")
                a.icon.is-medium.ml-3.mr-3(v-else v-if="!isRerun()" @click="operationStore.updateOperation($api, 'state', 'paused')" v-tooltip="'Pause'")
                    font-awesome-icon.fa-2x(icon="fas fa-pause")
                a.icon.is-medium.ml-3.mr-3(v-if ="!isRerun()" @click="operationStore.updateOperation($api, 'state', 'run_one_link')" v-tooltip="'Run one link'")
                    font-awesome-icon.fa-2x(icon="fas fa-play")
                    span.mt-5 1
                a.icon.is-medium.ml-3.mr-3(v-if="isRerun()" @click="operationStore.rerunOperation($api)" v-tooltip="'Re-run Operation'")
                    font-awesome-icon.fa-2x(icon="fas fa-redo")
        .column.is-4.is-flex.is-justify-content-right.is-align-items-center.is-flex-wrap-wrap.pt-0.pb-0
            span.is-size-6 Obfuscator: 
            .control(v-if="operationStore.isOperationRunning()")
                .select.ml-1.mr-4
                    select(v-model="operationStore.operations[operationStore.selectedOperationID].obfuscator" @change="operationStore.updateOperation($api, 'obfuscator', operationStore.operations[operationStore.selectedOperationID].obfuscator)")
                        option(v-for="(obf, idx) in coreStore.obfuscators" :key="idx" :value="obf.name") {{ `${obf.name}` }}
            .control(v-else)
                .select.ml-1.mr-4
                    select(v-model="operationStore.operations[operationStore.selectedOperationID].obfuscator" :disabled="true")
                        option(v-for="(obf, idx) in coreStore.obfuscators" :key="idx" :value="obf.name") {{ `${obf.name}` }}
            .control(v-if="operationStore.isOperationRunning()")
                input.switch(
                    :checked="operationStore.operations[operationStore.selectedOperationID].autonomous === 1" 
                    id="switchManual" 
                    type="checkbox" 
                    @change="updateAuto($event)"
                )
                label.label(for="switchManual") {{ operationStore.operations[operationStore.selectedOperationID].autonomous ? 'Autonomous' : 'Manual' }} 
            .control(v-else)
                input.switch(
                    :checked="operationStore.operations[operationStore.selectedOperationID].autonomous === 1" 
                    :disabled="true"
                    id="switchManual" 
                    type="checkbox" 
                )
                label.label(for="switchManual") {{ operationStore.operations[operationStore.selectedOperationID].autonomous ? 'Autonomous' : 'Manual' }}
        
//- Table
table.table.is-fullwidth.is-narrow.is-striped.mb-8#link-table(v-if="operationStore.selectedOperationID")
    thead
        tr
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('decide')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span Time Ran 
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('decide', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('decide', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('status')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span Status
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('status', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('status', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('abilityName')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span Ability Name
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('abilityName', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('abilityName', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('tactic')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span Tactic
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('tactic', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('tactic', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('agent')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span Agent
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('agent', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('agent', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('host')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span Host
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('host', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('host', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-row.is-align-items-center.gap-5(@click="handleTableSort('pid')" :style="{ cursor: 'pointer', width: 'fit-content' }")
              span pid
              div.is-flex.is-flex-direction-column.is-justify-content-center
                span.icon.m-n5(:style="{ color: getSortIconColor('pid', 'up') }")
                  font-awesome-icon(icon="fas fa-angle-up")
                span.icon(:style="{ color: getSortIconColor('pid', 'down') }")
                  font-awesome-icon(icon="fas fa-angle-down")
          th
            div.is-flex.is-flex-direction-column.is-justify-content-center
              span.mt-2 Link Command 
          th
            div.is-flex.is-flex-direction-column.is-justify-content-center
              span.mt-2 Link Output 
          th
    tbody
        tr(v-for="(link, idx) in filteredChain" :key="link.id" :id="`link-${idx}`")
            td {{ getReadableTime(link.decide) }}
            td
                .is-flex.is-align-items-center(style="border-bottom-width: 0px !important")
                    .link-status.mr-2(:style="{ color: getLinkStatus(link).color}") 
                    span(:style="{ color: getLinkStatus(link).color}") {{ getLinkStatus(link).text }}
            td {{ link.ability.name }}
            td {{ link.ability.tactic }}
            td {{ link.paw }}
            td {{ link.host }}
            td {{ link.pid ? link.pid : "N/A" }}
            td
                //- button.button(v-tooltip="b64DecodeUnicode(link.command)" @click="handleViewCommand(link)") View Command
                .dropdown.is-hoverable
                    .dropdown-trigger
                        button.button(aria-haspopup="true" aria-controls="dropdown-menu")
                          span View Command
                          span.icon.is-small(v-if="link.cleanup != 0")
                            font-awesome-icon(icon="fas fa-broom")
                    .dropdown-menu.command-popup(role="menu")
                        .dropdown-content
                            CommandPopup(:link="link")
            td
                //- button.button(v-if="link.output === 'True'" @click="handleViewOutput(link)") View Output
                .dropdown.is-hoverable(v-if="link.output === 'True'")
                    .dropdown-trigger
                        button.button(aria-haspopup="true" aria-controls="dropdown-menu" @click="handleViewOutput(link)") View Output
                    .dropdown-menu.command-popup(role="menu")
                        .dropdown-content
                            OutputPopup(:link="link")
                span(v-else) No output
            td(v-if="operationStore.currentOperation.state === 'running'")
                a.icon(@click="operationStore.rerunLink($api, link)" v-tooltip="'Re-run Link'")
                    font-awesome-icon(icon="fas fa-redo")
        ManualCommand(v-if="modals.operations.showAddManualCommand")
                
//- Modals
CreateModal(:selectInterval="selectOperation")
DeleteModal
DetailsModal
DownloadModal
AgentDetailsModal
AddPotentialLinkModal(
    :active="showPotentialLinkModal" 
    :operation="operationStore.operations[operationStore.selectedOperationID]"
    @select="addPotentialLinks" 
    @close="showPotentialLinkModal = false")
FiltersModal(:filters="tableFilter.filters" :possibleFilters="possibleFilters")
OutputModal(v-if="selectedOutputLink" :link="selectedOutputLink")
</template>

<style>
.node-text {
  white-space: nowrap;
  overflow: hidden;
}

.control-panel {
  position: sticky;
  top: 70px;
  z-index: 10;
  border-radius: 8px;
  background-color: #383838;
  border: 1px solid #121212;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 1);
}

#link-table {
  border-radius: 10px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 1);
  padding: 5rem;
  margin-bottom: 15rem !important;
}

.gap-5 {
  gap: 0.4rem;
}

.m-n5 {
  margin-bottom: -0.5rem;
}

.link-status {
  background-color: #242424;
  border: 0.2em solid;
  border-radius: 50%;
  height: 1em;
  width: 1em;
  z-index: 1;
}

.dropdown-menu.command-popup {
  top: 0;
  left: initial;
  right: 90%;
  max-width: 75vw;
  max-height: 300px;
  border-radius: 8px;
  padding: 0;
}
.dropdown-menu.command-popup > .dropdown-content {
  padding: 10px;
  margin-right: 10px;
  border: 1px solid hsl(0deg, 0%, 71%);
  overflow-y: auto;
  max-width: 85vw;
  max-height: 300px;
}

a.icon {
  text-decoration: none !important;
}

.table td {
  vertical-align: middle !important;
}

.highlight-link {
  border: 2px solid #8b00ff;
}
</style>
