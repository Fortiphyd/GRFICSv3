<script setup>
import { inject, ref, reactive, watch, onMounted } from "vue";
import { storeToRefs } from "pinia";

import { useAbilityStore } from "@/stores/abilityStore";
import CodeEditor from "@/components/core/CodeEditor.vue";
import AutoSuggest from "@/components/core/AutoSuggest.vue";

const props = defineProps({
  ability: Object,
  active: Boolean,
  creating: Boolean,
});
const emit = defineEmits(["close"]);

const $api = inject("$api");

const abilityStore = useAbilityStore();
const { tactics, techniqueIds, techniqueNames, platforms, payloads } =
  storeToRefs(abilityStore);

let abilityToEdit = ref({});
let validation = reactive({
  name: "",
  tactic: "",
  techniqueId: "",
  techniqueName: "",
  executors: "",
});

onMounted(async () => {
  await abilityStore.getAbilities($api);
  await abilityStore.getPayloads($api);
});

watch(
  () => props.ability,
  () => {
    setAbilityToEdit();
  }
);

function setAbilityToEdit() {
  abilityToEdit.value = JSON.parse(JSON.stringify(props.ability));
  if (!abilityToEdit.value.requirements) {
    abilityToEdit.value.requirements = [];
  }
}

function addExecutor() {
  const baseExecutor = {
    cleanup: [],
    timeout: 60,
    platform: "darwin",
    name: platforms.value.darwin[0],
    payloads: [],
    parsers: [],
  };
  if (!abilityToEdit.value.executors) {
    abilityToEdit.value.executors = [baseExecutor];
  } else {
    abilityToEdit.value.executors.push(baseExecutor);
  }
}

function validateAndSave() {
  validation.name = abilityToEdit.value.name ? "" : "Name cannot be empty";
  validation.tactic = abilityToEdit.value.tactic
    ? ""
    : "Tactic cannot be empty";
  validation.techniqueId = abilityToEdit.value.technique_id
    ? ""
    : "Technique ID cannot be empty";
  validation.techniqueName = abilityToEdit.value.technique_name
    ? ""
    : "Technique Name cannot be empty";
  validation.executors =
    abilityToEdit.value.executors &&
    abilityToEdit.value.executors.every(
      (executor) =>
        executor.platform &&
        executor.name &&
        executor.command &&
        executor.timeout !== null &&
        executor.timeout >= 0
    )
      ? ""
      : "There must be at least 1 executor. Each executor must have a command, platform, timeout, and executor.";

  if (Object.keys(validation).every((k) => !validation[k])) {
    abilityStore.saveAbility($api, abilityToEdit.value, props.creating);
    emit("close");
  }
}

async function deleteAbility() {
  await abilityStore.deleteAbility($api, abilityToEdit.value.ability_id);
  emit("close");
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': props.active }")
    .modal-background(@click="emit('close')")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title {{ props.creating ? 'Create' : 'Edit' }} Ability
        .modal-card-body.content.m-0
            form
                label.label Ability ID
                .field(v-if="!props.creating")
                    .control
                        input.input(v-model="abilityToEdit.ability_id" disabled)
                .field(v-else)
                    p.is-italic ID will be automatically created
                .field
                    label.label Name
                    .control
                        input.input(v-model="abilityToEdit.name" :class="{ 'is-danger': validation.name }")
                        p.has-text-danger {{ validation.name }}
                .field
                    label.label Description
                    .control
                        textarea.textarea(v-model="abilityToEdit.description")
                .field
                    label.label Tactic
                    .control(v-if="tactics.length > 0")
                        AutoSuggest(v-model="abilityToEdit.tactic" :items="tactics" :isDanger="!!validation.tactic" placeholder="Tactic")
                        p.has-text-danger {{ validation.tactic }}
                .field
                    label.label Technique ID
                    .control(v-if="techniqueIds.length > 0")
                        AutoSuggest(v-model="abilityToEdit.technique_id" :items="techniqueIds" :isDanger="!!validation.techniqueId" placeholder="Technique ID")
                        p.has-text-danger {{ validation.techniqueId }}
                .field
                    label.label Technique Name
                    .control(v-if="techniqueNames.length > 0")
                        AutoSuggest(v-model="abilityToEdit.technique_name" :items="techniqueNames" :isDanger="!!validation.techniqueName" placeholder="Technique Names")
                        p.has-text-danger {{ validation.techniqueName }}
                .field
                    label.label Options
                    .control
                        input(type="checkbox" v-model="abilityToEdit.singleton")
                        span.ml-3 Singleton
                .field
                    .control
                        input(type="checkbox" v-model="abilityToEdit.repeatable")
                        span.ml-3 Repeatable
                .field
                        .control
                            input(type="checkbox" v-model="abilityToEdit.delete_payload")
                            span.ml-3 Delete payload
            p.has-text-centered Executors
            p.has-text-danger {{ validation.executors }}
            .has-text-centered
                button.button.is-primary.mb-4(@click="addExecutor()")
                    span.icon
                        font-awesome-icon(icon="fas fa-plus")
                    span Add Executor
            .box(v-for="(executor, index) in abilityToEdit.executors" :key="index + (abilityToEdit.ability_id ? abilityToEdit.ability_id : 0)")
                button.button.delete-btn(@click="abilityToEdit.executors.splice(index, 1)")
                    span.icon
                        font-awesome-icon(icon="fas fa-times")
                form
                    .field
                        label.label Platform
                        .control
                            .select
                                select(v-model="executor.platform")
                                    option(v-for="platform in Object.keys(platforms)" :value="platform") {{ platform }}
                    .field
                        label.label Executor
                        .control
                            .select
                                select(v-model="executor.name")
                                    option(v-for="exec in platforms[executor.platform]" :value="exec") {{ exec }}
                    .field.is-grouped.is-grouped-multiline
                        label.label Payloads
                        br
                        .control(v-if="executor.payloads.length === 0" class="ml-4")
                            span.tag.is-light No payloads
                        .control(v-for="(payload, idx) in executor.payloads" class="ml-4")
                          .tags.has-addons
                            span.tag.is-primary {{ payload }}
                            a.tag.is-delete(@click="executor.payloads.splice(idx, 1)")
                    .field
                        .control.mt-3
                            div.select.is-small.is-multiple.is-fullwidth
                              select.select.is-multiple(multiple size="6")
                                template(v-for="payload in payloads")
                                  option(v-if="executor.payloads.indexOf(payload) === -1" @click="executor.payloads.push(payload)") {{ payload }}
                    .field
                        label.label Command
                        .control
                            CodeEditor(v-model="executor.command" :key="index" language="bash" line-numbers)
                    .field
                        label.label Timeout
                        .control
                            input.input(type="number" v-model="executor.timeout")
                    .field
                      label.label Cleanup
                      .field.has-addons(v-for="(cleanup, index) of executor.cleanup")
                          .control.is-expanded
                              CodeEditor(v-model="executor.cleanup[index]" :key="index" language="bash" line-numbers)
                          .control
                              a.button(@click="executor.cleanup.splice(index, 1)")
                                  span.icon
                                      font-awesome-icon(icon="fas fa-times")
                      button.button(type="button" @click="executor.cleanup.push('')")
                          span.icon
                              font-awesome-icon(icon="fas fa-plus")
                          span Add Cleanup Command
                    .field
                      label.label Requirements
                      .field.has-addons(v-for="(requirement, index) of abilityToEdit.requirements")
                          .control.is-expanded
                            .field
                              span Requirement Module
                              .control
                                input.input(type="text" v-model="abilityToEdit.requirements[index].module" placeholder="Requirement Module")
                            .field
                              span Source
                              .field.has-addons(v-for="(relationship, r_index) of abilityToEdit.requirements[index].relationship_match")
                                .field
                                  .control
                                    input.input(type="text" v-model="abilityToEdit.requirements[index].relationship_match[r_index].source" placeholder="Source")
                                .field
                                  .control
                                    input.input(type="text" v-model="abilityToEdit.requirements[index].relationship_match[r_index].edge" placeholder="Edge [optional]")
                                .field 
                                  .control
                                    input.input(type="text" v-model="abilityToEdit.requirements[index].relationship_match[r_index].target" placeholder="Target [optional]")
                          .control
                              a.button(@click="abilityToEdit.requirements.splice(index, 1)")
                                  span.icon
                                      font-awesome-icon(icon="fas fa-times")
                      button.button(type="button" @click="abilityToEdit.requirements.push({module: '',relationship_match:[{source:'', edge:'',target:''}]})")
                          span.icon
                              font-awesome-icon(icon="fas fa-plus")
                          span Add Requirement
                    .field
                      label.label Parsers
                      .field.has-addons(v-for="(parser, index) of executor.parsers")
                          .control.is-expanded
                            .field
                              span Parser Module
                              .control
                                input.input(type="text" v-model="executor.parsers[index].module" placeholder="Parser Module")
                            .field
                              span Output Source(s)
                                .field.has-addons(v-for="(parserconfig, pc_index) of executor.parsers[index].parserconfigs")
                                    .field
                                      .control
                                        input.input(type="text" v-model="executor.parsers[index].parserconfigs[pc_index].source" placeholder="Output Source")
                                    .field
                                      .control
                                        input.input(type="text" v-model="executor.parsers[index].parserconfigs[pc_index].edge" placeholder="Output Edge [optional]")
                                    .field
                                      .control
                                        input.input(type="text" v-model="executor.parsers[index].parserconfigs[pc_index].target" placeholder="Output Target [optional]")
                          .control
                              a.button(@click="executor.parsers.splice(index, 1)")
                                  span.icon
                                      font-awesome-icon(icon="fas fa-times")
                      button.button(type="button" @click="executor.parsers.push({module: '', parserconfigs: [{source:'', edge:'', target:''}]})")
                          span.icon
                              font-awesome-icon(icon="fas fa-plus")
                          span Add Parser
            p.has-text-danger(v-if="abilityToEdit.executors && abilityToEdit.executors.length") {{ validation.executors }}
            .has-text-centered
                button.button.is-primary.mb-4(v-if="abilityToEdit.executors && abilityToEdit.executors.length" @click="addExecutor()")
                    span.icon
                        font-awesome-icon(icon="fas fa-plus")
                    span Add Executor
        footer.modal-card-foot.is-flex.is-justify-content-space-between
            .is-flex
                button.button(@click="setAbilityToEdit()") 
                    span.icon
                        font-awesome-icon(icon="fas fa-undo")
                    span Reset
                button.button.is-danger.is-outlined(v-if="!props.creating" @click="deleteAbility()") 
                    span.icon
                        font-awesome-icon(icon="fas fa-trash")
                    span Delete
            .is-flex
                button.button(@click="emit('close')") Cancel 
                button.button.is-primary(@click="validateAndSave()")
                    span.icon
                        font-awesome-icon(icon="fas fa-save") 
                    span {{ props.creating ? "Create" : "Save" }} 
</template>

<style scoped>
.box {
  position: relative;
}

.delete-btn {
  position: absolute;
  top: 18px;
  right: 20px;
}

.modal-card {
  width: 1000px;
}

@media screen and (max-width: 1050px) {
  .modal-card {
    width: 600px;
  }
}
</style>
