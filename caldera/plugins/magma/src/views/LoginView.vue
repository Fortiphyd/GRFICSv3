<script setup>
import { ref, inject } from "vue";
import { useAuthStore } from "../stores/authStore.js";
let username = ref("");
let password = ref("");
let loginError = ref("");
const $api = inject("$api");

async function handleLogin(e) {
    e.preventDefault();
    const authStore = useAuthStore();
    try {
        await authStore.login(username, password, $api);
    } catch (error) {
        loginError.value = error;
    }
}
</script>

<template lang="pug">
#login.container.content.fullwh.is-flex.is-flex-direction-column.is-align-items-center.is-justify-content-center()
    img(src="/src/assets/img/caldera-logo.png" alt="Caldera Logo")
    .p-6
        form
            .field
                label.label Username
                .control.has-icons-left
                    input.input(v-focus v-model="username" type="text" placeholder="username")
                    span.icon.is-small.is-left
                        font-awesome-icon(icon="fas fa-user")
            .field
                label.label Password
                .control.has-icons-left
                    input.input(v-model="password" type="password" placeholder="password")
                    span.icon.is-small.is-left
                        font-awesome-icon(icon="fas fa-lock")
            button.button.fancy-button.is-fullwidth(type="submit" @click="handleLogin") Log In
        .has-text-danger
            p {{ loginError }}
</template>

<style scoped>
#login {
    height: 100vh;
}

#login img {
    width: 250px;
    margin: 16px;
}

.fancy-button:hover {
    background-image: linear-gradient(to right, #8b0000, #191970) !important;
    border-width: 2px;
}
</style>
