<script setup>
import { ref, inject } from "vue";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { storeToRefs } from "pinia";
import { useAdversaryStore } from "../../stores/adversaryStore";

const $api = inject("$api");

const adversaryStore = useAdversaryStore();
const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.adversaries.showDeleteConfirm }")
    .modal-background(@click="modals.adversaries.showDeleteConfirm = false")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title Delete Adversary
        .modal-card-body 
            br
            p.block Are you sure you want to delete this adversary? This action cannot be undone
            br

        footer.modal-card-foot.is-flex.is-justify-content-flex-end 
            button.button(@click="modals.adversaries.showDeleteConfirm = false") Cancel
            button.button.is-danger(@click="adversaryStore.deleteAdversary($api) && (modals.adversaries.showDeleteConfirm = false)")
                span.icon
                    font-awesome-icon(icon="fas fa-trash")
                span Delete
    </template>