<script setup>
import { ref, inject, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { toast } from 'bulma-toast'

import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import { useOperationStore } from '@/stores/operationStore';
import { useAdversaryStore } from "@/stores/adversaryStore";
import { useCoreStore } from "@/stores/coreStore";
import { useAgentStore } from "@/stores/agentStore";
import { useSourceStore } from "@/stores/sourceStore";

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
const adversaryStore = useAdversaryStore();
const operationStore = useOperationStore();
const coreStore = useCoreStore();
const agentStore = useAgentStore();
const sourceStore = useSourceStore();
const { sources } = storeToRefs(sourceStore);

const props = defineProps({
    selectInterval: {
        type: Function,
    },
});

let operationName = ref("");
let selectedAdversary = ref("");
let selectedSource = ref("")
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

async function getSources() {
    try {
        await sourceStore.getSources($api);
        selectedSource.value = sources.value.find(source => source.name === "basic");
    } catch(error) {
        console.error("Error getting sources", error);
    }
}

async function getPlanners() {
    try {
        await coreStore.getPlanners($api);
        selectedPlanner.value = coreStore.planners[0];
    } catch(error) {
        console.error("Error getting planners", error);
    }
}

async function createOperation() {
    if(!operationName.value){
        validation.value.name = "Name cannot be empty";
        return;
    }
    validation.value.name = "";
    if(!selectedAdversary.value.adversary_id){
        selectedAdversary.value = {adversary_id: "ad-hoc"};
    }
    const newOperation = {
        name: operationName.value,
        autonomous: Number(isAuto.value),
        use_learning_parsers: isDefParser.value,
        auto_close: isAutoClose.value,
        jitter: `${minJitter.value}/${maxJitter.value}`,
        state: isPause ? "running" : "paused",
        visibility: visibility.value,
        obfuscator: selectedObfuscator.value.name,
        source: {id: JSON.parse(JSON.stringify(selectedSource.value.id))},
        planner: {id: JSON.parse(JSON.stringify(selectedPlanner.value.id))},
        adversary: {adversary_id: JSON.parse(JSON.stringify(selectedAdversary.value.adversary_id))},
        group: selectedGroup.value,
    };
    try {
        await operationStore.createOperation($api, newOperation);
        props.selectInterval();
        toast({
            message: `Operation ${operationName.value} created`,
            type: 'is-success',
            dismissible: true,
            pauseOnHover: true,
            duration: 2000,
            position: "bottom-right",
        });
    } catch(error) {
        console.error("Error creating operation", error);
        toast({
            message: `Error creating operation`,
            type: 'is-danger',
            dismissible: true,
            pauseOnHover: true,
            duration: 2000,
            position: "bottom-right",
        });
    }
    modals.value.operations.showCreate = false
}

</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.operations.showCreate }")
    .modal-background(@click="modals.operations.showCreate = false")
    .modal-card
        header.modal-card-head 
            p.modal-card-title Start New Operation
        .modal-card-body
            .field.is-horizontal
                .field-label.is-normal 
                    label.label Operation Name
                .field-body 
                    input.input(placeholder="Operation Name" v-model="operationName")
                    label.label.ml-3.mt-1.has-text-danger {{ `${validation.name}` }}
            .field.is-horizontal
                .field-label.is-normal 
                    label.label Adversary
                .field-body
                    .control
                        .select
                            select(v-model="selectedAdversary")
                                option(selected value="") No Adversary (manual)
                                option(v-for="adversary in adversaryStore.adversaries" :key="adversary.id" :value="adversary") {{ `${adversary.name}` }}
            .field.is-horizontal
                .field-label.is-normal 
                    label.label Fact Source
                .field-body
                    .control
                        .select
                            select(v-model="selectedSource")
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
                            select(v-model="selectedPlanner")
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
                        input.is-checkradio(type="radio" id="defaultparser" :checked="isDefParser" @click="isDefParser = true")
                        label.label.ml-3.mt-1(for="defaultparser") Use Default Parser
                        input.is-checkradio.ml-3(type="radio" id="nondefaultparser" :checked="!isDefParser" @click="isDefParser = false")
                        label.label.ml-3.mt-1(for="nondefaultparser") Don't use default learning parsers
            .field.is-horizontal
                .field-label 
                    label.label Auto Close
                .field-body.is-grouped
                    input.is-checkradio(type="radio" id="keepopen" :checked="!isAutoClose" @click="isAutoClose = false")
                    label.label.ml-3.mt-1(for="keepopen") Keep open forever
                    input.is-checkradio.ml-3(type="radio" id="autoclose" :checked="isAutoClose" @click="isAutoClose = true")
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
                    input.input.is-small(v-model="minJitter")
                    span /
                    input.input.is-small(v-model="maxJitter")
        footer.modal-card-foot.is-justify-content-right
            button.button(@click="modals.operations.showCreate = false") Cancel
            button.button.is-primary(@click="createOperation()") Start 
</template>

<style scoped>
.modal-card {
    width: 800px;
}

.field-label label{
    font-size: 0.9rem;
}
</style>
