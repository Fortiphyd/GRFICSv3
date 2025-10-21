module.exports = {
  moduleFileExtensions: ["js", "json", "vue"],
  globals: {
    "vue-jest": {
      pug: { doctype: "html" },
    },
  },
  transform: {
    ".*\\.js$": "babel-jest",
    ".*\\.(vue)$": "@vue/vue3-jest",
  },
  transformIgnorePatterns: ["/node_modules/(?!pinia).+\\.js$"],
  testEnvironment: "jsdom",
};
