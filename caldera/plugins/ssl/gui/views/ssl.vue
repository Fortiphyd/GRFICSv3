<script setup>
import { inject, onMounted, ref } from "vue";

const $api = inject("$api");
const isHttps = ref(false);
onMounted(() => {
  isHttps.value = window.location.protocol === "https:";
});
</script>

<template lang="pug">
.content    
  h2 SSL
  p Add HTTPS to Caldera
hr
.content
  p(:class="{ 'has-text-success': isHttps, 'has-text-danger': !isHttps }") You are 
    span(v-if="!isHttps") not 
    | using Caldera over HTTPS
  p This plugin creates an HTTPS interface for Caldera, allowing user and gents to securely communicate with the server.
  a.button.is-primary.mt-4(href="/docs/Plugin-library.html#ssl" target="_blank")
    Setup Instructions
    span.icon
      font-awesome-icon(icon="fas fa-angle-right")
</template>
