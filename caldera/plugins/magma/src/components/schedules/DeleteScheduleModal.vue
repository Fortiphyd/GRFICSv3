<script setup>
import { inject } from "vue";
import { storeToRefs } from "pinia";

import { useCoreDisplayStore } from "@/stores/coreDisplayStore";
import { useScheduleStore } from "@/stores/schedulesStore";

const $api = inject("$api");

const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);
const scheduleStore = useScheduleStore();

async function deleteSchedule() {
  await scheduleStore.deleteSchedule($api, scheduleStore.selectedScheduleID);
  modals.value.schedules.showDelete = false;
  modals.value.schedules.showCreate = false;
}
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.schedules.showDelete }")
    .modal-background(@click="modals.schedules.showDelete = false")
    .modal-card
        header.modal-card-head
            p.modal-card-title Delete Schedule?
        .modal-card-body(v-if="scheduleStore.currentSchedule")
            p Are you sure you want to delete the schedule "{{ scheduleStore.currentSchedule.id }}"? This cannot be undone.
        footer.modal-card-foot.has-text-right
            button.button(@click="modals.schedules.showDelete = false") Cancel
            button.button.is-danger(@click="deleteSchedule().then(() => {})")
                span.icon
                    font-awesome-icon(icon="fa-trash")
                span Delete

</template>

<style scoped>
.modal-card-foot {
  display: block;
}
</style>
