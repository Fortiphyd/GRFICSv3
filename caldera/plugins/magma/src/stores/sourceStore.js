import { defineStore } from "pinia";

export const useSourceStore = defineStore("sourceStore", {
    state: () => {
        return {
            sources: [],
            selectedSource: "",
        };
    },
    actions: {
        async getSources($api) {
            try {
                const response = await $api.get("/api/v2/sources");
                this.sources = response.data;
            } catch(error) {
                console.error("Error getting sources", error);
            }
        },
        async saveSource($api) {
            try {
                const response = await $api.put(`/api/v2/sources/${this.selectedSource.id}`, this.selectedSource);
                const updatedSource = response.data;
                const matchIndex = this.sources.find((source) => source.id === updatedSource.id);
                this.sources[matchIndex] = updatedSource;
            } catch(error) {
                console.error("Error saving sources", error);
            }
        },
        async createSource($api, duplicate) {
            let src = { name: "New Source" };
            if (duplicate) {
                src = {
                    ...JSON.parse(JSON.stringify(this.selectedSource)),
                    name: `${this.selectedSource.name} (copy)`,
                    id: ''
                }
            }
            
            try {
                const response = await $api.post("/api/v2/sources", src);
                const newSource = response.data;
                this.sources.push(newSource);
                return newSource;
            } catch(error) {
                console.error("Error creating sources", error);
            }
        },
        async deleteSource($api) {
            try {
                const response = await $api.delete(`/api/v2/sources/${this.selectedSource.id}`);
                this.selectedSource = {};
                await this.getSources($api);
            } catch(error) {
                console.error("Error removing sources", error);
            }
        }
    },
});
