import { defineStore } from "pinia";

export const useAbilityStore = defineStore("abilityStore", {
    state: () => {
        return {
            abilities: [],
            payloads: [],
        };
    },
    getters: {
        platforms: (state) => {
            let platforms = {};
            state.abilities.forEach((ability) => {
                ability.executors.forEach((executor) => {
                    if (!platforms[executor.platform]) {
                        platforms[executor.platform] = [executor.name];
                    } else if (!platforms[executor.platform].includes(executor.name)) {
                        platforms[executor.platform].push(executor.name);
                    }
                });
            });
            return platforms;
        },
        tactics: (state) => (
            [...new Set(state.abilities.map((ability) => ability.tactic))].sort()
        ),
        techniques: (state) => (
            [...new Set(state.abilities.map((ability) => `${ability.technique_id} | ${ability.technique_name}`))].sort()
        ),
        techniqueIds: (state) => (
            [...new Set(state.abilities.map((ability) => ability.technique_id))].sort()
        ),
        techniqueNames: (state) => (
            [...new Set(state.abilities.map((ability) => ability.technique_name))].sort()
        ),
        plugins: (state) => (
            [...new Set(state.abilities.map((ability) => ability.plugin))].sort()
        )
    },
    actions: {
        async getAbilities($api) {
            try {
                const response = await $api.get("/api/v2/abilities");
                this.abilities = response.data;
            } catch(error) {
                console.error("Error fetching abilities", error);
            }
        },
        async saveAbility($api, ability, create) {
            try {
                if (create) {
                    const response = await $api.post(`/api/v2/abilities`, ability);
                    this.abilities.push(response.data);
                } else {
                    const response = await $api.patch(`/api/v2/abilities/${ability.ability_id}`, ability);
                    const index = this.abilities.findIndex((a) => a.ability_id === response.data.ability_id);
                    this.abilities[index] = response.data;
                }
            } catch(error) {
                console.error("Error saving ability", error);
            }
        },
        async deleteAbility($api, abilityId) {
            try {
                await $api.delete(`/api/v2/abilities/${abilityId}`);
                this.abilities.splice(this.abilities.findIndex((ability) => ability.ability_id === abilityId), 1);
            } catch(error) {
                console.error("Error fetching abilities", error);
            }
        },
        async getPayloads($api, sort=false, excludePlugins=false, addPath=false) {
            try {
                const response = await $api.get("/api/v2/payloads", {params: {sort: sort, exclude_plugins: excludePlugins, add_path: addPath}});
                this.payloads = response.data;
            } catch(error) {
                console.error("Error fetching payloads", error);
            }
        },
        async savePayload($api, file, sort=false, addPath=false) {
            try {
                let formData = new FormData();
                formData.append("file", file);
                const response = await $api.post(`/api/v2/payloads`, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });
                let name = response.data["payloads"][0]
                if (addPath) {
                    name = "data/payloads/" + name;
                }
                let index = sort ?
                    this.payloads.findIndex((payload) => name.localeCompare(payload) < 0) : -1;
                if (index === -1) {
                    this.payloads.push(name);
                } else {
                    this.payloads.splice(index, 0, name);
                }
            } catch(error) {
                console.error("Error uploading payload.", error);
            }
        },
        async deletePayload($api, payloadName, addPath=false) {
            try {
                await $api.delete(`/api/v2/payloads/${payloadName}`);
                this.payloads.splice(this.payloads.findIndex((payload) =>
                    (addPath ? payload.replace(/^data\/payloads\//, '') : payload) === payloadName), 1);
            } catch(error) {
                console.error("Error deleting payload.", error);
            }
        },
    },
});
