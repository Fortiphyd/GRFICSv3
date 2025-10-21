import { mount } from "@vue/test-utils";
import { axe, toHaveNoViolations } from "jest-axe";
import PlannersView from "../views/PlannersView.vue";

expect.extend(toHaveNoViolations);
const wrapper = mount(PlannersView);
test("PlannersView should have no accessibility violations", async () => {
  const results = await axe(wrapper.element, {
    // Set axe rules: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
    rules: {
      region: { enabled: false },
    },
  });
  expect(results).toHaveNoViolations();
});
