<script setup>
import { ref, onMounted } from "vue";
import { PrismEditor } from "vue-prism-editor";
import "vue-prism-editor/dist/prismeditor.min.css";

import { highlight, languages } from "prismjs/components/prism-core";
import "prismjs/themes/prism-tomorrow.css";

// Add any languages to support here
import "prismjs/components/prism-bash";

const { modelValue, lineNumbers, language } = defineProps({ 
    modelValue: String,
    lineNumbers: Boolean,
    language: String,
});

const intervalValue = ref(modelValue);

onMounted(() => {
})

const emit = defineEmits(['update:modelValue']); 

let focused = ref(false);

function highlighter(code) { 
    let lang = languages[language];

    if (language === "bash") {
        delete lang.comment;
        lang.fact = {
            pattern: /\#{.*?\}/,
            greedy: true
        };
        lang.string.forEach((str) => {
            str.inside = {
                fact: /\#{.*?\}/
            };
        });
    }

    return highlight(code, lang);
}

function updateValue(event) {
    intervalValue.value = event.target.value
    emit('update:modelValue', event.target.value);
}
</script>

<template lang="pug">
prism-editor.my-editor(v-model="intervalValue" @input="updateValue" @focus="focused = true" @blur="focused = false" :highlight="highlighter" :line-numbers="lineNumbers" :class="{ focused }")
</template>

<style scoped>
.my-editor {
    background: hsl(0deg, 0%, 14%);
    color: #ccc;
    border: 1px solid hsl(0deg, 0%, 30%);
    border-radius: 8px;
    height: auto;

    font-family: Fira code, Fira Mono, Consolas, Menlo, Courier, monospace;
    font-size: 14px;
    line-height: 1.5;
    padding: 5px;
}
.my-editor:hover {
    border-color: hsl(0deg, 0%, 71%);
}
.my-editor.focused {
    border-color: white;
}
</style>

<style>
.token.number {
    background-color: transparent;
    display: inline-block;
    font-size: inherit;
    margin: 0;
    padding: 0;
    height: auto;
    min-width: auto;
}

.token.fact {
    color: yellow;
}
</style>
