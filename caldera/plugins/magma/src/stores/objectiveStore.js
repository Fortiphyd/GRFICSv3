import { defineStore } from "pinia";

export const useObjectiveStore = defineStore("objectiveStore", {
    state: () => ({
        objectives: []
    }),
    actions: {
        async getObjectives($api) {
            try {
                const response = await $api.get("/api/v2/objectives")
                this.objectives = response.data
            } catch(error) {
                console.error("Error fetching objectives", error)
            }
        }
    },
});
