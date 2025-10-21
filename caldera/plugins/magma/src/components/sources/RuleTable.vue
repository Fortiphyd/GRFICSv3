<script setup>
import { ref, inject } from "vue";
import { storeToRefs } from "pinia";

import { useSourceStore } from "@/stores/sourceStore.js";

const $api = inject("$api");

const sourceStore = useSourceStore();
const { selectedSource } = storeToRefs(sourceStore);

let ruleIndexToEdit = ref(-1);

function addRule() {
    selectedSource.value.rules.push({
        trait: "",
        action: "ALLOW",
        match: ""
    });
    ruleIndexToEdit.value = selectedSource.value.rules.length - 1;
}

function removeRule(ruleIndex) {
    selectedSource.value.rules.splice(ruleIndex, 1);
    saveRules();
}

async function saveRules() {
    ruleIndexToEdit.value = -1;
    await sourceStore.saveSource($api);
} 
</script>

<template lang="pug">
.buttons.m-0
    button.button(@click="addRule()")
        span.icon
            font-awesome-icon(icon="fas fa-plus")
        span Add Rule

table.table.is-striped.is-fullwidth
    thead
        tr
            th Trait
            th Action
            th Match
            th
    tbody
        tr(v-for="(rule, index) of selectedSource.rules")
            td 
                input.input(v-if="ruleIndexToEdit === index" v-model="rule.trait" placeholder="Rule trait")
                span(v-else) {{ rule.trait }}
            td 
                .control(v-if="ruleIndexToEdit === index")
                    input.switch#ruleAction(
                        :checked="rule.action === 'ALLOW'" 
                        type="checkbox" 
                        @change="rule.action === 'ALLOW' ? rule.action = 'DENY' : rule.action = 'ALLOW'"
                    )
                    label.label(for="ruleAction") {{ rule.action }} 
                span.tag(v-else :class="{ 'is-success': rule.action === 'ALLOW', 'is-danger': rule.action === 'DENY' }") {{ rule.action }}
            td 
                input.input(v-if="ruleIndexToEdit === index" v-model="rule.match" placeholder="Rule match")
                span(v-else) {{ rule.match }}
            td
                .buttons
                    button.button.is-primary(
                            v-if="ruleIndexToEdit === index" @click="saveRules()"
                            :disabled="!rule.trait || !rule.match"
                            )
                        span.icon
                            font-awesome-icon(icon="fa-save")
                    button.button(v-else @click="ruleIndexToEdit = index")
                        span.icon
                            font-awesome-icon(icon="fa-pencil-alt")
                    button.button.is-danger.is-outlined(@click="removeRule(index)")
                        span.icon
                            font-awesome-icon(icon="fa-trash")

</template>
