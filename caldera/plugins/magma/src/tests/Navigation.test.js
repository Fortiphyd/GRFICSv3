import { mount } from "@vue/test-utils";
import { axe, toHaveNoViolations } from "jest-axe";
import Navigation from "../components/core/Navigation.vue";
import { createTestingPinia } from "@pinia/testing";

expect.extend(toHaveNoViolations);
test("Navigation should have no accessibility violations", async () => {
  const wrapper = mount(Navigation, {
    global: {
      plugins: [createTestingPinia()],
      stubs: ["router-link"],
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
