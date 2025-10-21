<script setup>
import { onMounted } from "vue";
import { useRoute } from "vue-router";

import { useCoreStore } from "@/stores/coreStore";
import Navigation from "@/components/core/Navigation.vue";
import PageTabs from "@/components/core/PageTabs.vue";

const route = useRoute();
const coreStore = useCoreStore();

onMounted(() => {
    coreStore.getUserSettings();
})
</script>

<template lang="pug">
//- Login page
.is-fullwidth(v-if="route.name === 'login'")
    router-view

//- All other pages
.is-flex.is-flex-direction-row(v-else style="min-height: 100vh;")
    Suspense
        Navigation

    main
        PageTabs

        .p-4#router
            router-view
</template>

<style scoped>
#router {
    height: calc(100% - 55px);
    margin-top: 55px;
}
</style>

<style>
/* GLOBAL STYLES */
@import "/src/assets/css/custom-bulma.css";

main {
    width: calc(100% - 220px);
}

*::-webkit-scrollbar {
  background-color: #0000;
  width: 8px;
  height: 8px;
}
*::-webkit-scrollbar-thumb {
  background: #3f3f3f;
  border-radius: 10px;
  height: 50px;
}
*::-webkit-scrollbar-corner {
  background-color: #0000;
  color: white;
}

.code {
    font-family: monospace;
}

.dropdown.searchable .dropdown-content {
    max-height: 300px;
    overflow-y: scroll;
}
.dropdown.searchable .dropdown-trigger {
    width: 100%;
}
.dropdown.searchable .dropdown-menu {
    width: 100%;
}

.is-fullwidth {
    width: 100%;
}

.pointer {
    cursor: pointer;
}

.vr {
    width: 1px;
    height: 30px;
    margin: 0 20px 0 10px;
    background-color: grey;
}
</style>
