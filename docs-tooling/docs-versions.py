#!/usr/bin/env python3
"""Prepare tagged documentation and retain released content for Pages."""

from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(
        "Hubuum tooling requires Python 3.11 or newer; found "
        + sys.version.split()[0]
        + ". Install Python 3.11+ and ensure python3 on PATH selects it."
    )

import argparse
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import tomllib
from urllib.parse import quote, urlsplit


ROOT = Path.cwd()
TOOLING = Path(__file__).resolve().parent
RELEASE = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
LIVE_STYLESHEET = "https://hubuum.github.io/assets/stylesheets/hubuum.css"


def validate_version(version: str) -> str:
    if version != "main" and not RELEASE.fullmatch(version):
        raise ValueError("Version must be main or a stable release tag such as v0.0.16")
    return version


def toml_value(value: object) -> str:
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{json.dumps(k)} = {toml_value(v)}" for k, v in value.items()) + " }"
    if isinstance(value, list):
        return "[" + ", ".join(map(toml_value, value)) + "]"
    return json.dumps(value, ensure_ascii=False)


def settings() -> dict:
    return tomllib.loads((ROOT / "zensical.toml").read_text()).get("tool", {}).get("hubuum_docs", {})


def project_config() -> dict:
    project = json.loads((TOOLING / "theme/defaults.json").read_text())
    overrides = tomllib.loads((ROOT / "zensical.toml").read_text())["project"]
    def merge(base, extra):
        for key, value in extra.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                merge(base[key], value)
            else:
                base[key] = value
    merge(project, overrides)
    project["extra"].update(json.loads((TOOLING / "theme/ecosystem.json").read_text()))
    return project


def filter_nav(value: object, available: set[str], seen: set[str], source: Path, source_sha: str, repo_url: str) -> object:
    if isinstance(value, str):
        if match := re.match(re.escape(repo_url) + r"/(blob|tree)/main/(.*)", value):
            if not (source / match[2]).exists():
                return None
            return value.replace("/main/", f"/{source_sha}/", 1)
        if urlsplit(value).scheme or value in available:
            seen.add(value)
            return value
        return None
    if isinstance(value, list):
        return [item for child in value if (item := filter_nav(child, available, seen, source, source_sha, repo_url))]
    return {key: item for key, child in value.items() if (item := filter_nav(child, available, seen, source, source_sha, repo_url))}


def release_home(source: Path, version: str, source_sha: str, project: dict) -> str:
    def links(value):
        if isinstance(value, list):
            return [item for child in value for item in links(child)]
        if isinstance(value, dict):
            result = []
            for label, child in value.items():
                if isinstance(child, str):
                    if child != "index.md" and child.endswith(".md") and (source / "docs" / child).is_file():
                        result.append(f"[{label}]({child})")
                else:
                    result.extend(links(child))
            return result
        return []
    cards = []
    for section in project["nav"]:
        for title, children in section.items():
            if items := links(children)[:3]:
                cards.append(f"- **{title}**\n\n    " + " · ".join(items))
    navigation = '<div class="grid cards" markdown>\n\n' + "\n\n".join(cards) + "\n\n</div>\n\n" if cards else ""
    if (source / "docs/openapi.json").is_file():
        navigation += "[Download this edition's OpenAPI specification](openapi.json).\n\n"
    return (
        f"# {project['site_name']} {version}\n\n"
        "Guides and reference from this released version. Choose a topic in the navigation or search this edition.\n\n"
        + navigation +
        "This edition preserves the documentation shipped with the release and uses the shared website theme. "
        "Choose **main (development)** in the version menu for unreleased documentation.\n\n"
        f"[Release notes]({project['repo_url']}/releases/tag/{version}) · "
        f"[Source snapshot]({project['repo_url']}/tree/{source_sha}) · "
        "[Hubuum ecosystem](https://hubuum.github.io/)\n"
    )


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Source path escapes repository: {relative}")
    return path


def prepare(source: Path, destination: Path, version: str, source_sha: str) -> None:
    source = source.resolve()
    destination = destination.resolve()
    validate_version(version)
    if source.resolve().is_relative_to(destination.resolve()):
        raise ValueError("The staging destination must not contain the source checkout")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("Source revision must be a full Git commit SHA")
    if not (source / "docs").is_dir():
        raise ValueError("The selected release has no docs directory")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    shutil.copytree(source / "docs", destination / "docs")
    shutil.copytree(TOOLING / "theme/overrides", destination / "docs-theme/overrides")
    shutil.copytree(TOOLING / "theme/assets", destination / "docs/assets", dirs_exist_ok=True)
    project = project_config()
    api_version = "latest" if version == "main" else version.removeprefix("v")
    project = json.loads(json.dumps(project).replace("{version}", api_version))
    options = settings()
    if relative := options.get("theme_overrides"):
        overrides = inside(source, relative)
        if overrides.is_dir():
            for path in overrides.rglob("*"):
                inside(source, str(path.relative_to(source)))
            shutil.copytree(overrides, destination / "docs-theme/overrides", dirs_exist_ok=True)
        elif version == "main":
            raise ValueError(f"Configured theme overrides are missing: {relative}")
    origins = {page.relative_to(destination / "docs").as_posix(): source / "docs" / page.relative_to(destination / "docs") for page in (destination / "docs").rglob("*.md")}
    for original, rendered in options.get("source_files", {}).items():
        origin = inside(source, original)
        target = inside(destination / "docs", rendered)
        if not origin.is_file():
            if version == "main":
                raise ValueError(f"Configured source file is missing: {original}")
            continue
        if target.exists():
            raise ValueError(f"Imported source would replace a documentation page: {rendered}")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = origin.read_text()
        if version == "main" and not content.startswith("---\n"):
            content = f'---\nedit_path: "../{original}"\n---\n\n' + content
        target.write_text(content)
        origins[rendered] = origin
    for relative in options.get("source_trees", []):
        origin = inside(source, relative)
        if origin.is_dir():
            shutil.copytree(origin, inside(destination, relative))
    repo_url = project["repo_url"].rstrip("/")
    versioned = options.get("versioned", True)
    base_url = project["site_url"].rstrip("/") + "/"
    project["site_url"] = base_url + version + "/" if versioned else base_url
    # The builder mounts target/docs-site here inside its container.
    project["site_dir"] = "site"
    project.setdefault("extra", {})["docs_version"] = version
    project["extra"]["docs_versioned"] = versioned
    project["extra"]["docs_source_sha"] = source_sha
    if version != "main":
        project["edit_uri"] = ""
        project["theme"]["features"] = [feature for feature in project["theme"]["features"] if feature != "content.action.edit"]
        index = destination / "docs/index.md"
        if not index.exists():
            index.write_text(release_home(destination, version, source_sha, project))
        available = {p.relative_to(destination / "docs").as_posix() for p in (destination / "docs").rglob("*.md")}
        seen: set[str] = set()
        project["nav"] = filter_nav(project["nav"], available, seen, source, source_sha, repo_url)
        if extra := sorted(available - seen):
            project["nav"].append({"Release reference": extra})

    # Keep repository links pinned to the same source as the documentation.
    for page in (destination / "docs").rglob("*.md"):
        content = re.sub(r"(https://docs\.rs/[^/]+/)\{version\}/", rf"\g<1>{api_version}/", page.read_text())
        source_page = origins.get(page.relative_to(destination / "docs").as_posix())

        def repository_link(match: re.Match) -> str:
            href = match[1]
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path or source_page is None:
                return match[0]
            target = (source_page.parent / parsed.path).resolve()
            if not target.is_relative_to(source.resolve()):
                raise ValueError(f"Link escapes source repository in {source_page}: {href}")
            migration_key = target.relative_to(source).as_posix() + ("#" + parsed.fragment if parsed.fragment else "")
            migration = options.get("link_migrations", {}).get(migration_key)
            if migration:
                replacement = urlsplit(migration)
                replacement_target = inside(source, replacement.path)
                if replacement_target.is_file():
                    target = replacement_target
                    parsed = parsed._replace(fragment=replacement.fragment)
            suffix = ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
            if target.is_relative_to((source / "docs").resolve()):
                rendered_target = destination / "docs" / target.relative_to(source / "docs")
                return f"]({Path(os.path.relpath(rendered_target, page.parent)).as_posix()}{suffix})"
            relative = target.relative_to(source.resolve()).as_posix()
            if relative in options.get("source_files", {}):
                rendered_target = destination / "docs" / options["source_files"][relative]
                return f"]({Path(os.path.relpath(rendered_target, page.parent)).as_posix()}{suffix})"
            kind = "tree" if target.is_dir() else "blob"
            ref = "main" if version == "main" else source_sha
            return f"]({repo_url}/{kind}/{ref}/{quote(relative)}{suffix})"

        content = re.sub(r"\]\(([^)]+)\)", repository_link, content)
        if version != "main":
            content = re.sub("(" + re.escape(repo_url) + r"/(?:blob|tree)/)main/", rf"\g<1>{source_sha}/", content)
        page.write_text(content)
    (destination / "zensical.toml").write_text("[project]\n" + "\n".join(f"{json.dumps(k)} = {toml_value(v)}" for k, v in project.items()) + "\n")
    (destination / "build.json").write_text(json.dumps({"version": version, "source_sha": source_sha}, indent=2) + "\n")


def assemble(site: Path, archive: Path, version: str, source_sha: str) -> None:
    validate_version(version)
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("Source revision must be a full Git commit SHA")
    if not (site / "index.html").is_file():
        raise ValueError("Refusing to publish a site without index.html")
    if not settings().get("versioned", True):
        if site.resolve().is_relative_to(archive.resolve()):
            raise ValueError("The archive destination must not contain the built site")
        if archive.exists():
            shutil.rmtree(archive)
        shutil.copytree(site, archive)
        (archive / ".nojekyll").touch()
        return
    manifest = archive / "versions.json"
    versions = json.loads(manifest.read_text()) if manifest.exists() else []
    existing = next((entry for entry in versions if entry["version"] == version), None)
    target = archive / version
    if existing and version != "main":
        if existing["source_sha"] != source_sha:
            raise ValueError(f"Refusing to replace immutable {version}: source commit changed")
        if not (target / "index.html").is_file():
            raise ValueError(f"Archive for {version} is incomplete")
        # A new renderer must not rewrite released HTML or source artifacts.
        # Shared presentation CSS is maintained separately by refresh_styles.
        return
    if target.exists():
        if version != "main":
            raise ValueError(f"Refusing to overwrite untracked archive {version}")
        shutil.rmtree(target)
    archive.mkdir(parents=True, exist_ok=True)
    shutil.copytree(site, target)
    versions = [entry for entry in versions if entry["version"] != version]
    versions.append({"version": version, "source_sha": source_sha})
    releases = sorted((entry for entry in versions if entry["version"] != "main"), key=lambda entry: tuple(map(int, RELEASE.fullmatch(entry["version"]).groups())), reverse=True)
    versions = releases + [entry for entry in versions if entry["version"] == "main"]
    manifest.write_text(json.dumps(versions, indent=2) + "\n")
    (archive / ".nojekyll").touch()
    if releases:
        latest = releases[0]["version"]
        (archive / "index.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Hubuum documentation</title>'
            f'<meta http-equiv="refresh" content="0; url={latest}/">'
            f'<p><a href="{latest}/">Open the latest released documentation ({html.escape(latest)})</a>.</p></html>\n'
        )
        # GitHub Pages serves only the root 404 page for unknown paths.
        root_url = tomllib.loads((ROOT / "zensical.toml").read_text())["project"]["site_url"]
        (archive / "404.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Page not found · Hubuum</title><h1>Page not found</h1>'
            f'<p>Open <a href="{html.escape(root_url, quote=True)}">Hubuum documentation</a> and select a version.</p></html>\n'
        )


class StylesheetMigration(HTMLParser):
    """Replace only the known local theme href, preserving every other byte."""

    def __init__(self, content: str, page: Path, stylesheet: Path):
        super().__init__(convert_charrefs=False)
        self.page = page
        self.stylesheet = stylesheet
        self.offsets = [0] + [match.end() for match in re.finditer("\n", content)]
        self.replacements = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag != "link" or "stylesheet" not in (attributes.get("rel") or "").lower().split():
            return
        href = urlsplit(attributes.get("href") or "")
        if href.scheme or href.netloc or not href.path or href.path.startswith("/"):
            return
        if (self.page.parent / href.path).resolve() != self.stylesheet:
            return
        raw = self.get_starttag_text()
        # Walk complete attributes so data-href or text inside another quoted
        # attribute cannot be mistaken for the real stylesheet URL.
        pattern = r'''([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?'''
        for match in re.finditer(pattern, raw):
            if match[1].lower() != "href":
                continue
            group = next((index for index in (2, 3, 4) if match[index] is not None), None)
            if group is not None:
                line, column = self.getpos()
                start = self.offsets[line - 1] + column
                self.replacements.append((start + match.start(group), start + match.end(group)))
            break

    def rewrite(self, content: str) -> str:
        for start, end in reversed(self.replacements):
            content = content[:start] + LIVE_STYLESHEET + content[end:]
        return content


def refresh_styles(archive: Path) -> None:
    """Migrate retained editions to the live theme without rebuilding content."""
    stylesheet = Path("assets/stylesheets/extra.css")
    manifest = archive / "versions.json"
    if manifest.exists():
        editions = [
            validate_version(entry["version"])
            for entry in json.loads(manifest.read_text())
        ]
        roots = [inside(archive, edition) for edition in editions]
    else:
        roots = [archive.resolve()]
    targets = [(root, inside(root, str(stylesheet))) for root in roots]
    content = (TOOLING / "theme" / stylesheet).read_bytes()
    for root, target in targets:
        # Cached older HTML can still use the legacy path's live CSS import.
        if target.is_file():
            target.write_bytes(content)
        for page in root.rglob("*.html"):
            inside(root, str(page.relative_to(root)))
            original = page.read_bytes().decode("utf-8")
            updated = StylesheetMigration(original, page, target).rewrite(original)
            if updated != original:
                page.write_bytes(updated.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--destination", type=Path, required=True)
    publish = commands.add_parser("assemble")
    publish.add_argument("--site", type=Path, required=True)
    publish.add_argument("--archive", type=Path, required=True)
    styles = commands.add_parser("refresh-styles")
    styles.add_argument("--archive", type=Path, required=True)
    for subparser in (prep, publish):
        subparser.add_argument("--version", required=True)
        subparser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.source, args.destination, args.version, args.source_sha)
        elif args.command == "assemble":
            assemble(args.site, args.archive, args.version, args.source_sha)
        else:
            refresh_styles(args.archive)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Documentation version error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
