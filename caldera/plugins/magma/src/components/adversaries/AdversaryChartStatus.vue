<script setup>
import { inject, ref, onMounted, onBeforeUnmount, watch } from "vue";
import * as echarts from "echarts";
import { storeToRefs } from "pinia";

import { useAdversaryStore } from "@/stores/adversaryStore";

const $api = inject("$api");

const adversaryStore = useAdversaryStore();
const adversaryChartStatus = ref(null);
const chart = ref(null);
const possibleColors = ["#4a9", "#F7DB89", "hsl(207deg, 61%, 53%)", "#c31"];

onMounted(() => {
  initChart();
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
});

watch(adversaryStore.adversaries, () => {
  setChartOption();
});

async function initChart() {
  chart.value = echarts.init(adversaryChartStatus.value);
  chart.value.showLoading("default", {
    maskColor: "rgba(25, 25, 25, 0.8)",
    textColor: "white",
  });
  resizeChart();

  await adversaryStore.getAdversaries($api);
  setChartOption();
  chart.value.hideLoading();
}

function setChartOption() {
  chart.value.setOption({
    title: {
      text: `${Object.keys(adversaryStore.adversaries).length} ${Object.keys(adversaryStore.adversaries).length == 1 ? "Adversary" : "Adversaries"}`,
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
        name: "Adversary Plugin",
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
  if (!Object.keys(adversaryStore.adversaries).length) return [];
  const adversaryPlugins = [
    ...new Set(
      Object.values(adversaryStore.adversaries).map((adversary) => {
        if (adversary.plugin === "") return "none";
        return adversary.plugin;
      })
    ),
  ];
  let currentColorIndex = 0;
  const chartData = adversaryPlugins.map((plugin) => {
    if (currentColorIndex >= possibleColors.length) currentColorIndex = 0;
    return {
      name: plugin,
      value: Object.values(adversaryStore.adversaries).filter((adversary) => {
        if (plugin === "none") return adversary.plugin === "";
        return adversary.plugin === plugin;
      }).length,
      itemStyle: { color: possibleColors[currentColorIndex++] },
    };
  });
  return chartData;
}

function resizeChart() {
  if (!chart.value) return;
  chart.value.resize();
}
</script>

<template lang="pug">
#adversaryChartStatus(ref="adversaryChartStatus")
</template>

<style scoped>
#adversaryChartStatus {
  width: 100%;
  height: 100%;
}
</style>
