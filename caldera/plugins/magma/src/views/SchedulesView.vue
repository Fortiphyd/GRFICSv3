<script setup>
import { computed, inject, onMounted } from 'vue';
import { storeToRefs } from "pinia";

import CreateScheduleModal from "@/components/schedules/CreateScheduleModal.vue";
import DeleteScheduleModal from "@/components/schedules/DeleteScheduleModal.vue";
import { useScheduleStore } from "@/stores/schedulesStore";
import { useAgentStore } from "@/stores/agentStore";
import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import { useCoreStore } from "@/stores/coreStore";
import { useOperationStore } from '@/stores/operationStore';

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const scheduleStore = useScheduleStore();
const agentStore = useAgentStore();
const coreStore = useCoreStore();
const { schedules } = storeToRefs(scheduleStore);
const { modals } = storeToRefs(coreDisplayStore);

const scheduleCount = computed(() => Object.keys(schedules.value).length);

const handleClick = (id) => {
  modals.value.schedules.showCreate = true;
  scheduleStore.selectedScheduleID = id;
};

onMounted(async () => {
  await scheduleStore.getSchedules($api);
  await coreStore.getObfuscators($api);
  await agentStore.getAgents($api);
  agentStore.updateAgentGroups();
});
</script>

<template lang="pug">
//- Header
.content
  h2 Schedules
hr

//- Button row
.columns.mb-4
  .column.is-one-quarter.is-flex.buttons.mb-0
    button.button.is-primary.level-item(@click="modals.schedules.showCreate = true")
      span.icon
        font-awesome-icon(icon="fas fa-plus")
      span Create a schedule
  .column.is-half.is-flex.is-justify-content-center
    span.tag.is-medium.m-0
      span.has-text-success
      strong {{ scheduleCount }} schedule{{ scheduleCount === 0 || scheduleCount > 1 ? 's' : '' }}
table.table.is-striped.is-fullwidth.is-narrow
  thead
    tr
      th.is-one-third Task Name
      th Schedule
  tbody
    tr.pointer(v-for="(schedule, id) in schedules" @click="handleClick(id)")
      td {{ schedule.task.name }}
      td {{ schedule.schedule }}

//- Modals
CreateScheduleModal
DeleteScheduleModal
</template>

<style scoped>
tr {
  cursor: pointer;
}

td.has-text-centered {
  width: 40px;
}
</style>
