import { defineStore } from "pinia";

export const useExfilledStore = defineStore("exfilledStore", {
  state: () => ({
    exfilDir: "",
    files: {},
    numFiles: 0,
  }),
  actions: {
    setExfilDir(dir) {
      this.exfilDir = dir;
    },
    async loadFiles($api, operationID) {
      try {
        const response = await $api.post("/api/rest", {
          index: "exfil_files",
          operation_id: operationID,
        });
        this.files = response.data;
        this.numFiles = 0;
        if (this.selectedOperationId) {
          let validHosts = [];
          this.operations
            .filter((operation) => operation.id === this.selectedOperationId)
            .forEach((operation) => {
              operation.host_group.forEach((host) => {
                validHosts.push(`${host.host}-${host.paw}`);
              });
            });

          Object.keys(this.files).forEach((host) => {
            if (!validHosts.includes(host)) {
              this.files[host] = {};
            }
          });
        }
        Object.keys(this.files).forEach((agent) => {
          Object.keys(this.files[agent]).forEach((filename) => this.numFiles++);
        });
      } catch (error) {
        console.error("Error fetching exfilled files", error);
      }
    },
  },
});
