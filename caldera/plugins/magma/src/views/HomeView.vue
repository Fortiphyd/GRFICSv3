<script setup>
import AgentChartStatus from "@/components/agents/AgentChartStatus.vue";
import OperationChartStatus from "@/components/operations/OperationChartStatus.vue";
import AbilityChartStatus from "@/components/abilities/AbilityChartStatus.vue";
import AdversaryChartStatus from "@/components/adversaries/AdversaryChartStatus.vue";
import CodeEditor from "@/components/core/CodeEditor.vue";
import { useCoreStore } from "@/stores/coreStore";
import { storeToRefs } from "pinia";
import { onMounted, inject } from "vue";

const coreStore = useCoreStore();
const $api = inject("$api");
onMounted(async () => {
  try {
    await coreStore.getMainConfig($api);
  } catch (error) {
    console.error(error);
  }
});
</script>

<template lang="pug">
.columns
  .column.is-3
    .box.is-flex.is-flex-direction-column
      AgentChartStatus.is-flex-grow-1
      router-link.button.is-primary.is-fullwidth(to="/agents") 
        span Manage Agents
        span.icon
          font-awesome-icon(icon="fas fa-arrow-right")
  .column.is-3
    .box.is-flex.is-flex-direction-column
      OperationChartStatus.is-flex-grow-1
      router-link.button.is-primary.is-fullwidth(to="/operations")
        span Manage Operations
        span.icon
          font-awesome-icon(icon="fas fa-arrow-right")
  .column.is-3
    .box.is-flex.is-flex-direction-column
      AbilityChartStatus.is-flex-grow-1
      router-link.button.is-primary.is-fullwidth(to="/abilities")
        span Manage Abilities
        span.icon
          font-awesome-icon(icon="fas fa-arrow-right")
  .column.is-3
    .box.is-flex.is-flex-direction-column
      AdversaryChartStatus.is-flex-grow-1
      router-link.button.is-primary.is-fullwidth(to="/adversaries")
        span Manage Adversaries
        span.icon
          font-awesome-icon(icon="fas fa-arrow-right")
.columns
  .column.is-3
    .box
      p.has-text-centered.has-text-weight-bold Server
      span Your Caldera instance is running at <b> {{coreStore.mainConfig["app.contact.http"]}} </b>
      


</template>

<style scoped>
.box {
  height: 300px;
}
</style>
