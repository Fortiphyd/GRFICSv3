<script setup>
import { ref, inject, onMounted } from "vue";
const $api = inject("$api");

const envs = ref();

onMounted(async () => {
  try {
    const res = await $api.get("/plugin/builder/environment");
    envs.value = res.data;
  } catch (error) {
    console.error(error);
  }
});
</script>

<template lang="pug">
.content    
  h2 Builder
  p Dynamically compile ability code via docker containers.

.content
<!-- a table with a list of envs -->
  table.table.is-fullwidth
    thead
      tr
        th Name
        th Docker image
        th File extension
        th Working directory
        th Build command
    tbody
      tr(v-for="(env, name) in envs" :key="name")
        td {{ name }}
        td {{ env.docker }}
        td {{ env.extension }}
        td {{ env.workdir }}
        td {{ env.build_command }}
.is-flex.is-align-items-center.is-justify-content-center
    a.button.is-primary(href="/docs/Dynamically-Compiled-Payloads.html" target="_blank")
        span Read more about using Builder to create dynamically-compiled payloads here:
        span.icon
            font-awesome-icon(icon="fas fa-angle-right")

</template>
