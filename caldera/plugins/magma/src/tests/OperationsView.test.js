import { mount } from "@vue/test-utils";
import { axe, toHaveNoViolations } from "jest-axe";
import OperationsView from "../views/OperationsView.vue";

expect.extend(toHaveNoViolations);
const wrapper = mount(OperationsView);
test("OperationsView should have no accessibility violations", async () => {
  const results = await axe(wrapper.element, {
    // Set axe rules: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
    rules: {
      region: { enabled: false },
    },
  });
  expect(results).toHaveNoViolations();
});
