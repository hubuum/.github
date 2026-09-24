#!/usr/bin/env bash
set -euo pipefail

tooling_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
command="${1:-build}"
version="${2:-main}"
if [[ "$command" == check ]]; then
  exec python3 -I -S "$tooling_root/test-check-docs.py"
fi
if [[ "$command" != build && "$command" != serve ]]; then
  echo 'Usage: bash scripts/docs.sh [check|build|serve] [main|vX.Y.Z]' >&2
  exit 2
fi
if [[ "$version" != main && ! "$version" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
  echo 'Version must be main or a stable vX.Y.Z tag.' >&2
  exit 2
fi
python3 "$tooling_root/check-docs.py" --help > /dev/null
mkdir -p target
source_root="$repo_root"
source_sha="$(git rev-parse HEAD)"
if [[ "$version" != main ]]; then
  source_sha="$(git rev-parse --verify "refs/tags/$version^{commit}")"
  source_root="$(mktemp -d "$repo_root/target/docs-release.XXXXXX")"
  trap 'rm -rf "$source_root"' EXIT
  git archive "$source_sha" | tar -x -C "$source_root"
fi
python3 "$tooling_root/docs-versions.py" prepare --source "$source_root" \
  --destination target/docs-source --version "$version" --source-sha "$source_sha"
python3 "$tooling_root/check-docs.py" --root target/docs-source
source "$tooling_root/tools.env"
builder="$(python3 -c 'import tomllib; print(tomllib.load(open("zensical.toml", "rb")).get("tool", {}).get("hubuum_docs", {}).get("builder", "container"))')"
mkdir -p target/docs-site target/docs-cache target/docs-source/site target/docs-source/.cache
if [[ "$builder" == uv ]]; then
  # The caller's locked docs dependencies provide mkdocstrings. API sources in
  # the staged tree come from the selected tag, never from the current package.
  uv run --locked --extra dev zensical build --strict \
    --config-file "$repo_root/target/docs-source/zensical.toml"
  rm -rf target/docs-site
  mv target/docs-source/site target/docs-site
elif [[ "$builder" == container ]]; then
  docker run --rm --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$repo_root/target/docs-source,dst=/docs,readonly" \
    --mount "type=bind,src=$repo_root/target/docs-site,dst=/docs/site" \
    --mount "type=bind,src=$repo_root/target/docs-cache,dst=/docs/.cache" \
    "$ZENSICAL_IMAGE" build --strict
else
  echo "Unknown documentation builder: $builder" >&2
  exit 2
fi
python3 "$tooling_root/check-docs.py" --root target/docs-source --site-dir target/docs-site
cp target/docs-source/build.json target/docs-site/build.json
if [[ "$command" == serve ]]; then
  echo 'Preview: http://127.0.0.1:8000/ (rebuild after editing sources).'
  python3 -m http.server 8000 --bind 127.0.0.1 --directory target/docs-site
fi
