# Hubuum shared repository

This repository holds the [GitHub organization profile](profile/README.md),
shared documentation tooling, and reusable Pages workflows. The public ecosystem
landing page lives in [hubuum/hubuum.github.io](https://github.com/hubuum/hubuum.github.io).
Each product keeps its documentation with its own source.

## Documentation platform

[The maintainer guide](docs-tooling/README.md) describes the shared theme,
source staging, frozen release content, shared styles, link checks, and publishing workflow.
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

## Documentation-only CI

Pull requests and pushes containing only repository prose run Markdown lint
without the Python tooling test matrix. Tooling, shared theme, and workflow
changes retain the complete tooling checks. Unknown files and executable examples also retain tooling CI. Mixed changes run both kinds of checks.

`scripts/ci-policy.py` owns the allowlist and exceptions. Update its regression
tests whenever a document becomes a build, test, or packaging input; direct
literal Rust includes are checked automatically. Run the policy tests with
`python3 scripts/test-ci-policy.py`.

The `markdown` check is the aggregate CI gate: classification failures,
failed checks, and unexpectedly skipped required jobs fail it. Keep that check
required in branch protection. Add the `ci:full` pull-request label or dispatch
the CI workflow manually to request complete validation. The reusable documentation build and publish workflows retain their existing
validation and are unaffected by this repository's prose-only selection.
