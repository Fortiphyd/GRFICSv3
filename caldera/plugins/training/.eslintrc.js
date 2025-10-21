module.exports = {
    "extends": "airbnb-base",
    "env": {
        "browser": true,
        "es2021": true,
        "jquery": true,
    },
    "parserOptions": {
        "ecmaVersion": 12
    },
    "globals": {
        stream: "readonly",
        restRequest: "readonly",
        certificates: "readonly",
    },
    "rules": {
        // These can't be fixed with --fix and will require manual updates.
        "camelcase": "off",
        "eqeqeq": "off",
        "func-names": "off",
        "guard-for-in": "off",
        "no-alert": "off",
        "no-case-declarations": "off",
        "no-console": "off",
        "no-labels": "off",
        "no-param-reassign": "off",
        "no-restricted-globals": "off",
        "no-restricted-syntax": "off",
        "no-unused-vars": "off",
        "no-use-before-define": "off",
    }
};
