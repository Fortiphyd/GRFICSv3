<script setup>
import { inject, ref, onMounted, onBeforeUnmount, watch } from "vue";
import * as echarts from "echarts";
import { storeToRefs } from "pinia";

import { useAbilityStore } from "@/stores/abilityStore";
import { getAbilityPlatforms } from "@/utils/abilityUtil.js";

const $api = inject("$api");

const abilityStore = useAbilityStore();
const abilityChartStatus = ref(null);
const chart = ref(null);

onMounted(() => {
  initChart();
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
});

watch(abilityStore.abilities, () => {
  setChartOption();
});

async function initChart() {
  chart.value = echarts.init(abilityChartStatus.value);
  chart.value.showLoading("default", {
    maskColor: "rgba(25, 25, 25, 0.8)",
    textColor: "white",
  });
  resizeChart();

  await abilityStore.getAbilities($api);
  setChartOption();
  chart.value.hideLoading();
}

function setChartOption() {
  chart.value.setOption({
    title: {
      text: `${Object.keys(abilityStore.abilities).length} ${
        Object.keys(abilityStore.abilities).length == 1 ? "Ability" : "Abilities"
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
        name: "Ability Platform",
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
  if (!Object.keys(abilityStore.abilities).length) return [];
  return [
    {
      name: "windows",
      value: Object.values(abilityStore.abilities).filter(
        (ability) => getAbilityPlatforms(ability).indexOf("windows") >= 0
      ).length,
      itemStyle: { color: "#4a9" },
    },
    {
      name: "linux",
      value: Object.values(abilityStore.abilities).filter(
        (ability) => getAbilityPlatforms(ability).indexOf("linux") >= 0
      ).length,
      itemStyle: { color: "#F7DB89" },
    },
    {
      name: "darwin",
      value: Object.values(abilityStore.abilities).filter(
        (ability) => getAbilityPlatforms(ability).indexOf("darwin") >= 0
      ).length,
      itemStyle: { color: "hsl(207deg, 61%, 53%)" },
    },
    {
      name: "unknown",
      value: Object.values(abilityStore.abilities).filter(
        (ability) => getAbilityPlatforms(ability).indexOf("unknown") >= 0
      ).length,
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
#abilityChartStatus(ref="abilityChartStatus")
</template>

<style scoped>
#abilityChartStatus {
  width: 100%;
  height: 100%;
}
</style>
