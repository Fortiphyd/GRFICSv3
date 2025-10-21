import { defineStore } from "pinia";
import { b64DecodeUnicode } from "../utils/utils";

export const useOperationStore = defineStore("operationStore", {
  state: () => {
    return {
      operations: {},
      selectedOperationID: "",
      selectedLink: {},
      facts: {},
    };
  },
  getters: {
    currentOperation(state) {
      return state.operations[state.selectedOperationID];
    },
  },
  actions: {
    async getOperations($api) {
      try {
        const response = await $api.get("/api/v2/operations");
        // TODO: Sort operations
        for (const operation of response.data) {
          this.operations[operation.id] = operation;
        }
      } catch (error) {
        console.error("Error fetching operations", error);
      }
    },
    async getOperation($api, operationID) {
        try {
          const response = await $api.get(`/api/v2/operations/${operationID}`);
          let operation = response.data;
          this.operations[operation.id] = operation;
        } catch (error) {
          console.error("Error fetching operations", error);
        }
      },
    async createOperation($api, operation) {
      try {
        const response = await $api.post("/api/v2/operations", operation);
        this.operations[response.data.id] = response.data;
        this.selectedOperationID = response.data.id;
      } catch (error) {
        console.error("Error creating operation", error);
      }
    },
    async deleteOperation($api, operationID) {
      try {
        await $api.delete(`/api/v2/operations/${operationID}`);
        delete this.operations[operationID];
        this.selectedOperationID = "";
        this.getOperations($api);
      } catch (error) {
        console.error("Error deleting operation", error);
      }
    },
    async updateOperationChain($api) {
      try {
        const response = await $api.get(
          `/api/v2/operations/${this.selectedOperationID}`
        );
        if (this.selectedOperationID != response.data.id) {
          return;
        }
        operations[this.selectedOperationID] = response.data;
      } catch (error) {
        console.error("Error updating operation chain", error);
      }
    },
    async updateOperation($api, field, updateValue) {
      const newOperation = { ...this.operations[this.selectedOperationID] };
      newOperation[field] = updateValue;
      try {
        await $api.patch(
          `/api/v2/operations/${this.selectedOperationID}`,
          newOperation
        );
        this.getOperations($api);
      } catch (error) {
        console.error("Error updating operation", error);
      }
    },
    async rerunOperation($api) {
      let { id, start, state, chain, host_group, ...newOp } =
        this.operations[this.selectedOperationID];
      let dateMatches = newOp.name.match(
        /[(]\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{1,3}Z[)]$/g
      );
      let stringToReplace =
        dateMatches && dateMatches.length
          ? dateMatches[dateMatches.length - 1]
          : "";
      let date = `(${new Date().toISOString()})`;
      newOp.name = stringToReplace
        ? newOp.name.replace(stringToReplace, date)
        : `${newOp.name} ${date}`;
      try {
        const response = await $api.post("/api/v2/operations", newOp);
        this.selectedOperationID = response.data.id;
        this.getOperations($api);
      } catch (error) {
        console.error("Error rerunning operation", error);
      }
    },
    isOperationRunning() {
      if (
        this.selectedOperationID === "" ||
        !this.operations[this.selectedOperationID]
      )
        return false;
      return !(
        this.operations[this.selectedOperationID].state === "finished" ||
        this.operations[this.selectedOperationID].state === "cleanup" ||
        this.operations[this.selectedOperationID].state === "out_of_time"
      );
    },
    async updateLink($api, status, command = null, currentLink) {
      const updatedLink = {
        ...currentLink,
        command: currentLink.command,
      };
      if (command) updatedLink.command = command;
      updatedLink.status = status;
      try {
        const response = await $api.patch(
          `/api/v2/operations/${this.selectedOperationID}/links/${currentLink.id}`,
          updatedLink
        );
        await this.getOperations($api);
        return response.data;
      } catch (error) {
        console.error("Error updating link state", error);
      }
    },
    async addManualCommand($api, manualCommand) {
      try {
        const response = await $api.post(
          `/api/v2/operations/${this.selectedOperationID}/potential-links`,
          manualCommand
        );
        await this.getOperations($api);
        return response.data;
      } catch (error) {
        console.error("Error adding manual command", error);
      }
    },
    async addPotentialLinks($api, potentialLink) {
      try {
        for (let link of potentialLink) {
          await $api.post(
            `/api/v2/operations/${this.selectedOperationID}/potential-links`,
            link
          );
        }
        await this.getOperations($api);
      } catch (error) {
        console.error("Error adding potential links", error);
      }
    },
    async rerunLink($api, link) {
      try {
        await $api.post(
          `/api/v2/operations/${this.selectedOperationID}/potential-links`,
          link
        );
        await this.getOperations($api);
      } catch (error) {
        console.error("Error rerunning link", error);
      }
    },
    async getFacts($api) {
      if (this.selectedOperationID === "") return;
      try {
        const response = await $api.get(
          `/api/v2/facts/${this.selectedOperationID}`
        );
        this.facts = response.data.found;
      } catch (error) {
        console.error("Error getting facts");
      }
    },
    async downloadOperationInfo($api, format, operationID, isAgentOutput) {
      switch (format) {
        case 0:
          format = "report";
          break;
        case 1:
          format = "event-logs";
          break;
        case 2:
          format = "csv";
          break;
        default:
          format = "report";
          break;
      }
      if (format !== "csv") {
        try {
          const response = await $api.post(
            `/api/v2/operations/${operationID}/${format}`,
            { enable_agent_output: isAgentOutput }
          );
          const data = JSON.stringify(response.data);
          const blob = new Blob([data], { type: "text/plain" });
          this.createDownloadReport(blob, "json", format);
        } catch (error) {
          console.error("Error downloading operation", error);
        }
      } else {
        let csv = [
          "Time Ran,Ability Name,Agent,Host,pid,Link Command,Plaintext Command",
        ];
        this.operations[this.selectedOperationID].chain.forEach((link) => {
          const rowItems = [];
          rowItems.push(link.decide);
          rowItems.push(link.ability.name);
          rowItems.push(link.paw);
          rowItems.push(link.host);
          rowItems.push(link.pid);
          rowItems.push(link.command);
          rowItems.push(link.plaintext_command);
          csv.push(rowItems.join(","));
        });
        const blob = new Blob([csv.join("\n")], { type: "text/csv" });
        this.createDownloadReport(blob, "csv", format);
      }
    },
    createDownloadReport(blob, fileName, format) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = `${
        this.operations[this.selectedOperationID].name
      }_${format}.${fileName}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    },
  },
});
