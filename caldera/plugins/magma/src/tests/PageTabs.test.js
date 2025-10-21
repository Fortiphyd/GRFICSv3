import { mount } from "@vue/test-utils";
import { axe, toHaveNoViolations } from "jest-axe";
import { createRouter, createWebHistory } from "vue-router";
import PageTabs from "../components/core/PageTabs.vue";
import { createTestingPinia } from "@pinia/testing";

// Cant use mock router because component is modifying router
// Note for future reference: For testing the router specifically it might be better to import all routes
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: {
        template: "Testing",
      },
    },
  ],
});

expect.extend(toHaveNoViolations);
test("PageTabs should have no accessibility violations", async () => {
  const wrapper = mount(PageTabs, {
    global: {
      plugins: [createTestingPinia(), router],
    },
  });
  const results = await axe(wrapper.element, {
    // Set axe rules: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
    rules: {
      region: { enabled: false },
    },
  });
  expect(results).toHaveNoViolations();
});
