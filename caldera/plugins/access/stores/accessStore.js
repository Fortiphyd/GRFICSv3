import { defineStore } from "pinia";

export const useAccessStore = defineStore("accessStore", {
    state: () => {
        return {};
    },
    getters: {
        enabledPlugins: (state) => (state.mainConfig ? state.mainConfig.plugins : [])  
    },
    actions: {
        async restRequest(requestType, data, callback = (r) => {
            console.log('Fetch Success', r);
        }, endpoint = '/api/rest') {
            const requestData = requestType === 'GET' ?
                {method: requestType, headers: {'Content-Type': 'application/json'}} :
                {method: requestType, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)}

            fetch(endpoint, requestData)
                .then((response) => {
                    if (!response.ok) {
                        throw (response.statusText);
                    }
                    return response.text();
                })
                .then((text) => {
                    try {
                        callback(JSON.parse(text));
                    } catch {
                        callback(text);
                    }
                })
                .catch((error) => console.error(error));
        },

        async apiV2(requestType, endpoint, body = null, jsonRequest = true) {
            let requestBody = { method: requestType };
            if (jsonRequest) {
                requestBody.headers = { 'Content-Type': 'application/json' };
                if (body) {
                    requestBody.body = JSON.stringify(body);
                }
            } else {
                if (body) {
                    requestBody.body = body;
                }
            }

            return new Promise((resolve, reject) => {
                fetch(endpoint, requestBody)
                    .then((response) => {
                        if (!response.ok) {
                            reject(response.statusText);
                        }
                        return response.text();
                    })
                    .then((text) => {
                        try {
                            resolve(JSON.parse(text));
                        } catch {
                            resolve(text);
                        }
                    });
            });
        }
    },
});
