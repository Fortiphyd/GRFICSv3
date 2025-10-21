<script setup>
import { inject, ref, onMounted, onBeforeUnmount, watch } from "vue";
import * as echarts from "echarts";
import { storeToRefs } from "pinia";

import { useOperationStore } from "@/stores/operationStore";

import { useAgentStore } from "@/stores/agentStore";
import { getAgentStatus } from "@/utils/agentUtil.js";

const $api = inject("$api");

const agentStore = useAgentStore();
const { agents } = storeToRefs(agentStore);

const operationStore = useOperationStore();
const operationChartStatus = ref(null);
const chart = ref(null);

onMounted(() => {
  initChart();
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
});

watch(operationStore.operations, () => {
  setChartOption();
});

async function initChart() {
  chart.value = echarts.init(operationChartStatus.value);
  chart.value.showLoading("default", {
    maskColor: "rgba(25, 25, 25, 0.8)",
    textColor: "white",
  });
  resizeChart();

  await operationStore.getOperations($api);
  setChartOption();
  chart.value.hideLoading();
}

function setChartOption() {
  chart.value.setOption({
    title: {
      text: `${Object.keys(operationStore.operations).length} Operation${
        Object.keys(operationStore.operations).length == 1 ? "" : "s"
      }`,
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
        name: "Operation Status",
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
//Cleanup
//Finished
//Running
//Pause
//Out_of_time

function getChartData() {
  if (!Object.keys(operationStore.operations).length) return [];
  return [
    {
      name: "running",
      value: Object.values(operationStore.operations).filter(
        (operation) => operation.state === "running"
      ).length,
      itemStyle: { color: "#4a9" },
    },
    {
      name: "paused",
      value: Object.values(operationStore.operations).filter(
        (operation) => operation.state === "paused"
      ).length,
      itemStyle: { color: "#F7DB89" },
    },
    {
      name: "cleanup",
      value: Object.values(operationStore.operations).filter(
        (operation) => operation.state === "cleanup"
      ).length,
      itemStyle: { color: "hsl(207deg, 61%, 53%)" },
    },
    {
      name: "out_of_time",
      value: Object.values(operationStore.operations).filter(
        (operation) => operation.state === "out_of_time"
      ).length,
      itemStyle: { color: "#c31" },
    },
    {
      name: "finished",
      value: Object.values(operationStore.operations).filter(
        (operation) => operation.state === "finished"
      ).length,
      itemStyle: { color: "#a05195" },
    },
  ];
}

function resizeChart() {
  if (!chart.value) return;
  chart.value.resize();
}
</script>

<template lang="pug">
#operationChartStatus(ref="operationChartStatus")
</template>

<style scoped>
#operationChartStatus {
  width: 100%;
  height: 100%;
}
</style>
