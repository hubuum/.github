# Shared Hubuum documentation platform

All six sites share Zensical styling, ecosystem navigation, source staging,
link checks, and GitHub Pages publishing. Product repositories own their
navigation, examples, API sources, compatibility records, and release history.
The organization landing page is unversioned; each product's root opens its
latest stable release, with immutable `/vX.Y.Z/` and explicitly selected `/main/`
editions.

## Repository ownership

| Repository | Public site |
| --- | --- |
| `hubuum/hubuum.github.io` | `https://hubuum.github.io/` |
| `hubuum/hubuum` | `https://hubuum.github.io/hubuum/` |
| `hubuum/hubuum-client-rust` | `https://hubuum.github.io/hubuum-client-rust/` |
| `hubuum/hubuum-client-python` | `https://hubuum.github.io/hubuum-client-python/` |
| `hubuum/hubuum-cli` | `https://hubuum.github.io/hubuum-cli/` |
| `hubuum/hubuum-frontend` | `https://hubuum.github.io/hubuum-frontend/` |

The `.github/profile/README.md` file supplies the organization profile on GitHub.
It links to the public ecosystem site; it does not publish the root Pages site.

## Project configuration

`zensical.toml` supplies the project name, URLs, and navigation. Shared theme
settings come from `theme/defaults.json` and can be overridden in `[project]`.
Additional `[tool.hubuum_docs]` settings are:

| Setting | Purpose |
| --- | --- |
| `versioned` | Defaults to `true`; only the ecosystem landing page uses `false`. |
| `source_files` | Maps repository files such as `README.md` into generated documentation paths; the originals remain canonical. |
| `source_trees` | Includes tagged source trees for generated API reference, such as the Python client's `src`. |
| `builder` | `container` uses the digest-pinned official Zensical image; `uv` uses a Python project's locked documentation dependencies. |
| `link_migrations` | Explicitly repairs historical moved-file/anchor links when the replacement exists in the selected tag. |

Every staged Markdown page must occur in navigation exactly once. The renderer
rewrites relative repository links and imported-document links; release source
links use the resolved tag commit. Tags predating the site get a generated entry
page and navigation filtered to their original documents. Current tutorials are
never copied into an older edition. Python API reference reads the tagged source.

## Local builds

Copy `bootstrap.sh` to the project's `scripts/docs.sh`. Pin this repository's full
commit SHA in `.github/docs-tools.env` as `DOCS_TOOLING_REVISION`, and pin the
reusable workflows to the same SHA. Then run:

```sh
bash scripts/docs.sh build
bash scripts/docs.sh serve
bash scripts/docs.sh build vX.Y.Z
```

Python 3.11+, Bash, and Git are required. Most projects also require Docker; the
Python client uses its existing uv lock and mkdocstrings dependencies instead.
The shared Python scripts use only the standard library. The preview serves
`target/docs-site/` on loopback port 8000; rebuild after editing sources.

For development of this tooling, set `DOCS_TOOLING_ROOT` to an explicit local
checkout of this repository. Published workflows always checkout a pinned SHA.

## CI and publishing

`docs-build.yml` builds with read-only repository permission. It checks the
shared contracts, builds development and the latest published stable GitHub
release, checks source and rendered links, and retains `documentation-site` for
14 days. A manual version input additionally builds an older published release.

The calling workflow accepts ordinary PR/main events, published releases, and
successful release-workflow completions from this repository's own tag pushes.
The completion trigger covers releases created by `GITHUB_TOKEN`; PR workflow
completions cannot publish. Callers keep the build and publishing jobs separate
so write permissions exist only on trusted publishing events.
The Python client's GitHub releases are published manually after PyPI succeeds,
so its site uses the release-published event directly.

`docs-publish.yml` checks out the exact source revision validated by the build
and downloads that run's artifact. Publication is serialized per repository.
It combines editions with the retained `gh-pages` archive, commits generated
files under `site/`, and deploys a Pages artifact. Release directories are
append-only: the same source commit preserves the existing output, while a moved
tag is rejected. The highest stable archived version remains the default when
an older release is backfilled. Search stays within the selected edition.

Archive retention is independent of Actions artifact expiry. Keep the
`gh-pages` branch; never force-push or delete it. A manual workflow run on `main`
can retry publication after a hosting failure.

## Validate and update

```sh
python3 -I -S docs-tooling/test-check-docs.py
bash -n docs-tooling/build.sh docs-tooling/bootstrap.sh scripts/setup-pages.sh
npx --yes markdownlint-cli2@0.23.3 --config .markdownlint.json '**/*.md' '!target'
```

For changes to source staging, the theme, or Zensical, also build each project's
current and latest-release editions. Inspect the ecosystem home, generated
Python API, version menu, search, light/dark modes, and narrow-screen navigation.
The shared theme and version archive originated in the server documentation PR.

Adopt a reviewed change by updating each project's tooling and workflow pins
together. Keep project-specific fixes in that project's source and shared
behavior here. No synchronized application release is required.
