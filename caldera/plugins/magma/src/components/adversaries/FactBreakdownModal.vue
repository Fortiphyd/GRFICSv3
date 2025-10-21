<script setup>
import { useCoreDisplayStore } from "../../stores/coreDisplayStore";
import { storeToRefs } from "pinia";

const coreDisplayStore = useCoreDisplayStore();
const { modals } = storeToRefs(coreDisplayStore);

const props = defineProps(['breakdown']);
</script>

<template lang="pug">
.modal(:class="{ 'is-active': modals.adversaries.showFactBreakdown }")
    .modal-background(@click="modals.adversaries.showFactBreakdown = false")
    .modal-card 
        header.modal-card-head 
            p.modal-card-title Fact Breakdown
        .modal-card-body 
            p.help.tags.mb-1.has-text-centered
                span.tag.is-success Required and Collected
                span.tag.is-warning Required and not Collected
                span.tag.is-black Collected but not Required
            hr.mt-2
            .tags(v-if="breakdown.length")
                span.tag(v-for="fact in breakdown" :class="{ 'is-warning': fact.type === 'unmet', 'is-success': fact.type === 'met' }")
                    span.icon
                        font-awesome-icon(v-if="fact.type === 'unmet'" icon="fas fa-exclamation-triangle")
                        font-awesome-icon(v-if="fact.type === 'met'" icon="fas fa-check")
                        font-awesome-icon(v-if="fact.type === 'extra'" icon="fas fa-minus")
                    span {{ fact.fact }}
            p(v-else) No facts to show
        footer.modal-card-foot.is-flex.is-justify-content-flex-end 
            button.button(@click="modals.adversaries.showFactBreakdown = false") Close
</template>
