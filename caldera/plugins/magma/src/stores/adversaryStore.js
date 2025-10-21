import { defineStore } from "pinia";
import { useAbilityStore as abilityStore } from "./abilityStore";

export const useAdversaryStore = defineStore("adversaryStore", {
  state: () => {
    return {
      adversaries: [],
      selectedAdversary: {},
      selectedAdversaryAbilities: [],
      objectives: [],
      selectedObjective: "",
    };
  },
  actions: {
    async getAdversaries($api) {
      try {
        const response = await $api.get("/api/v2/adversaries");
        this.adversaries = response.data;
      } catch (error) {
        console.error("Error fetching adversaries", error);
      }
    },
    async getObjectives($api) {
      try {
        const response = await $api.get("/api/v2/objectives");
        this.objectives = response.data;
      } catch (error) {
        console.error("Error fetching objectives", error);
      }
    },
    async createObjective($api) {
      try {
        const response = await $api.post("/api/v2/objectives", {
          name: "New objective",
          description: "Enter a description",
        });
        this.objectives.push(response.data);
        this.selectedObjective = this.objectives[this.objectives.length - 1];
      } catch (error) {
        console.error("Error creating objective", error);
      }
    },
    async saveObjective($api) {
      try {
        await $api.put(
          `/api/v2/objectives/${this.selectedObjective.id}`,
          this.selectedObjective
        );
      } catch (error) {
        console.error("Error saving objective", error);
      }
    },
    async createAdversary($api, adversary = null) {
      try {
        const response = await $api.post(
          "/api/v2/adversaries",
          adversary || {
            name: "New adversary",
            description: "---",
            atomic_ordering: [],
          }
        );
        this.adversaries.push(response.data);
        this.adversaries.sort((a, b) => a.name > b.name);
        this.selectedAdversary = response.data;
        this.updateSelectedAdversaryAbilities();
      } catch (error) {
        console.error("Error creating an adversary", error);
      }
    },
    async saveSelectedAdversary($api) {
      const reqBody = {
        name: this.selectedAdversary.name,
        description: this.selectedAdversary.description,
        objective: this.selectedAdversary.objective,
        atomic_ordering: this.selectedAdversaryAbilities.map(
          (ability) => ability.ability_id
        ),
      };

      try {
        const response = await $api.patch(
          `/api/v2/adversaries/${this.selectedAdversary.adversary_id}`,
          reqBody
        );
        const index = this.adversaries.findIndex(
          (adversary) =>
            adversary.adversary_id === this.selectedAdversary.adversary_id
        );
        this.adversaries[index] = this.selectedAdversary;
        return response.data;
      } catch (error) {
        console.error("Error saving adversary", error);
      }
    },
    async deleteAdversary($api) {
      try {
        const response = await $api.delete(
          `/api/v2/adversaries/${this.selectedAdversary.adversary_id}`
        );
        const index = this.adversaries.findIndex(
          (adversary) =>
            adversary.adversary_id === this.selectedAdversary.adversary_id
        );
        this.selectedAdversary = {};
        this.selectedAdversaryAbilities = [];
        this.adversaries.splice(index, 1);
      } catch (error) {
        console.error("Error deleting adversary", error);
      }
    },
    updateSelectedAdversaryAbilities() {
      if (!this.selectedAdversary.atomic_ordering) {
        this.selectedAdversaryAbilities = [];
      } else {
        this.selectedAdversaryAbilities =
          this.selectedAdversary.atomic_ordering.map((ability_id) => {
            return {
              ...abilityStore().abilities.find(
                (ability) => ability.ability_id === ability_id
              ),
            };
          });
      }
    },
  },
});
