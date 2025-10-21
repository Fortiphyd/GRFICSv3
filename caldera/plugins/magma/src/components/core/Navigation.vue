<script setup>
import { inject } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { useCoreStore } from "@/stores/coreStore";
import { useCoreDisplayStore } from "@/stores/coreDisplayStore.js";
import { useAuthStore } from "@/stores/authStore.js";
import PluginModal from "./PluginModal.vue";

const authStore = useAuthStore();
const coreDisplayStore = useCoreDisplayStore();
const coreStore = useCoreStore();
const { modals } = storeToRefs(coreDisplayStore);
const { enabledPlugins, availablePlugins, userSettings, hideDisabledPlugins } =
  storeToRefs(coreStore);
const { group, version } = storeToRefs(authStore);

const router = useRouter();

const $api = inject("$api");

try {
  await coreStore.getAvailablePlugins($api);
  await coreStore.getMainConfig($api);
  await authStore.getGroup($api);
} catch (error) {
  console.log(error);
}

function handleLogout() {
  coreDisplayStore.removeAllTabs();
  authStore.logout($api);
}

function promptToEnablePlugin(pluginName) {
  this.modals.core.selectedPlugin = pluginName;
  this.modals.core.showPluginPopup = true;
}
</script>

<template lang="pug">
#navigation(:class="{ 'collapsed': userSettings.collapseNavigation }")
    #expandCollapse
        a.icon(@click="coreStore.modifyUserSettings('collapseNavigation', !userSettings.collapseNavigation)")
            font-awesome-icon(:icon="userSettings.collapseNavigation ? 'fas fa-angles-right' : 'fas fa-angles-left'")
    #logo(v-if="!userSettings.collapseNavigation")
        img(src="/src/assets/img/caldera-logo.png" alt="Caldera Logo" @click="router.push('/')")
    #logo-collapsed(v-if="userSettings.collapseNavigation")
        img(src="/src/assets/img/caldera-logo-mtn.png" alt="Caldera Logo" @click="router.push('/')")
    #user-info(v-if="!userSettings.collapseNavigation")
      div.team-container
        span.icon(:class="{ 'is-red': group === 'RED', 'is-blue': group === 'BLUE'}")
          font-awesome-icon(icon="fas fa-user")
        span {{ version }}
    aside.menu(v-if="!userSettings.collapseNavigation")

        p.menu-label
            font-awesome-icon(icon="fas fa-flag").pr-2
            | Campaigns
        ul.menu-list
            li
                router-link.menu-item(to="/agents") agents
            li
                router-link.menu-item(to="/abilities") abilities
            li
                router-link.menu-item(to="/adversaries") adversaries
            li
                router-link.menu-item(to="/operations") operations
            li
              router-link.menu-item(to="/schedules") schedules
        p.menu-label
            font-awesome-icon(icon="fas fa-puzzle-piece").pr-2
            | Plugins
        ul.menu-list
            li(v-for="plugin in availablePlugins")
                a.menu-item(v-if="plugin.name === 'fieldmanual'" target="_blank" :href="'/docs/index.html'") {{ plugin.name }}
                router-link.menu-item(v-else-if="enabledPlugins.includes(plugin.name)" :to="`/plugins/${plugin.name}`") {{ plugin.name }}
                p.menu-item(v-else-if="plugin.name !== 'magma' && !hideDisabledPlugins" @click="promptToEnablePlugin(plugin.name)") {{ plugin.name }}
        p.menu-label
            font-awesome-icon(icon="fas fa-cog").pr-2
            | Configuration
        ul.menu-list
            li
                router-link.menu-item(to="/settings") settings
            li
                router-link.menu-item(to="/factsources") fact sources
            li
                router-link.menu-item(to="/objectives") objectives
            li
                router-link.menu-item(to="/contacts") contacts
            li
                router-link.menu-item(to="/exfilledfiles") exfilled files
            li
                router-link.menu-item(to="/payloads") payloads
        p.menu-label
            font-awesome-icon(icon="fas fa-book").pr-2
            | Resources
        ul.menu-list
            li
                router-link.menu-item(to="/planners") planners
            li
                router-link.menu-item(to="/obfuscators") obfuscators
            li
                a.menu-item(href="/api/docs" target="_blank")
                    | api docs
                    font-awesome-icon(icon="fas fa-external-link-alt").pl-1.is-size-7
        ul.menu-list.has-text-centered.mt-2
            li
                .menu-item.is-clickable(@click="handleLogout()")
                    span.icon
                        font-awesome-icon(icon="fas fa-sign-out-alt")
                    span Log out
            .control.mt-2
                    input.switch.is-rounded(type="checkbox" id="disabled-plugins" name="disabled-plugins" v-model="hideDisabledPlugins")
                    label.label(for="disabled-plugins") Hide disabled plugins

    .is-flex.is-flex-direction-column.is-align-items-center(v-else)
        .dropdown.is-hoverable.mb-2
            .dropdown-trigger
                button.button(aria-haspopup="true" aria-controls="dropdown-menu")
                    span.icon.is-small
                        font-awesome-icon(icon="fas fa-flag")
            .dropdown-menu(role="menu")
                .dropdown-content.ml-2
                    router-link.dropdown-item(to="/agents") agents
                    router-link.dropdown-item(to="/abilities") abilities
                    router-link.dropdown-item(to="/adversaries") adversaries
                    router-link.dropdown-item(to="/operations") operations
                    router-link.dropdown-item(to="/schedules") schedules
        .dropdown.is-hoverable.mb-2
            .dropdown-trigger
                button.button(aria-haspopup="true" aria-controls="dropdown-menu")
                    span.icon.is-small
                        font-awesome-icon(icon="fas fa-puzzle-piece")
            .dropdown-menu(role="menu")
                .dropdown-content.ml-2
                    div(v-for="plugin in availablePlugins")
                        a.dropdown-item(v-if="plugin.name === 'fieldmanual'" target="_blank" :href="'/docs/index.html'") {{ plugin.name }}
                        router-link.dropdown-item(v-else-if="enabledPlugins.includes(plugin.name)" :to="`/plugins/${plugin.name}`") {{ plugin.name }}
                        p.dropdown-item(v-else-if="plugin.name !== 'magma'" @click="promptToEnablePlugin(plugin.name)") {{ plugin.name }}
        .dropdown.is-hoverable.mb-2
            .dropdown-trigger
                button.button(aria-haspopup="true" aria-controls="dropdown-menu")
                    span.icon.is-small
                        font-awesome-icon(icon="fas fa-cog")
            .dropdown-menu(role="menu")
                .dropdown-content.ml-2
                    router-link.dropdown-item(to="/settings") settings
                    router-link.dropdown-item(to="/factsources") fact sources
                    router-link.dropdown-item(to="/objectives") objectives
                    router-link.dropdown-item(to="/contacts") contacts
                    router-link.dropdown-item(to="/exfilledfiles") exfilled files
                    router-link.dropdown-item(to="/payloads") payloads
        .dropdown.is-hoverable.mb-2
            .dropdown-trigger
                button.button(aria-haspopup="true" aria-controls="dropdown-menu")
                    span.icon.is-small
                        font-awesome-icon(icon="fas fa-book")
            .dropdown-menu(role="menu")
                .dropdown-content.ml-2
                    router-link.dropdown-item(to="/planners") planners
                    router-link.dropdown-item(to="/obfuscators") obfuscators
                    a.dropdown-item(href="/api/docs" target="_blank")
                        | api docs
                        font-awesome-icon(icon="fas fa-external-link-alt").pl-1.is-size-7

//- Modals
PluginModal
</template>

<style scoped>
#logo {
  width: 100%;
  text-align: center;
}
#logo > img {
  max-height: 150px;
  cursor: pointer;
  padding: 1.5em 3em;
}
#logo-collapsed > img {
  width: auto;
  height: auto;
  max-height: 100%;
  max-width: 100%;
  padding: 50px 10px 0 10px;
  margin-bottom: 15px;
}

#navigation {
  position: relative;
  background-color: #060606;
  width: 220px;
}
#navigation.collapsed {
  width: 105px;
}

#navigation {
  transition: width 0.5s ease;
}

#expandCollapse {
  position: absolute;
  top: 10px;
  right: 12px;
}

.menu {
  background-color: #060606;
  padding-bottom: 20px;
  user-select: none;
}

.menu-label {
  cursor: default;
  background: none !important;
  letter-spacing: 0.1em;
  color: white !important;
  padding: 8px;
  border-radius: 4px;
  margin: 0 10px;
}

.menu-item {
  padding: 0.25em 1.5em !important;
  border: 1px solid transparent;
  border-radius: 8px;
}

p.menu-item {
  color: grey;
}
p.menu-item:hover {
  cursor: pointer;
  border: 1px solid grey;
}

p.dropdown-item {
  color: grey;
}
p.dropdown-item:hover {
  cursor: pointer;
  border: 1px solid grey;
  border-radius: 8px;
}

.dropdown-menu {
  top: 0;
  left: 100%;
  padding-top: 0;
}

.team-container {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 0.5rem;
}

.team-container {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 0.5rem;
}

.is-red {
  color: #c31;
}

.is-blue {
  color: hsl(204, 86%, 53%);
}
</style>
