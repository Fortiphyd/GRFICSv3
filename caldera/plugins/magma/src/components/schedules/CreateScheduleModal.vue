<script setup>
import { ref, inject, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { toast } from "bulma-toast";

import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import { useScheduleStore } from "@/stores/schedulesStore";
import { useAdversaryStore } from "@/stores/adversaryStore";
import { useCoreStore } from "@/stores/coreStore";
import { useAgentStore } from "@/stores/agentStore";
import { useSourceStore } from "@/stores/sourceStore";

import cron from "cron-validate";

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
const adversaryStore = useAdversaryStore();
const scheduleStore = useScheduleStore();
const coreStore = useCoreStore();
const agentStore = useAgentStore();
const sourceStore = useSourceStore();
const { sources } = storeToRefs(sourceStore);

let schedule = ref("");
let taskName = ref("");
let selectedAdversary = ref({});
let selectedSource = ref({});
let selectedGroup = ref("");
let selectedObfuscator = ref({ name: "plain-text" });
let selectedPlanner = ref();
let isAuto = ref(true);
let isDefParser = ref(true);
let isAutoClose = ref(false);
let isPause = ref(false);
let minJitter = ref(2);
let maxJitter = ref(8);
let visibility = ref(51);
let validation = ref({
  schedule: "",
  name: "",
});

onMounted(async () => {
  await agentStore.getAgents($api);
  agentStore.updateAgentGroups();
  await adversaryStore.getAdversaries($api);
  await getSources();
  await coreStore.getObfuscators($api);
  await getPlanners();
});

watch(
  () => modals.value.schedules.showCreate,
  (newValue) => {
    if (newValue) {
      resetFields();
    }
  }
);

function resetFields() {
  validation.value.schedule = "";
  validation.value.name = "";

  let currentSchedule = scheduleStore.currentSchedule;
  if (currentSchedule) {
    schedule.value = currentSchedule.schedule;
    taskName.value = currentSchedule.task.name;
    selectedAdversary.value =
      currentSchedule.task.adversary.adversary_id === "ad-hoc"
        ? ""
        : currentSchedule.task.adversary;
    selectedSource.value =
      sources.value.find(
        (source) => source.id === currentSchedule.task.source.id
      ) || null;
    selectedGroup.value = currentSchedule.task.group;
    selectedPlanner.value =
      coreStore.planners.find(
        (planner) => planner.id === currentSchedule.task.planner.id
      ) || null;
    selectedObfuscator.value = { name: currentSchedule.task.obfuscator };
    isDefParser.value = currentSchedule.task.use_learning_parsers;
    isAutoClose.value = currentSchedule.task.auto_close;
    isPause.value = currentSchedule.task.state === "paused";
    minJitter.value = Number(currentSchedule.task.jitter.split("/")[0]);
    maxJitter.value = Number(currentSchedule.task.jitter.split("/")[1]);
    visibility.value = currentSchedule.task.visibility;
  } else {
    schedule.value = "";
    taskName.value = "";
    selectedAdversary.value = "";
    selectedSource.value =
      sources.value.find((source) => source.name === "basic") || null;
    selectedGroup.value = "";
    selectedPlanner.value = coreStore.planners[0] || null;
    selectedObfuscator.value = { name: "plain-text" };
    isDefParser.value = true;
    isAutoClose.value = false;
    isPause.value = false;
    minJitter.value = 2;
    maxJitter.value = 8;
    visibility.value = 51;
  }
}

function closeModal() {
  modals.value.schedules.showCreate = false;
  scheduleStore.selectedScheduleID = "";
}

async function getSources() {
  try {
    await sourceStore.getSources($api);
    selectedSource.value = sources.value.find(
      (source) => source.name === "basic"
    );
  } catch (error) {
    console.error("Error getting sources", error);
  }
}

async function getPlanners() {
  try {
    await coreStore.getPlanners($api);
    selectedPlanner.value = coreStore.planners[0];
  } catch (error) {
    console.error("Error getting planners", error);
  }
}

function createNewSchedule() {
  if (!schedule.value) {
    validation.value.schedule = "Schedule cannot be empty";
    return null;
  }

  if (!cron(schedule.value).isValid()) {
    validation.value.schedule = "Schedule cron expression is invalid";
    return null;
  }
  validation.value.schedule = "";

  if (!taskName.value) {
    validation.value.name = "Task Name cannot be empty";
    return null;
  }
  validation.value.name = "";

  if (!selectedAdversary.value.adversary_id) {
    selectedAdversary.value = { adversary_id: "ad-hoc" };
  }

  return {
    schedule: schedule.value,
    task: {
      name: taskName.value,
      autonomous: Number(isAuto.value),
      use_learning_parsers: isDefParser.value,
      auto_close: isAutoClose.value,
      jitter: `${minJitter.value}/${maxJitter.value}`,
      state: isPause.value ? "paused" : "running",
      visibility: visibility.value,
      obfuscator: selectedObfuscator.value.name,
      source: { id: JSON.parse(JSON.stringify(selectedSource.value.id)) },
      planner: { id: JSON.parse(JSON.stringify(selectedPlanner.value.id)) },
      adversary: {
        adversary_id: JSON.parse(
          JSON.stringify(selectedAdversary.value.adversary_id)
        ),
      },
      group: selectedGroup.value,
    },
  };
}

async function createSchedule(newSchedule) {
  try {
    await scheduleStore.createSchedule($api, newSchedule);
    toast({
      message: `Schedule ${schedule.value} created`,
      type: "is-success",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
      position: "bottom-right",
    });
    closeModal();
  } catch (error) {
    console.error("Error creating schedule", error);
    toast({
      message: `Error creating schedule`,
      type: "is-danger",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
      position: "bottom-right",
    });
  }
}

async function updateSchedule(newSchedule) {
  try {
    await scheduleStore.updateSchedule($api, newSchedule);
    toast({
      message: `Schedule ${schedule.value} updated`,
      type: "is-success",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
      position: "bottom-right",
    });
    closeModal();
  } catch (error) {
    console.error("Error updating schedule", error);
    toast({
      message: `Error updating schedule`,
      type: "is-danger",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
      position: "bottom-right",
    });
  }
}

async function callApi() {
  let newSchedule = createNewSchedule();
  if (!newSchedule) {
    return;
  }
  if (scheduleStore.currentSchedule) {
    await updateSchedule(newSchedule);
  } else {
    await createSchedule(newSchedule);
  }
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.schedules.showCreate }")
  .modal-background(@click="closeModal()")
  .modal-card
    header.modal-card-head
      p.modal-card-title {{ scheduleStore.currentSchedule ? "Update" : "Create New" }} Schedule
    .modal-card-body
      .field.is-horizontal
        .field-label.is-normal
          label.label Schedule
        .field-body
          input.input(placeholder="* * * * *    <minute> <hour> <day-of-month> <month> <day-of-week>" v-model="schedule")
          label.label.ml-3.mt-1.has-text-danger {{ `${validation.schedule}` }}
      .field.is-horizontal
        .field-label.is-normal
          label.label Task Name
        .field-body
          input.input(placeholder="Operation Name" v-model="taskName" :disabled="scheduleStore.currentSchedule")
          label.label.ml-3.mt-1.has-text-danger {{ `${validation.name}` }}
      .field.is-horizontal
        .field-label.is-normal
          label.label Adversary
        .field-body
          .control
            .select
              select(v-model="selectedAdversary" :disabled="scheduleStore.currentSchedule")
                option(selected value="") No Adversary (manual)
                option(v-for="adversary in adversaryStore.adversaries" :key="adversary.id" :value="adversary") {{ `${adversary.name}` }}
      .field.is-horizontal
        .field-label.is-normal
          label.label Fact Source
        .field-body
          .control
            .select
              select(v-model="selectedSource" :disabled="scheduleStore.currentSchedule")
                option(disabled selected value="") Choose a Fact Source
                option(v-for="source in sources" :key="source.id" :value="source") {{ `${source.name}` }}
      .field.is-horizontal
        .field-label.is-normal
          label.label Group
        .field-body
          button.button(:class="{ 'is-primary': selectedGroup === '' }" @click="selectedGroup = ''") All groups
          button.button.mx-2(v-for="group in agentStore.agentGroups" :key="group" :class="{ 'is-primary': selectedGroup === group }", @click="selectedGroup = group") {{`${group}`}}
      .field.is-horizontal
        .field-label.is-normal
          label.label Planner
        .field-body
          .control
            .select
              select(v-model="selectedPlanner" :disabled="scheduleStore.currentSchedule")
                option(v-for="planner in coreStore.planners" :key="planner.id" :value="planner") {{ `${planner.name}` }}
      .field.is-horizontal
        .field-label
          label.label Obfuscators
        .field-body
          .field.is-grouped-multiline
            button.button.my-1.mr-2(v-for="obf in coreStore.obfuscators" :key="obf.id" :value="obf" :class="{ 'is-primary': selectedObfuscator.name === obf.name }" @click="selectedObfuscator = obf") {{ `${obf.name}` }}
      .field.is-horizontal
        .field-label
          label.label Autonomous
        .field-body
          .field.is-grouped
            input.is-checkradio(type="radio" id="auto" :checked="isAuto" @click="isAuto = true")
            label.label.ml-3.mt-1(for="auto") Run autonomously
            input.is-checkradio.ml-3(type="radio" id="manual" :checked="!isAuto" @click="isAuto = false")
            label.label.ml-3.mt-1(for="manual") Require manual approval
      .field.is-horizontal
        .field-label
          label.label Parser
        .field-body
          .field.is-grouped
            input.is-checkradio(type="radio" id="defaultparser" :checked="isDefParser" @click="isDefParser = true" :disabled="scheduleStore.currentSchedule")
            label.label.ml-3.mt-1(for="defaultparser") Use Default Parser
            input.is-checkradio.ml-3(type="radio" id="nondefaultparser" :checked="!isDefParser" @click="isDefParser = false" :disabled="scheduleStore.currentSchedule")
            label.label.ml-3.mt-1(for="nondefaultparser") Don't use default learning parsers
      .field.is-horizontal
        .field-label
          label.label Auto Close
        .field-body.is-grouped
          input.is-checkradio(type="radio" id="keepopen" :checked="!isAutoClose" @click="isAutoClose = false" :disabled="scheduleStore.currentSchedule")
          label.label.ml-3.mt-1(for="keepopen") Keep open forever
          input.is-checkradio.ml-3(type="radio" id="autoclose" :checked="isAutoClose" @click="isAutoClose = true" :disabled="scheduleStore.currentSchedule")
          label.label.ml-3.mt-1(for="autoclose") Auto close operation
      .field.is-horizontal
        .field-label
          label.label Run State
        .field-body.is-grouped
          input.is-checkradio(type="radio" id="runimmediately" :checked="!isPause" @click="isPause = false")
          label.label.ml-3.mt-1(for="runimmediately") Run immediately
          input.is-checkradio.ml-3(type="radio" id="pausestart" :checked="isPause" @click="isPause = true")
          label.label.ml-3.mt-1(for="pausestart") Pause on start
      .field.is-horizontal
        .field-label
          label.label Jitter (sec/sec)
        .field-body
          input.input.is-small(v-model="minJitter" :disabled="scheduleStore.currentSchedule")
          span /
          input.input.is-small(v-model="maxJitter" :disabled="scheduleStore.currentSchedule")

    footer.modal-card-foot.is-justify-content-space-between
      div(v-if="!scheduleStore.currentSchedule")
      button.button.is-danger(@click="modals.schedules.showDelete = true" v-if="scheduleStore.currentSchedule") Delete
      div
        button.button(@click="closeModal()") Cancel
        button.button.is-primary(@click="callApi().then(() => {})")
          span(v-if="scheduleStore.currentSchedule") Update
          span(v-else) Create
</template>

<style scoped>
.modal-card {
  width: 800px;
}

.field-label label {
  font-size: 0.9rem;
}
</style>
