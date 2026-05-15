# Development

Use the devcontainer or initialize the local environment with:

```bash
scripts/setup
```

Useful commands:

```bash
scripts/lint
scripts/test
scripts/check
scripts/docs
scripts/develop
```

`scripts/check` is the local quality gate used by CI. It runs formatting,
linting, type checking, compile checks, tests, Bandit, HACS metadata validation,
and documentation builds.

## Documentation Rules

Public modules, classes, and functions should include clear Google-style
docstrings. Private helpers should include docstrings when they encode OpenDTU
API quirks, Home Assistant registry behavior, or non-obvious data-shaping logic.
