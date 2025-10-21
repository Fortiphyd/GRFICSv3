<script setup>
import { watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useCoreDisplayStore } from "../../stores/coreDisplayStore.js";

const coreDisplayStore = useCoreDisplayStore();

let { openTabs, activeTab } = storeToRefs(coreDisplayStore);

const route = useRoute();
const router = useRouter();

watch(route, (route, prevRoute) => {
    if (route.name === "NotFound") return;
    if (route.params.pluginName) {
        activeTab = route.params.pluginName;
        coreDisplayStore.addTab(
            route.params.pluginName,
            `/plugins/${route.params.pluginName}`
        );
    } else {
        activeTab = route.name;
        coreDisplayStore.addTab(route.name, `${route.path}`);
    }
});

watch(activeTab, (tab, prevTab) => {
    if (!tab) router.push("/");
});

function closeTab(index, isActive) {
    coreDisplayStore.removeTab(index)
    if (openTabs.value.length && isActive) {
        let nextTab = (index - 1 < openTabs.value.length && index > 0) ? openTabs.value[index - 1] : openTabs.value[0];
        router.push(nextTab.path);
    }
}
</script>

<template lang="pug">
#tabs.is-flex.is-flex-direction-row
    .tags.has-addons.mr-2.mb-0(v-for="(tab, index) in openTabs" @click="router.push(tab.path)")
        p.tag.is-large(:class="{ 'is-primary': tab.name === activeTab }") {{ tab.name }}
        p.tag.is-large.is-delete(@click.stop="closeTab(index, tab.name === activeTab)" :class="{ 'is-primary': tab.name === activeTab }")
</template>

<style scoped>
#tabs {
    position: fixed;
    width: 100%;
    height: 55px;
    padding: 10px;
    background-color: #111;
    z-index: 10;
}

.tag {
    background-color: #2c2c2c;
    padding: 15px;
    cursor: pointer;
    user-select: none;
}

.tag.is-delete:hover {
    background-color: #3f3f3f;
}
.tag.is-delete.is-primary:hover {
    background-color: #7400d2;
}
</style>
