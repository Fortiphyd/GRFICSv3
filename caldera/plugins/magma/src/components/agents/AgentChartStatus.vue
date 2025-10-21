<script setup>
import { inject, ref, onMounted, onBeforeUnmount, watch } from "vue";
import * as echarts from "echarts";
import { storeToRefs } from "pinia";

import { useAgentStore } from "@/stores/agentStore";
import { getAgentStatus } from "@/utils/agentUtil.js";

const $api = inject("$api");

const agentStore = useAgentStore();
const { agents } = storeToRefs(agentStore);
const agentChartStatus = ref(null);
const chart = ref(null);

onMounted(() => {
  initChart();
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
});

watch(agents, () => {
  setChartOption();
});

async function initChart() {
  chart.value = echarts.init(agentChartStatus.value);
  chart.value.showLoading("default", {
    maskColor: "rgba(25, 25, 25, 0.8)",
    textColor: "white",
  });
  resizeChart();

  await agentStore.getAgents($api);
  setChartOption();
  chart.value.hideLoading();
}

function setChartOption() {
  chart.value.setOption({
    title: {
      text: `${agents.value.length} Agent${agents.value.length == 1 ? "" : "s"}`,
      textStyle: {
        color: "white",
      },
    },
    tooltip: {
      trigger: "item",
    },
    legend: {
      show: false,
    },
    series: [
      {
        name: "Agent Status",
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: "hsl(0deg, 0%, 14%)",
          borderWidth: 2,
        },
        label: {
          show: false,
          position: "center",
        },
        labelLine: {
          show: false,
        },
        data: getChartData(),
      },
    ],
  });
}

function getChartData() {
  if (!agents.value.length) return [];
  return [
    {
      name: "Alive (trusted)",
      value: agents.value.filter(
        (agent) => getAgentStatus(agent) === "alive" && agent.trusted
      ).length,
      itemStyle: { color: "#4a9" },
    },
    {
      name: "Alive (untrusted)",
      value: agents.value.filter(
        (agent) => getAgentStatus(agent) === "alive" && !agent.trusted
      ).length,
      itemStyle: { color: "#F7DB89" },
    },
    {
      name: "Pending kill",
      value: agents.value.filter(
        (agent) => getAgentStatus(agent) === "pending kill"
      ).length,
      itemStyle: { color: "hsl(207deg, 61%, 53%)" },
    },
    {
      name: "Dead",
      value: agents.value.filter((agent) => getAgentStatus(agent) === "dead")
        .length,
      itemStyle: { color: "#c31" },
    },
  ];
}

function resizeChart() {
  if (!chart.value) return;
  chart.value.resize();
}
</script>

<template lang="pug">
#agentChartStatus(ref="agentChartStatus")
</template>

<style scoped>
#agentChartStatus {
  width: 100%;
  height: 100%;
}
</style>
