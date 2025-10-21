# MITRE Caldera Plugin: Training

The training plugin provides a certification course to become a Caldera subject matter expert (SME)

If you earn a code, submit the code to this form to obtain a certificate: https://forms.office.com/g/sYRNDuxCjC.

## Development

### JavaScript:
This plugin uses `eslint` for javascript linting and requires the following dependencies:

* `node >= 15.9.0`
* `npm >= 7.5.0`

Linting is performed automatically when changes are pushed to a branch in github via a github
action.

To run locally, perform the following commands:

```
> cd /path/to/training/repo
> npm ci
> npm run lint
```

To fix issues automatically run the following (note: not all violations can be fixed automatically):

```
> npm run lint -- --fix
```

For information about rule violations, see the [eslint rules](https://eslint.org/docs/rules/) page.
