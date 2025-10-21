<script setup>
import { ref, watch, onMounted, inject, onBeforeUnmount } from "vue";
const $api = inject("$api");

const selectedCert = ref("");
const selectedBadge = ref("");
const badgeList = ref([]);
const visibleFlagList = ref([]);
const completedFlags = ref(0);
const completedBadges = ref(0);
const flagList = ref([]);
const completedCertificate = ref(false);
const certificateCode = ref("");
const certificateCodeList = ref([]);
const end = ref(0);
const certificates = ref([
  { name: "User Certificate" },
  { name: "Blue Certificate" },
]);
let updateInterval = ref();

// Simulating Alpine's initTraining with Vue's onMounted
onBeforeUnmount(() => {
  if (updateInterval) clearInterval(updateInterval);
});

onMounted(async () => {
  const res = await $api.get("/plugin/training/certs");
  certificates.value = res.data.certificates;
  let confettiScript = document.createElement("script");
  confettiScript.setAttribute(
    "src",
    "https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js"
  );
  document.head.appendChild(confettiScript);
  if (updateInterval) clearInterval(updateInterval);
  updateInterval = setInterval(async () => {
    getTraining();
  }, "3000");
});

watch(selectedCert, (newValue) => {
  getTraining();
});

watch(selectedBadge, (newValue) => {
  updateVisibleFlags(newValue);
});

const getTraining = () => {
  if (!selectedCert.value) return;
  $api
    .post("/plugin/training/flags", {
      name: selectedCert.value,
      answers: {},
    })
    .then((data) => {
      getFlags(data.data);
      updateVisibleFlags(selectedBadge.value);
      checkCertificateCompletion();
    })
    .catch((e) => console.error(e));
};

function getEmptyDataObject() {
  return {
    flagList: [],
    badgeList: [],
    completedFlags: 0,
    completedBadges: 0,
    certificateCodeList: [],
  };
}

const updateVisibleFlags = (badge) => {
  if (badge) {
    selectedBadge.value = badge;
    visibleFlagList.value = flagList.value.filter(
      (flag) => flag.badge_name === selectedBadge.value.name
    );
  } else {
    visibleFlagList.value = flagList.value;
  }
};

function isCardActive(index) {
  if (selectedBadge.value) {
    const badgeIndex = badgeList.value.findIndex(
      (badge) => badge.name === selectedBadge.value.name
    );
    if (badgeIndex > 0) {
      const earlierFlags = flagList.value.filter(
        (flag) => flag.badge_name === badgeList.value[badgeIndex - 1].name
      );
      if (!earlierFlags[earlierFlags.length - 1].completed) {
        return false;
      }
    }
  }

  return (
    (index === 0 &&
      visibleFlagList.value.length > 0 &&
      !visibleFlagList.value[0].completed) ||
    (visibleFlagList.value[index] &&
      !visibleFlagList.value[index].completed &&
      visibleFlagList.value[index - 1].completed)
  );
}

function checkCertificateCompletion() {
  if (completedBadges.value === badgeList.value.length) {
    completedCertificate.value = true;
    let code = certificateCodeList.value.sort(
      (a, b) => a.toString().length - b.toString().length
    );
    code = code.join(" ");
    certificateCode.value = btoa(code);

    const duration = 10000;
    if (end.value === 0) end.value = Date.now() + duration; // spray confetti for 10 seconds
    playConfetti();
  }
}
function compareFlags(currentBadge, iconSrc, flag, flagIndex) {
  const updatedFlag = {
    ...flag,
    badge_name: currentBadge.name,
    badge_icon: iconSrc,
    cert_name: selectedCert.value,
    showMore: false,
  };
  if (flagList.value[flagIndex]) {
    const previousFlag = flagList.value[flagIndex];
    if (previousFlag.name === updatedFlag.name) {
      updatedFlag.showMore = previousFlag.showMore;
    }
  }
  return updatedFlag;
}
function updateFlagData(newData) {
  if (newData) {
    flagList.value = newData.flagList;
    badgeList.value = newData.badgeList;
    completedFlags.value = newData.completedFlags;
    completedBadges.value = newData.completedBadges;
    certificateCodeList.value = newData.certificateCodeList;
  }
}

async function getFlags(data) {
  if (!data) return;
  const newData = getEmptyDataObject();
  let runningFlagIndex = 0;

  // Fetch flag from API and compares it to previous data,
  // rather than completely override (for variables like showMore)
  data.badges.forEach((badge) => {
    const iconSrc = `/plugin/training/assets/img/badges/${badge.name}.png`;
    let isBadgeCompleted = false;
    let badgeCompletedFlags = 0;

    badge.flags.forEach((flag) => {
      const currentFlag = compareFlags(badge, iconSrc, flag, runningFlagIndex);
      if (currentFlag.completed) badgeCompletedFlags += 1;
      newData.flagList.push(currentFlag);
      newData.certificateCodeList.push(currentFlag.code);
      runningFlagIndex += 1;
    });

    if (badgeCompletedFlags === badge.flags.length) {
      newData.completedBadges += 1;
      isBadgeCompleted = true;
    }

    newData.badgeList.push({
      ...badge,
      completed: isBadgeCompleted,
      icon_src: iconSrc,
    });
    // Keep selected badge so it doesn't get overriden by new data
    if (selectedBadge.value.name === badge.name) selectedBadge.value = badge;
    newData.completedFlags += badgeCompletedFlags;
  });
  updateFlagData(newData);
}
function copyCode() {
  document.getElementById("certificatecode").select();
  document.execCommand("copy");
  // toast('Code copied', true);
}

function playConfetti() {
  const canvas = document.getElementById("confettiCanvas");
  if (!canvas || !confetti) return;
  // eslint-disable-next-line
  const confettiCanon = confetti.create(canvas, {
    resize: true,
    useWorker: true,
  });

  const frame = () => {
    // launch a few confetti from the left edge
    confettiCanon({
      particleCount: 100,
      angle: 60,
      spread: 55,
      origin: { x: 0 },
    });
    // and launch a few from the right edge
    confettiCanon({
      particleCount: 100,
      angle: 120,
      spread: 55,
      origin: { x: 1 },
    });
  };

  // keep going until we are out of time
  if (Date.now() < end.value) {
    requestAnimationFrame(frame);
  }
}
</script>

<template lang="pug">
#trainingPage.section-profile
  template(v-if="completedCertificate")
    canvas#confettiCanvas

  .z-index-1
    div
      div
        h2 Training
      hr

    form
      #select-certificate.field.has-addons
        label.label Select a certificate &nbsp;&nbsp;&nbsp;
        .control.is-expanded
          .select.is-small.is-fullwidth
            select.has-text-centered(v-model="selectedCert")
              option(disabled selected value="") Select a certificate 
              option(v-for="cert in certificates" :value="cert.name" :key="cert.name") {{ cert.name }}

    template(v-if="completedCertificate")
      .content.is-flex.is-align-items-center.is-flex-direction-column.mt-4
        h3 🎉 Certificate complete! 🎉
        .field.has-addons
          .control
            input#certificatecode.input.is-small(type="text" readonly v-model="certificateCode" aria-label="Certificate code")
          .control
            a.button.is-small(@click="copyCode()")
              span.icon
                font-awesome-icon(icon="far fa-copy")
              span Copy
        p Congrats! Fill out the form to validate your code and get a certificate of completion.
        a.button.fancy-button(href="https://forms.office.com/g/sYRNDuxCjC" target="_blank" rel="noopener") Get your certificate 🎓 

    template(v-if="badgeList")
      .is-flex.is-justify-content-space-evenly.mt-3
        template(v-for="(badge, index) in badgeList" :key="index")
          button.badge-container-button(@click="(selectedBadge === badge) ? selectedBadge = '' : selectedBadge = badge" :class="{ 'selected-badge': selectedBadge.name === badge.name }")
            span.is-flex.is-flex-direction-column.is-justify-content-center.is-align-items-center.p-2
              span.badge-icon-container(:class="badge.completed ? 'badge-completed' : ''")
                svg(xmlns="http://www.w3.org/2000/svg" fill="current" viewBox="0 0 24 24" stroke="currentColor")
                  path(stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z")
              img(:alt="badge.name" class="badge-icon-img" onerror="this.src='/plugin/training/assets/img/badges/defaultlock.png'" :src="badge.icon_src")
            span.badge-text.hover.bg-caldera-primary.rounded(:class="{ 'badge-completed-text': badge.completed }")  {{badge.name}}

    .has-text-centered.mt-4.mb-4
      template(v-for="(flag, index) in visibleFlagList" :key="index")
        span.icon
          font-awesome-icon(:icon="flag.completed ? 'fas fa-flag' : 'far fa-flag'")

    .flag-card-container
      template(v-for="(flag, index) in visibleFlagList" :key="flag.name")
        .flag-card.is-flex.is-flex-direction-column.rounded
          .flag-card-content.is-flex.is-flex-direction-column.overflow-hidden(:class="{ 'flag-card-content-active': isCardActive(index), 'flag-show-more': flag.showMore }")
            .flag-card-title.is-flex.is-justify-content-space-evenly.is-align-items-center(:class="{ 'flag-card-title-active': flag.completed || isCardActive(index) }")
              .is-flex.is-justify-content-start.is-align-items-center.flag-card-title-name
                span.icon(:class="flag.completed ? 'flag-icon-completed' : ''")
                  font-awesome-icon(:icon="flag.completed ? 'fas fa-flag' : 'far fa-flag'")
                p {{ flag.name }}
              a.icon.has-tooltip-left.solution-guide-link(:class="flag.has_solution_guide ? '' : 'hidden'" :href="`/plugin/training/solution-guides/certificates/${flag.cert_name}/badges/${flag.badge_name}/flags/${flag.name}`" target="_blank" data-tooltip="Solution Guide")
                font-awesome-icon(icon="far fa-circle-question")
              .is-flex.is-justify-content-center.is-align-items-center.flag-card-title-badge
                span.flag-badge-icon-container
                  svg(xmlns="http://www.w3.org/2000/svg" fill="current" viewBox="0 0 24 24" stroke="currentColor")
                    path(stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z")
                img(:alt="flag.badge_name" class="badge-icon-img" onerror="this.src='/plugin/training/assets/img/badges/defaultlock.png'" :src="flag.badge_icon")
            .flag-card-text
              div
                .is-flex.is-flex-direction-column.is-justify-content-center.has-text-left
                  p.has-text-weight-bold() {{ flag.challenge }}
                  p {{ flag.extra_info }}
                  template(v-if="flag.code.includes('text-entry')")
                    span
                      label(:for="flag.code") Write text here:
                      input(:disabled="flag.completed" class="text-colors-black pl-1 pr-2" :id="flag.code" placeholder="type here" @input="onTextInput")
          .flag-show-more-button.is-flex.is-justify-content-center(@click="flag.showMore = !flag.showMore" :class="{ 'flag-show-more-active': isCardActive(index) }")
            span.icon.is-small
              font-awesome-icon(:icon="flag.showMore ? 'fas fa-chevron-up' : 'fas fa-chevron-down'")
</template>

<style scoped>
#select-certificate {
  max-width: 800px;
  margin: 0 auto;
}

#trainingPage .z-index-1 * {
  z-index: 1;
}

#trainingPage canvas {
  position: fixed;
  z-index: 0;
  width: 85%;
  height: 100%;
  top: 0;
}

#trainingPage .overflow-hidden {
  overflow: hidden;
}

#trainingPage .hover\:bg-caldera-primary:hover {
  background-color: #8b0000 !important;
}

#trainingPage .rounded {
  border-radius: 4px !important;
}

#trainingPage .solution-guide-link {
  color: white;
  cursor: pointer;
}

#trainingPage .hidden {
  pointer-events: none;
  color: grey;
}

#trainingPage .badge-container {
  margin: 0.75rem 0;
}

#trainingPage .badge-container-button {
  color: #ffffff;
  width: 5rem !important;
  padding: 0.85rem 0.25rem 0.25rem;
  font-size: 1rem;
  line-height: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  cursor: pointer;
  background-color: initial;
  border: none;
}

#trainingPage .badge-container-button:hover {
  background-color: #8b0000 !important;
}

#trainingPage .badge-icon-container {
  z-index: 0;
  width: 3.5rem !important;
  fill: currentColor;
  position: absolute;
  opacity: 0.8;
}

#trainingPage .badge-icon-img {
  /*Important styles to override those from shared.css*/
  width: 20px !important;
  height: auto !important;
  border: none !important;
  background-color: initial !important;
  z-index: 10;
  max-width: 100%;
  display: block;
  border-radius: 0;
  margin-bottom: 0;
}

#trainingPage .badge-completed-text {
  background-color: #8b0000 !important;
  color: gray !important;
}

#trainingPage .badge-text {
  text-decoration: none;
  color: #ffffff;
  padding-left: 0.25rem;
  padding-right: 0.25rem;
  margin-top: 1rem;
  font-size: 0.75rem;
  line-height: 1rem;
}

#trainingPage .selected-badge {
  font-weight: bold;
  background-color: #8b0000 !important;
  border-radius: 5px;
}

#trainingPage .flag-card-container {
  display: flex;
  justify-content: space-evenly;
  flex-flow: row wrap;
  box-sizing: border-box;
}

#trainingPage .flag-card {
  box-sizing: border-box;
  margin: 0.25rem;
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
  background-color: initial !important;
}

@media (min-width: 640px) {
  #trainingPage .flag-card {
    width: 100%;
    font-size: 0.875rem;
    line-height: 1.25rem;
  }
}

@media (min-width: 768px) {
  #trainingPage .flag-card {
    width: 33.333333%;
    font-size: 1rem;
    line-height: 1.75rem;
  }
}

@media (min-width: 1024px) {
  #trainingPage .flag-card {
    width: 24%;
    font-size: 0.9rem;
    line-height: 2rem;
  }
}

#trainingPage .flag-icon-completed {
  color: gold;
}

#trainingPage .flag-card-content {
  height: 18rem;
  width: 100%;
  background-color: #272727;
  border-radius: 4px 4px 0 0;
}

#trainingPage .flag-show-more {
  min-height: 18rem;
  height: auto;
}

#trainingPage .flag-card-title {
  padding: 5px;
  background-color: #202020;
  color: #ffffff;
  font-size: 1.125rem;
  line-height: 1.75rem;
  text-align: left;
}

#trainingPage .flag-card-title-active {
  background-color: #8b0000;
}

#trainingPage .flag-card-title div:first-child span {
  width: 1.5rem;
  margin-right: 0.5rem;
}

#trainingPage .flag-card:not(.flag-card-completed) .flag-card-title svg {
  opacity: 0.5;
}

#trainingPage .flag-card-title-name {
  width: 83.333333%;
}

#trainingPage .flag-card-title-badge {
  width: 16.666667%;
}

#trainingPage .flag-badge-icon-container {
  z-index: 0;
  fill: currentColor;
  position: absolute;
  width: 35px;
  padding-top: 6px;
}

#trainingPage .flag-card-text {
  overflow-wrap: break-word;
  padding: 0 0.5rem;
  background-color: #272727;
}

#trainingPage .flag-card-content-active {
  border: 2px solid #8b0000;
  border-bottom: none;
}

#trainingPage .flag-show-more-button {
  padding: 0.5rem;
  cursor: pointer;
  background-color: #272727;
  border-radius: 0 0 4px 4px;
}

#trainingPage .flag-show-more-active {
  border: 2px solid #8b0000;
  border-top: none;
}

#trainingPage .flag-show-more-button span {
  width: 1rem;
}
</style>
