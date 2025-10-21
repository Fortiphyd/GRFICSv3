import { defineStore } from "pinia";
import router from "../router";

export const useAuthStore = defineStore({
  id: "auth",
  state: () => ({
    isUserAuthenticated: false,
    returnUrl: null,
    group: "",
    version: "",
  }),
  actions: {
    async login(username, password, $api) {
      try {
        const fd = new FormData();
        fd.append("username", username.value);
        fd.append("password", password.value);
        await $api.post("/enter", fd);

        this.isUserAuthenticated = true;
        await this.getGroup($api);
        router.push({ name: this.returnUrl || "home" });
      } catch (error) {
        if (!error.response) throw "The server encountered an error";
        if (error.response.status == 401) {
          throw "Incorrect username or password";
        }
        console.log(error);
        throw "The server encountered an error";
      }
    },
    async getAuthStatus($api) {
      try {
        await $api.head("/api/v2/config/main");
        return true;
      } catch (error) {
        return false;
      }
    },
    async getGroup($api) {
      try {
        const response = await $api.get("/api/v2/health");
        this.group = response.data.access;
        this.version = response.data.version;
        return response.data.access;
      } catch (error) {
        console.log(error);
      }
    },
    async logout($api) {
      try {
        await $api.post("/logout");
        this.isUserAuthenticated = false;
        router.push("/login");
      } catch (error) {
        console.log(error);
      }
    },
  },
});
