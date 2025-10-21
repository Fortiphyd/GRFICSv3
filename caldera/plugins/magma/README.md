# MITRE Caldera Plugin: Magma
The UI/UX Vue.js framework of Caldera v5.

## Dependencies
* NodeJS (v16+ recommended)
* Caldera (v4.0.0+)

## Installation
If you are going to run Magma without developing on it, all you have to do is run Caldera with an extra flag once. To do so:

In the Caldera directory:
1. Run `python3 server.py --build`.

The `--build` flag automatically installs any dependencies, bundles the Vue frontend into a `dist` directory, and is served by the Caldera server.
You will only have to use the `--build` flag again if you add any plugins.

### Development
To serve up the UI in a development environment (with hot-reloading, etc.), do

In the magma directory:
1. Run `npm install`.
2. Run `npm run build`

In the Caldera directory:
1. Run `python3 server.py --uidev localhost`.

You can reach the UI in your browser at [http://localhost:3000](http://localhost:3000)

### Code Quality
Currently Linting is done manually by the developer. To do so:

1. Run `npm run lint`.

In order to run linting with it automatically formatting issues:

1. Run `npm run lintfix`.

### Testing
Magma uses [Jest](https://jestjs.io/) as its frontend testing framework. All tests are located at the `src/tests` directory.

1. Run `npm run test-all` to run all tests.

Each vue component is tested for accessibility in their respected file. This is done using a custom Jest matcher, [jest-axe](https://github.com/nickcolley/jest-axe). Jest-axe adheres to
[axe-core rules](https://github.com/dequelabs/axe-core/blob/master/doc/rule-descriptions.md). Each one of these rules can be modified or disabled when calling the axe function.

1. Run `npm run test-accessibility` to run only accessibility tests.
