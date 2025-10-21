import { defineStore } from "pinia";

const DEFAULT_USER_SETTINGS = {
  collapseNavigation: false,
};

export const useCoreStore = defineStore("coreStore", {
  state: () => {
    return {
      mainConfig: {},
      availablePlugins: [],
      planners: [],
      obfuscators: [],
      userSettings: {},
      contacts: [],
      availableContacts: [],
      hideDisabledPlugins: false,
    };
  },
  getters: {
    enabledPlugins: (state) =>
      state.mainConfig ? state.mainConfig.plugins : [],
  },
  actions: {
    async getMainConfig($api) {
      try {
        const response = await $api.get("/api/v2/config/main");
        this.mainConfig = response.data;
      } catch (error) {
        console.error("Error fetching main config", error);
      }
    },
    async getAvailablePlugins($api) {
      try {
        const response = await $api.get("/api/v2/plugins");
        this.availablePlugins = response.data;
      } catch (error) {
        throw error;
      }
    },
    async updateMainConfigSetting($api, key, value) {
      try {
        await $api.patch("/api/v2/config/main", {
          prop: key,
          value: value,
        });
        this.mainConfig[key] = value;
      } catch (error) {
        console.error("Error updating main config", error);
      }
    },
    async getPlanners($api) {
      try {
        const response = await $api.get("/api/v2/planners");
        this.planners = response.data;
      } catch (error) {
        console.error("Error getting planners", error);
      }
    },
    async getObfuscators($api) {
      try {
        const response = await $api.get("/api/v2/obfuscators");
        this.obfuscators = response.data;
      } catch (error) {
        console.error("Error getting obfuscators", error);
      }
    },
    async getContacts($api) {
      try {
        const response = await $api.get("/api/v2/contactlist");
        this.contacts = response.data;
      } catch (error) {
        console.error("Error getting list of contacts", error);
      }
    },
    async getAvailableContacts($api, contact) {
      try {
        const response = await $api.get("/api/v2/contacts");
        this.availableContacts = response.data;
      } catch (error) {
        console.error("Error getting contacts", error);
      }
    },
    async downloadContactReport($api, contact) {
      try {
        const response = await $api.get(`/api/v2/contacts/${contact}`);
        this.downloadJson(`${contact}_contact_report`, response.data);
      } catch (error) {
        console.error("Error downloading contact report", error);
      }
    },
    getUserSettings() {
      const settings = localStorage.getItem("calderaUserSettings");
      this.userSettings = JSON.parse(settings) || DEFAULT_USER_SETTINGS;
    },
    modifyUserSettings(setting, value) {
      if (!Object.keys(DEFAULT_USER_SETTINGS).includes(setting)) return;
      this.userSettings[setting] = value;
      localStorage.setItem(
        "calderaUserSettings",
        JSON.stringify(this.userSettings)
      );
    },
    downloadJson(filename, data) {
      let dataStr =
        "data:text/json;charset=utf-8," +
        encodeURIComponent(JSON.stringify(data, null, 2));
      let downloadAnchorNode = document.createElement("a");
      downloadAnchorNode.setAttribute("href", dataStr);
      downloadAnchorNode.setAttribute("download", filename + ".json");
      document.body.appendChild(downloadAnchorNode);
      downloadAnchorNode.click();
      downloadAnchorNode.remove();
    },
  },
});
