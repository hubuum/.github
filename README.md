# Hubuum shared repository

This repository holds the [GitHub organization profile](profile/README.md),
shared documentation tooling, and reusable Pages workflows. The public ecosystem
landing page lives in [hubuum/hubuum.github.io](https://github.com/hubuum/hubuum.github.io).
Each product keeps its documentation with its own source.

## Documentation platform

[The maintainer guide](docs-tooling/README.md) describes the shared theme,
source staging, immutable versions, link checks, and publishing workflow.
Projects pin the shared revision; a change here does not silently rebuild every
site with moving tooling.

## Initial hosting setup

Run this in an administrator's authenticated terminal:

```sh
bash scripts/setup-pages.sh
```

It creates the organization-site repository when needed and enables GitHub
Actions Pages for the ecosystem, server, Rust client, Python client, CLI, and
frontend sites. It preserves existing environment reviewers and branch
protections. Merge each project's documentation PR to publish its site.
