#!/usr/bin/env bash
# Run from an authenticated administrator's terminal. Never prints credentials.
set -euo pipefail
export GH_HOST=github.com

org=hubuum
landing="$org/$org.github.io"
gh auth status --hostname github.com
gh api --hostname github.com user --jq '"Authenticated as " + .login'

if ! gh repo view "$landing" --json name --jq .name > /dev/null 2>&1; then
  gh repo create "$landing" --public --add-readme \
    --description 'Hubuum ecosystem: server, web frontend, CLI, and client libraries'
fi

for name in hubuum.github.io hubuum hubuum-client-rust hubuum-client-python hubuum-cli hubuum-frontend; do
  repo="$org/$name"
  echo "Configuring GitHub Actions Pages for $repo"
  if gh api --hostname github.com "repos/$repo/pages" > /dev/null 2>&1; then
    gh api --hostname github.com --method PUT "repos/$repo/pages" \
      -f build_type=workflow --silent
  else
    gh api --hostname github.com --method POST "repos/$repo/pages" \
      -f build_type=workflow --silent
  fi

  # Preserve existing environment reviewers and protection rules. The checked-in
  # workflows restrict publishing to trusted main/release events themselves.
  if ! gh api --hostname github.com "repos/$repo/environments/github-pages" > /dev/null 2>&1; then
    gh api --hostname github.com --method PUT "repos/$repo/environments/github-pages" --silent
  fi
  policy="$(gh api --hostname github.com "repos/$repo/environments/github-pages" \
    --jq '.deployment_branch_policy | if . == null then "unrestricted" elif .protected_branches then "protected" else "custom" end')"
  if [[ "$policy" == custom ]]; then
    for type in branch tag; do
      pattern=main
      [[ "$type" == branch ]] || pattern='v*'
      if ! gh api --hostname github.com "repos/$repo/environments/github-pages/deployment-branch-policies" \
        --jq '.branch_policies[] | [.type, .name] | @tsv' | \
        awk -F '\t' -v expected_type="$type" -v expected_name="$pattern" \
          '$1 == expected_type && $2 == expected_name { found=1 } END { exit !found }'; then
        gh api --hostname github.com --method POST \
          "repos/$repo/environments/github-pages/deployment-branch-policies" \
          -f name="$pattern" -f type="$type" --silent
      fi
    done
  elif [[ "$policy" == protected ]]; then
    echo "  Existing protected-branch deployment policy preserved; check main/tag access before publishing."
  fi
done

echo 'Repository and Pages settings are ready. Merge the documentation PRs to publish the sites.'
echo 'Existing branch protection, reviewers, releases, and source branches were preserved.'
