import { defineStore } from "pinia";

export const useScheduleStore = defineStore("scheduleStore", {
  state: () => {
    return {
      schedules: {},
      selectedScheduleID: "",
    };
  },
  getters: {
    currentSchedule(state) {
      return state.schedules[state.selectedScheduleID];
    },
  },
  actions: {
    async getSchedules($api) {
      try {
        const response = await $api.get("/api/v2/schedules");
        // TODO: Sort schedules
        for (const schedule of response.data) {
          this.schedules[schedule.id] = schedule;
        }
      } catch (error) {
        console.error("Error fetching schedules", error);
      }
    },
    async createSchedule($api, schedule) {
      try {
        const response = await $api.post("/api/v2/schedules", schedule);
        this.schedules[response.data.id] = response.data;
        this.selectedScheduleID = response.data.id;
      } catch (error) {
        console.error("Error creating schedule", error);
        throw error;
      }
    },
    async deleteSchedule($api, scheduleID) {
      try {
        await $api.delete(`/api/v2/schedules/${scheduleID}`);
        delete this.schedules[scheduleID];
        this.selectedScheduleID = "";
        this.getSchedules($api);
      } catch (error) {
        console.error("Error deleting schedule", error);
      }
    },
    async updateSchedule($api, newSchedule) {
      try {
        await $api.put(`/api/v2/schedules/${this.selectedScheduleID}`, newSchedule);
        this.getSchedules($api);
      } catch (error) {
        console.error("Error updating schedule", error);
      }
    },
  },
});
