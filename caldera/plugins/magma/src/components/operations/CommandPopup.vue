<script setup>
import { inject, ref, computed } from "vue";

import { useOperationStore } from "@/stores/operationStore";
import { b64DecodeUnicode } from "@/utils/utils";
import { toast } from "bulma-toast";

const props = defineProps({
  link: Object,
});

const $api = inject("$api");

const operationStore = useOperationStore();

let editableCommand = ref(props.link.command || "");

const command = computed(() => {
  if (props.link.command === props.link.plaintext_command) return "";
  return props.link.command;
});
const plaintextCommand = computed(() => {
  return props.link.plaintext_command;
});
const isCommandObfuscated = computed(() => {
  return command.value !== "";
});

function isLinkEditable(currentLink) {
  if (!currentLink) return false;
  // Link can only be editable if operation is running, and if link is paused, queued, or completed
  return (
    operationStore.isOperationRunning() &&
    currentLink.status === -1 &&
    !(currentLink.finish || currentLink.output === "True")
  );
}

function copyCommand() {
  if (plaintextCommand.value === "") return;
  navigator.clipboard.writeText(plaintextCommand.value);
  toast({
    message: "Copied command to clipboard",
    type: "is-success",
    position: "bottom-right",
    dismissible: true,
    pauseOnHover: true,
    duration: 2000,
  });
}
</script>

<template lang="pug">
section(v-if="isLinkEditable(props.link)")
    p.is-size-5 Edit Command:
    textarea.input(v-model="editableCommand")
.box.p-0.mb-2(v-else)
    div(v-if="isCommandObfuscated")
        label.label Obfuscated
        pre.m-0.pt-2.pb-2 {{ command }}
        label.label.mt-2 Plaintext
        pre.m-0.pt-2.pb-2 {{ plaintextCommand }}
    pre.m-0.pt-2.pb-2(v-else) {{ plaintextCommand }}
    a.button.is-outlined.is-fullwidth(v-if="!isLinkEditable(props.link)" @click="copyCommand()")
        span.icon
            font-awesome-icon(icon="far fa-copy").fa-lg
        span Copy
    
.buttons.p-2(v-if="isLinkEditable(props.link)")
    button.button.is-primary(@click="operationStore.updateLink($api, -3, editableCommand, props.link)") Approve
    button.button.is-danger.ml-auto(@click="operationStore.updateLink($api, -2, null, props.link)") Discard 
</template>

<style>
.buttons {
  flex-wrap: nowrap !important;
}
</style>
