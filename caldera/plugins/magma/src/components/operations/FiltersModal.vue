<script setup>
import { inject, reactive, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { LINK_STATUSES } from "@/utils/operationUtil.js";
const $api = inject("$api");
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

const { filters, possibleFilters } = defineProps({
  filters: Object,
  possibleFilters: Object,
});

const handleLinkInput = (event) => {
  if (event.target.checked) {
    filters.status.push(event.target.value);
  } else {
    filters.status = filters.status.filter(
      (status) => status !== event.target.value
    );
  }
};
const handleAbilityInput = (event) => {
  if (event.target.checked) {
    filters.abilityName.push(event.target.value);
  } else {
    filters.abilityName = filters.abilityName.filter(
      (name) => name !== event.target.value
    );
  }
};
const handleTacticInput = (event) => {
  if (event.target.checked) {
    filters.tactic.push(event.target.value);
  } else {
    filters.tactic = filters.tactic.filter(
      (name) => name !== event.target.value
    );
  }
};
const handleAgentInput = (event) => {
  if (event.target.checked) {
    filters.paw.push(event.target.value);
  } else {
    filters.paw = filters.paw.filter((name) => name !== event.target.value);
  }
};
const handleHostInput = (event) => {
  if (event.target.checked) {
    filters.host.push(event.target.value);
  } else {
    filters.host = filters.host.filter((name) => name !== event.target.value);
  }
};
const clearFilters = () => {
  filters.decide = [];
  filters.status = [];
  filters.abilityName = [];
  filters.paw = [];
  filters.tactic = [];
  filters.host = [];
  filters.pid = [];
};
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.operations.showFilters }")
    .modal-background(@click="modals.operations.showFilters = false")
    .modal-card
        header.modal-card-head
            p.modal-card-title Filter Operation
        .modal-card-body
          div.is-flex.is-flex-direction-row#filter-container
            ul Statuses
              li(v-for="(value, key) in LINK_STATUSES")
                input(type="checkbox" @input="handleLinkInput" :value="key" :checked="filters.status.includes(key)")
                span.ml-2 {{ value }}
            ul Abilities
              li(v-for="ability in possibleFilters.abilityName")
                input(type="checkbox" @input="handleAbilityInput" :value="ability" :checked="filters.abilityName.includes(ability)")
                span.ml-2 {{ ability }}
            ul Tactics
              li(v-for="tactic in possibleFilters.tactic")
                input(type="checkbox" @input="handleTacticInput" :value="tactic" :checked="filters.tactic.includes(tactic)")
                span.ml-2 {{ tactic }}
            ul Agents
              li(v-for="agent in possibleFilters.paw")
                input(type="checkbox" @input="handleAgentInput" :value="agent" :checked="filters.paw.includes(agent)")
                span.ml-2 {{ agent }}
            ul Hosts
              li(v-for="host in possibleFilters.host")
                input(type="checkbox" @input="handleHostInput" :value="host" :checked="filters.host.includes(host)")
                span.ml-2 {{ host }}
        footer.modal-card-foot.has-text-right
            button.button(@click="clearFilters()") Clear Filters 
            button.button(@click="modals.operations.showFilters = false") Close 
</template>

<style scoped>
.modal-card-foot {
  display: block;
}
.modal-card {
  width: auto;
}
#filter-container {
  gap: 1rem;
}
ul {
  background-color: hsl(0deg, 0%, 14%);
  border-radius: 0.25rem;
  padding: 1rem;
  box-shadow: 0 0 0.5rem hsl(0deg, 0%, 14%);
}
li:first-child {
  margin-top: 0.5rem;
}
li span {
  white-space: nowrap;
}
</style>
