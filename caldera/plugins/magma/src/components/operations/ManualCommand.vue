<script setup>
import { reactive, inject, ref } from "vue";
import { storeToRefs } from "pinia";
import { toast } from "bulma-toast";

import CodeEditor from "@/components/core/CodeEditor.vue";
import { useOperationStore } from "@/stores/operationStore";
import { useCoreDisplayStore } from "@/stores/coreDisplayStore";

const operationStore = useOperationStore();
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

const $api = inject("$api");

const manualCommand = reactive({
  agent: null,
  executor: {
    name: "",
    command: "",
    platform: "",
  },
  paw: operationStore.currentOperation.host_group[0].paw,
});

function getExecutorsByPaw(targetPaw) {
  var agent = operationStore.currentOperation.host_group.find(({ paw }) => paw === targetPaw);
  if (!manualCommand.executor.name || !agent.executors.includes(manualCommand.executor.name)) {
    manualCommand.executor.name = agent.executors[0];
  }
  return agent.executors;
}

function addManualCommand() {
  if (manualCommand.executor.command.length <= 0) {
    toast({
      message: "Please enter a command",
      type: "is-danger",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
      position: "bottom-right",
    });
    return;
  }
  manualCommand.agent = operationStore.currentOperation.host_group.find(({ paw }) => paw === manualCommand.paw);
  manualCommand.executor.platform = manualCommand.agent.platform;
  if (operationStore.currentOperation.state === "paused") {
    toast({
      message: "Operation is paused",
      type: "is-danger",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
      position: "bottom-right",
    });
    modals.value.operations.showAddManualCommand = false;
    return;
  }
  operationStore.addManualCommand($api, manualCommand);
  modals.value.operations.showAddManualCommand = false;
}
</script>

<template lang="pug">
tr(id="manual-input-command")
    td New Manual Command
    td(colspan="2")
        .control
            .select
                select(v-model="manualCommand.paw")
                    option(v-for="(agent, idx) in operationStore.currentOperation.host_group" :key="agent.paw" :value="agent.paw") {{ `${agent.display_name} - ${agent.paw}` }}
    td
        .control
            .select 
                select(v-model="manualCommand.executor.name")
                    option(v-for="(executor) in getExecutorsByPaw(manualCommand.paw)" :key="executor" :value="executor") {{`${executor}`}}
    td(colspan="3")
        CodeEditor(v-model="manualCommand.executor.command" language="bash" line-numbers)
    td
        .is-flex.is-flex-direction-column.is-justify-content-center
            button.button.is-primary(@click="addManualCommand()" :disabled="!manualCommand.paw || !manualCommand.executor.command || !manualCommand.executor.name") Add Command 
            button.button.mt-2(@click="modals.operations.showAddManualCommand = false") Cancel 
</template>
