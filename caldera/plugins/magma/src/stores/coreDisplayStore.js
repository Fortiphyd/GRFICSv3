import { defineStore } from "pinia";

export const useCoreDisplayStore = defineStore("coreDisplayStore", {
  state: () => {
    return {
      openTabs: [],
      activeTab: "",
      modals: {
        agents: {
          showDeploy: false,
          showConfig: false,
          showDetails: false,
        },
        payloads: {
          showUpload: false,
        },
        adversaries: {
          showFactBreakdown: false,
          showImport: false,
          showDetails: false,
          showDeleteConfirm: false,
        },
        core: {
          showPluginPopup: false,
          selectedPlugin: "",
        },
        operations: {
          showCreate: false,
          showDelete: false,
          showDetails: false,
          showAgentDetails: false,
          showDownload: false,
          showAddManualCommand: false,
          showFilters: false,
          showOutput: false,
        },
        schedules: {
          showCreate: false,
          showDelete: false,
        },
      },
    };
  },

  actions: {
    addTab(name, path) {
      const newTab = {
        name: name,
        path: path,
      };
      if (!name || name === "login") {
        return;
      }
      if (
        this.openTabs.map((tab) => tab.name).indexOf(name) === -1 &&
        name !== "home"
      ) {
        this.openTabs.push(newTab);
      }
      this.openTabs.push("");
      this.openTabs.pop();
      this.activeTab = name;
    },
    removeTab(index) {
      this.openTabs.splice(index, 1);
      if (this.openTabs.length === 0) {
        this.activeTab = "";
      }
    },
    removeAllTabs() {
      this.openTabs = [];
      this.activeTab = "";
    },
  },
});
