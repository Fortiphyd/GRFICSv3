<script setup>
import { defineAsyncComponent, shallowRef, watch, ref, inject, onBeforeUnmount } from "vue";
import PluginErrorView from "./PluginErrorView.vue";
import PluginLoadingView from "./PluginLoadingView.vue";

const isProduction = import.meta.env.PROD;

const $api = inject("$api");
const props = defineProps(["pluginName"]);

const pluginComponent = shallowRef();
const legacyIframe = ref(null);
const isUsingLegacy = ref(true);
const plugins = isProduction
  ? import.meta.glob("../plugins/**/views/*.vue")
  : import.meta.glob("../../../**/gui/views/*.vue");
const legacyScriptPaths = [
  "/gui/js/shared.js",
  "/gui/js/core.js",
  "/gui/js/lib/bulma-toast.min.js",
  "/gui/js/lib/confetti.browser.min.js",
];
const legacyStylePaths = [
  "/gui/css/shared.css",
  "/gui/css/core.css",
  "/gui/css/modal.css",
  "/gui/css/basic.css",
  "/gui/css/timeline.css",
  "/gui/css/multi-select.css",
  "/gui/css/lib/custom-bulma.css",
  "/gui/css/lib/bulma-tooltip.min.css",
  "/gui/css/lib/fa-all.min.css",
];
watch(() => props.pluginName, loadComp);

function isScriptLoaded(src) {
  return document.querySelector(`script[src="${src}"]`) !== null;
}

async function loadComp() {
  if (document.getElementById("legacyContainer")) {
    document.getElementById("legacyContainer").innerHTML = "";
  }
  const requestedPluginLoader =
    plugins[
      isProduction
        ? `../plugins/${props.pluginName}/views/${props.pluginName}.vue`
        : `../../../${props.pluginName}/gui/views/${props.pluginName}.vue`
    ];

  if (!requestedPluginLoader) {
    try {
      const res = await $api.get(
        `http://localhost:8888/plugin/${props.pluginName}/gui`
      );
      const html = res.data;
      const newElement = document.createElement("div");
      newElement.innerHTML = html;
      //Replace scripts
      const scripts = Array.from(newElement.querySelectorAll("script"));
      if (scripts) {
        scripts.forEach((oldScript) => {
          if (oldScript.src && isScriptLoaded(oldScript.src)) {
            console.log("script already loaded");
            return; // Skip this script as it's already loaded
          }
          const newScript = document.createElement("script");
          Array.from(oldScript.attributes).forEach((attr) =>
            newScript.setAttribute(attr.name, attr.value)
          );
          newScript.appendChild(document.createTextNode(oldScript.innerHTML));
          oldScript.parentNode.replaceChild(newScript, oldScript);
        });
      }
      legacyScriptPaths.forEach((path) => {
        // Inject a <script> tag
        if (!isScriptLoaded(path)){
          let script = document.createElement("script");
          script.src = path;
          newElement.appendChild(script);
        }
      });
      legacyStylePaths.forEach((path) => {
        let link = document.createElement("link");
        link.href = path;
        link.rel = "stylesheet";
        newElement.appendChild(link);
      });
      if (!isScriptLoaded("/gui/js/lib/alpine.min.js")){
        console.log("in alpine");
        let alpineScript = document.createElement("script");
        alpineScript.src = "/gui/js/lib/alpine.min.js";
        alpineScript.defer = true;
        newElement.appendChild(alpineScript);
      }
      document.getElementById("legacyContainer").appendChild(newElement);
      isUsingLegacy.value = true;
      return;
    } catch (error) {
      pluginComponent.value = PluginErrorView;
      console.error(error);
      return;
    }
  }
  isUsingLegacy.value = false;

  pluginComponent.value = defineAsyncComponent({
    // Source: https://vuejs.org/guide/components/async.html
    loader: requestedPluginLoader,
    loadingComponent: PluginLoadingView,
    errorComponent: PluginErrorView,
    // The error component will be displayed if a timeout is provided and exceeded. Default: Infinity.
    timeout: 10000,
  });
}

loadComp();
</script>

<template lang="pug">
component(v-if="pluginComponent && !isUsingLegacy" :is="pluginComponent")
.warning(v-if="isUsingLegacy")
  h2 Warning: You're currently using the legacy plugin interface for {{props.pluginName}}. While it might function, we cannot guarantee its full compatibility or stability. For the best experience, we recommend updating to the latest UI version.
.container(id="legacyContainer")
</template>

<style>
iframe {
  width: 100%;
  height: 100%;
  border: none;
}
.warning {
  background-color: rgb(251, 162, 169);
  border: 1px solid red;
  padding: 10px;
  color: black;
  margin-bottom: 30px;
  border-radius: 5px;
}
</style>
