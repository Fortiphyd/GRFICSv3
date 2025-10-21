<script setup>
import { ref, inject } from "vue";
import { storeToRefs } from "pinia";
import { toast } from "bulma-toast";

import AbilitySelection from "@/components/abilities/AbilitySelection.vue";
import AddAbilitiesFromAdversaryModal from "@/components/adversaries/AddAbilitiesFromAdversaryModal.vue";
import { useSourceStore } from "@/stores/sourceStore.js";
import { getAbilityFacts } from "@/utils/abilityUtil.js";

const $api = inject("$api");

const sourceStore = useSourceStore();
const { selectedSource } = storeToRefs(sourceStore);

let factIndexToEdit = ref(-1);
let showAbilitySelection = ref(false);
let showAddFromAdversary = ref(false);

function addFact() {
  selectedSource.value.facts.push({
    trait: "",
    value: "",
    score: 0,
  });
  factIndexToEdit.value = selectedSource.value.facts.length - 1;
}

function removeFact(factIndex) {
  selectedSource.value.facts.splice(factIndex, 1);
  saveFacts();
}

async function saveFacts() {
  factIndexToEdit.value = -1;
  await sourceStore.saveSource($api);
}

async function addFromAbility(ability) {
  const abilityFacts = getAbilityFacts(ability);
  if (!abilityFacts.length) {
    toast({
      message: "Ability has no facts to add",
      position: "bottom-right",
      type: "is-warning",
      dismissible: true,
      pauseOnHover: true,
      duration: 2000,
    });
    showAbilitySelection.value = false;
    return;
  }

  abilityFacts.forEach((fact) => {
    selectedSource.value.facts.push({
      trait: fact,
      value: "",
      score: 0,
    });
  });
  showAbilitySelection.value = false;
  await sourceStore.saveSource($api);
}

async function addFromAdversary(abilities) {
  abilities.forEach((ability) => addFromAbility(ability));
  showAddFromAdversary.value = false;
}

const getFactOriginShort = (originType) => {
  switch (originType) {
    case "IMPORTED":
      return "IMP";
    case "SEEDED":
      return "SED";
    case "LEARNED":
      return "LRN";
    case "USER":
      return "USR";
    case "DOMAIN":
      return "DOM";
  }
};
const getFactOriginColor = (originType) => {
  switch (originType) {
    case "IMPORTED":
      return "has-background-primary-dark";
    case "SEEDED":
      return "is-warning";
    case "LEARNED":
      return "is-success";
    case "USER":
      return "is-info";
    case "DOMAIN":
      return "is-primary";
  }
};
</script>

<template lang="pug">
.buttons.m-0
    button.button(@click="addFact()")
        span.icon
            font-awesome-icon(icon="fas fa-plus")
        span Add Fact
    button.button(@click="showAbilitySelection = true")
        span.icon
            font-awesome-icon(icon="fas fa-plus")
        span Add Facts from Ability
    button.button(@click="showAddFromAdversary = true")
        span.icon
            font-awesome-icon(icon="fas fa-plus")
        span Add Facts from Adversary

table.table.is-striped.is-fullwidth
    colgroup(width="30%")
    colgroup(width="30%")
    colgroup(width="20%")
    colgroup(width="20%")
    thead
        tr
            th Fact Trait
            th Fact Value
            th Score
            th
    tbody
        tr(v-for="(fact, index) of selectedSource.facts")
            td 
                input.input(v-if="factIndexToEdit === index" v-model="fact.trait" placeholder="Fact trait")
                div.is-flex.is-flex-direction-row(v-else)
                  span {{ fact.trait || "---" }}
                  #fact-source-icon.tag.ml-2(v-if="fact.origin_type" :class="getFactOriginColor(fact.origin_type)" v-tooltip="`Origin: ${fact.origin_type.toLowerCase()}`") {{ getFactOriginShort(fact.origin_type) }}
            td 
                input.input(v-if="factIndexToEdit === index" v-model="fact.value" placeholder="Fact value")
                span(v-else) {{ fact.value || "---" }}
            td 
                input.input(v-if="factIndexToEdit === index" v-model="fact.score" placeholder="Fact score")
                span(v-else) {{ fact.score }}
            td
                .buttons
                    button.button.is-primary(
                            v-if="factIndexToEdit === index" @click="saveFacts()")
                        span.icon
                            font-awesome-icon(icon="fa-save")
                    button.button(v-else @click="factIndexToEdit = index")
                        span.icon
                            font-awesome-icon(icon="fa-pencil-alt")
                    button.button.is-danger.is-outlined(@click="removeFact(index)")
                        span.icon
                            font-awesome-icon(icon="fa-trash")

//- Modals
AbilitySelection(:active="showAbilitySelection" @select="addFromAbility" @close="showAbilitySelection = false" :canCreate="false")
AddAbilitiesFromAdversaryModal(:active="showAddFromAdversary" @select="addFromAdversary" @close="showAddFromAdversary = false")

</template>

<style scoped>
#fact-source-icon {
  font-size: 0.95em;
}
</style>
