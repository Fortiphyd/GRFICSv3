<script setup>
import { ref, inject } from "vue";
import { storeToRefs } from "pinia";

import { useAdversaryStore } from "@/stores/adversaryStore.js";

const $api = inject("$api");

const adversaryStore = useAdversaryStore();
const { selectedObjective } = storeToRefs(adversaryStore);

const OPERATORS = [ "<", ">", "<=", ">=", "in", "*", "==" ];
let goalIndexToEdit = ref(-1);

async function addNewGoal() {
    selectedObjective.value.goals.push({
        target: "",
        operator: "==",
        value: "",
        count: 1,
        achieved: false
    });
    saveObjective();
}

async function saveObjective() {
    await adversaryStore.saveObjective($api);
    goalIndexToEdit.value = -1;
}

function removeGoal(goalIndex) {
    selectedObjective.value.goals.splice(goalIndex, 1);
    saveObjective();
}
</script>

<template lang="pug">
.buttons
    button.button(@click="addNewGoal()")
        span.icon
            font-awesome-icon(icon="fas fa-plus")
        span Add Goal
table.table.is-striped.is-fullwidth
    thead
        tr
            th Target
            th Operator
            th Value
            th Count
            th Achieved
            th
    tbody
        tr(v-for="(goal, index) in selectedObjective.goals")
            td 
                input.input(v-if="goalIndexToEdit === index" v-model="goal.target" placeholder="Goal target")
                span(v-else) {{ goal.target }}
            td 
                .control(v-if="goalIndexToEdit === index")
                    .select
                        select(v-model="goal.operator")
                            option(v-for="op in OPERATORS" :value="op") {{ op }}
                span(v-else) {{ goal.operator }}
            td 
                input.input(v-if="goalIndexToEdit === index" v-model="goal.value" placeholder="Goal value")
                span(v-else) {{ goal.value }}
            td 
                input.input(v-if="goalIndexToEdit === index" type="number" v-model="goal.count" placeholder="Goal count")
                span(v-else) {{ goal.count }}
            td {{ goal.achieved }}
            td
                .buttons
                    button.button.is-primary(
                            v-if="goalIndexToEdit === index" @click="saveObjective()"
                            :disabled="false"
                            )
                        span.icon
                            font-awesome-icon(icon="fa-save")
                    button.button(v-else @click="goalIndexToEdit = index")
                        span.icon
                            font-awesome-icon(icon="fa-pencil-alt")
                    button.button.is-danger.is-outlined(@click="removeGoal(index)")
                        span.icon
                            font-awesome-icon(icon="fa-trash")
</template>
