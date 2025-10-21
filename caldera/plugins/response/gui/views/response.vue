<script setup>
import { ref, onMounted, inject } from "vue";

const $api = inject("$api");
const adversaries = ref([]);
const selectedAdversaryId = ref("");
const abilities = ref([]);

const getAdversaries = async () => {
  const { data } = await $api.get("/plugin/responder/adversaries");
  adversaries.value = data.adversaries;
  selectedAdversaryId.value = data.auto_response;
};
const getAbilities = async () => {
  const { data } = await $api.get("/plugin/responder/abilities");
  abilities.value = data;
};
const saveAutoResponse = async () => {
  await $api.post("/plugin/responder/update", {
    adversary_id: selectedAdversaryId.value,
  });
};

onMounted(() => {
  getAdversaries();
  getAbilities();
});
</script>

<template lang="pug">
  
.content
  h2 Response
  p Think of response as the blue version of the stockpile plugin. Specific blue team response actions are stored here as abilities. Instead of adversaries,you'll find defenders, which can be launched on a host to protect it against an attacker.
hr
.content
  .columns
    .column
      .select.is-fullwidth
        select(v-model="selectedAdversaryId")
          option(v-for="adversary in adversaries" :value="adversary.adversary_id") {{ adversary.name }}
        button.button.is-primary.mt-4(@click="saveAutoResponse") Save
    .column.info
      .inner-col
        h3 abilities
        h1 {{ abilities.length}}
      .inner-col
        h3 defenders
        h1 {{ adversaries.length}}

</template>

<style scoped>
.inner-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.info {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-around;
}
</style>
