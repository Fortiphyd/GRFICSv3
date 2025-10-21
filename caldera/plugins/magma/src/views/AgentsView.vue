<script setup>
import { inject, onMounted, onBeforeUnmount, ref } from "vue";
import { storeToRefs } from "pinia";

import { useAgentStore } from '@/stores/agentStore';
import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import DeployModal from '@/components/agents/DeployModal.vue';
import ConfigModal from '@/components/agents/ConfigModal.vue';
import DetailsModal from "@/components/agents/DetailsModal.vue";
import { getAgentStatus } from "@/utils/agentUtil.js";

const $api = inject("$api");

const agentStore = useAgentStore();
const { agents, selectedAgent } = storeToRefs(agentStore);
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

let agentRefreshInterval = ref(null);

onMounted(async () => {
    await agentStore.getAgents($api);
    await agentStore.getAgentConfig($api);
    agentRefreshInterval.value = setInterval(async () => {
        await agentStore.getAgents($api);
    }, 3000);
});

onBeforeUnmount(() => {
    clearInterval(agentRefreshInterval.value);
})

function removeDeadAgents() {
    agents.value.forEach((agent, index) => {
        if (getAgentStatus(agent) === "dead") {
            agentStore.deleteAgent($api, agent.paw, index);
        }
    });
}

function removeAllAgents() {
    agents.value.forEach((agent, index) => agentStore.deleteAgent($api, agent.paw, index));
}

function killAllAgents() {
    agents.value.forEach((agent) => agentStore.killAgent($api, agent.paw));
}
</script>

<template lang="pug">
//- Header
.content
    h2 Agents
    p You must deploy at least 1 agent in order to run an operation. Groups are collections of agents so hosts can be compromised simultaneously.
hr

//- Button row
.columns.mb-4
    .column.is-4.is-flex.buttons.mb-0
        button.button.is-primary.level-item(@click="modals.agents.showDeploy = true")
            span.icon
                font-awesome-icon(icon="fas fa-plus") 
            span Deploy an agent
        button.button.is-primary.level-item(@click="modals.agents.showConfig = true")
            span.icon
                font-awesome-icon(icon="fas fa-cog")
            span Configuration
    .column.is-4.is-flex.is-justify-content-center
        span.tag.is-medium.m-0
            span.mr-4.has-text-success 
                span.has-text-weight-bold.mr-3 {{ agents.filter((a) => getAgentStatus(a) === 'alive' || getAgentStatus(a) === 'pending kill').length }} alive
                span.has-text-weight-bold {{ agents.filter((a) => a.trusted).length }} trusted
            strong.mr-4 {{ agents.length }} agent{{ agents.length > 1 ? 's' : '' }}
            span.mr-4.has-text-warning 
                span.has-text-weight-bold.mr-3 {{ agents.filter((a) => getAgentStatus(a) === 'dead').length }} dead
                span.has-text-weight-bold {{ agents.filter((a) => !a.trusted).length }} untrusted
    .column.is-4.is-flex.is-justify-content-end
        .dropdown.is-right.is-hoverable
            .dropdown-trigger 
                button.button.is-primary(aria-haspopup="true" aria-controls="bulk-actions")
                    span Bulk Actions 
                    span.icon 
                        font-awesome-icon(icon="fas fa-angle-down" aria-hidden="true")
            .dropdown-menu(role="menu")
                .dropdown-content 
                    a.dropdown-item(@click="removeDeadAgents()") Remove dead agents
                    a.dropdown-item(@click="removeAllAgents()") Remove all agents 
                    a.dropdown-item(@click="killAllAgents()") Kill all agents

//- Agents table
table.table.is-striped.is-hoverable.is-fullwidth(v-if="agents.length")
    thead
        tr
            th id (paw)
            th host 
            th group 
            th platform
            th contact
            th pid
            th privilege
            th status
            th last seen
            th
    tbody
        tr(v-for="(agent, index) in agents" :key="agent.paw" @click="selectedAgent = agent; modals.agents.showDetails = true")
            td {{ agent.paw }}
            td {{ agent.host }}
            td {{ agent.group }}
            td {{ agent.platform }}
            td {{ agent.contact }}
            td {{ agent.pid }}
            td {{ agent.privilege }}
            td 
                span(:class="{ 'has-text-warning': getAgentStatus(agent) === 'dead', 'has-text-success': getAgentStatus(agent) === 'alive', 'has-text-info': getAgentStatus(agent) === 'pending kill' }") {{ getAgentStatus(agent) }}
                span , 
                span(:class="{ 'has-text-warning': !agent.trusted, 'has-text-success': agent.trusted }") {{ agent.trusted ? 'trusted' : 'untrusted' }}
            td {{ new Date(agent.last_seen).toLocaleString() }}
            td.has-text-centered 
                button.delete.is-white(@click.stop="agentStore.deleteAgent($api, agent.paw, index)")
.has-text-centered.content(v-if="!agents.length")
    p No deployed agents

//- Modals
DeployModal
ConfigModal
DetailsModal
</template>

<style scoped>
tr {
    cursor: pointer;
}
</style>
