import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/authStore.js";
import axios from "axios";

import HomeView from "./views/HomeView.vue";
import LoginView from "./views/LoginView.vue";
import AgentsView from "./views/AgentsView.vue";
import PayloadsView from "./views/PayloadsView.vue";
import AbilitiesView from "./views/AbilitiesView.vue";
import AdversariesView from "./views/AdversariesView.vue";
import OperationsView from "./views/OperationsView.vue";
import SchedulesView from "@/views/SchedulesView.vue";
import FactSourcesView from "./views/FactSourcesView.vue";
import ObjectivesView from "./views/ObjectivesView.vue";
import PlannersView from "./views/PlannersView.vue";
import ContactsView from "./views/ContactsView.vue";
import ObfuscatorsView from "./views/ObfuscatorsView.vue";
import SettingsView from "./views/SettingsView.vue";
import ExfilledFilesView from "./views/ExfilledFilesView.vue";
import PluginView from "./views/PluginView.vue";
import NotFoundView from "./views/NotFoundView.vue";

// Cant use global API variable because we aren't in a component
const $api = axios.create({
  withCredentials: true,
  baseURL: window.location.origin,
});

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/agents",
      name: "agents",
      component: AgentsView,
    },
    {
      path: "/payloads",
      name: "payloads",
      component: PayloadsView,
    },
    {
      path: "/abilities",
      name: "abilities",
      component: AbilitiesView,
    },
    {
      path: "/adversaries",
      name: "adversaries",
      component: AdversariesView,
    },
    {
      path: "/operations",
      name: "operations",
      component: OperationsView,
    },
    {
      path: "/schedules",
      name: "schedules",
      component: SchedulesView,
    },
    {
      path: "/factsources",
      name: "fact sources",
      component: FactSourcesView,
    },
    {
      path: "/objectives",
      name: "objectives",
      component: ObjectivesView,
    },
    {
      path: "/planners",
      name: "planners",
      component: PlannersView,
    },
    {
      path: "/contacts",
      name: "contacts",
      component: ContactsView,
    },
    {
      path: "/obfuscators",
      name: "obfuscators",
      component: ObfuscatorsView,
    },
    {
      path: "/settings",
      name: "settings",
      component: SettingsView,
    },
    {
      path: "/exfilledfiles",
      name: "exfilled files",
      component: ExfilledFilesView,
    },
    {
      path: "/plugins/:pluginName",
      name: "Plugin",
      component: PluginView,
      props: true,
    },
    {
      path: '/docs/index.html',
      beforeEnter: () => {
        window.location.href = '/docs/index.html';
      }
    },
    { path: "/:pathMatch(.*)*", name: "NotFound", component: NotFoundView },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    } else {
      return { top: 0 };
    }
  },
});

router.beforeEach(async (to) => {
  const publicPages = ["/login"];
  const authRequiredPages = !publicPages.includes(to.path);
  const auth = useAuthStore();
  // Check that the user is authenticated before each page in case something changes in server
  auth.isUserAuthenticated = await auth.getAuthStatus($api);
  if (to.path == "/login" && auth.isUserAuthenticated) {
    return "/";
  }
  if (authRequiredPages && !auth.isUserAuthenticated) {
    auth.returnUrl = to.name;
    return "/login";
  }
});

export default router;
