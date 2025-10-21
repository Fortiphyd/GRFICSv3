import { createApp } from "vue";
import { createPinia } from "pinia";
import VueScrollTo from "vue-scrollto";
import axios from "axios";
import FloatingVue from "floating-vue";
import VNetworkGraph from "v-network-graph"
import "v-network-graph/lib/style.css"

import App from "@/App.vue";
import router from "@/router.js";

// Global styles
import "floating-vue/dist/style.css";

const app = createApp(App);
// Set default API url
const $api = axios.create({
  withCredentials: true,
});
app.provide("$api", $api);

app.use(createPinia());
app.use(router);
app.use(VueScrollTo);
app.use(FloatingVue);
app.use(VNetworkGraph);
app.directive('focus', {
  mounted(el) {
    el.focus();
  }
});
// Font awesome icons, add more icons here as needed
import { library } from '@fortawesome/fontawesome-svg-core';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';

import { 
  faAngleDown, faAngleRight, faAngleUp, faAnglesLeft, faAnglesRight, faArrowRight, faBan, faBook, faCheck, faCog, faDownload, faExclamationTriangle, 
  faExternalLinkAlt, faFileExport, faFileImport, faFlag as fasFlag, faKey, faLock, faMinus, faPause, faPencilAlt, faPlay, faPlus, faPuzzlePiece, faRedo, faRunning, faSave, faFilter,
  faSearch, faSkullCrossbones, faSignOutAlt, faStop, faTimes, faTrash, faUndo, faUnlockAlt, faUpload, faUser, faWeightHanging, faFolderOpen, faFolder, faFile, faDragon, faFolderClosed, faArrowLeft, faArrowUp, faArrowDown, 
  faChevronUp, faChevronDown, faBroom, faForward, faFastForward, faBackward, faFastBackward
} from '@fortawesome/free-solid-svg-icons';
library.add(
  faAngleDown, faAngleRight, faAngleUp, faAnglesLeft, faAnglesRight, faArrowRight, faBan, faBook, faCheck, faCog, faDownload, faExclamationTriangle, faFilter,
  faExternalLinkAlt, faFileExport, faFileImport, fasFlag, faKey, faLock, faMinus, faPause, faPencilAlt, faPlay, faPlus, faPuzzlePiece, faRedo, faRunning, faSave, 
  faSearch, faSkullCrossbones, faSignOutAlt, faStop, faTimes, faTrash, faUndo, faUnlockAlt, faUpload, faUser, faWeightHanging, faFolderOpen, faFolder, faFile, faDragon, faFolderClosed, faArrowLeft, faArrowUp, faArrowDown,
  faChevronUp, faChevronDown, faBroom, faForward, faFastForward, faBackward, faFastBackward
);
import { 
  faCircle, faCircleQuestion, faCopy, faFlag as farFlag
} from '@fortawesome/free-regular-svg-icons';
library.add(
  faCircle, faCircleQuestion, faCopy, farFlag
);
import { 
  faApple, faLinux, faWindows 
} from '@fortawesome/free-brands-svg-icons';
library.add(
  faApple, faLinux, faWindows
);

app.component('font-awesome-icon', FontAwesomeIcon);

app.mount("#app");
