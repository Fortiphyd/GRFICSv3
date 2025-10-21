<script setup>
import { ref, onMounted } from 'vue';

const { modelValue, items, placeholder, isDanger } = defineProps({ 
    modelValue: String,
    items: Array,
    placeholder: String,
    isDanger: Boolean
});
const emit = defineEmits(['update:modelValue']);

let results = ref([]);
let isFocused = ref(false);
let isMouseover = ref(false);

onMounted(() => {
    getResults("");
})

function getResults(value) {
    results.value = items.filter((item) => {
        const a = item.toString().toLowerCase();
        const b = value.toLowerCase();
        return a.includes(b) && a !== b;
    });
}

function selectItem(result) {
    emit('update:modelValue', result);
    getResults(result);
    isFocused.value = false;
    isMouseover.value = false;
}

function updateValue(event) {
    emit('update:modelValue', event.target.value);
    getResults(event.target.value);
}
</script>

<template lang="pug">
input.input(type="text" :placeholder="placeholder" :value="modelValue" @input="updateValue" autocomplete="off" @focus="isFocused = true; getResults(modelValue || '')" @focusout="isFocused = false" :class="{ 'is-danger': isDanger }")
.results(v-if="isFocused || isMouseover" @mouseenter="isMouseover = true" @mouseleave="isMouseover = false")
    a.dropdown-item(v-for="result in results" @click="selectItem(result)") {{ result }}
</template>

<style scoped>
.results {
    background-color: hsl(0deg, 0%, 14%);
    border-radius: 8px;
    margin-top: 4px;
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 20;
    width: 100%;
    overflow-y: scroll;
    max-height: 200px;
}
</style>
