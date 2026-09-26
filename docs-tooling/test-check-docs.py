#!/usr/bin/env python3
"""Regression tests for documentation coverage and GitHub Pages path checking."""

import sys

if sys.version_info < (3, 11):
    sys.exit(
        "Hubuum tooling requires Python 3.11 or newer; found "
        + sys.version.split()[0]
        + ". Install Python 3.11+ and ensure python3 on PATH selects it."
    )

import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest


spec = importlib.util.spec_from_file_location("check_docs", Path(__file__).with_name("check-docs.py"))
assert spec and spec.loader
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)
version_spec = importlib.util.spec_from_file_location("docs_versions", Path(__file__).with_name("docs-versions.py"))
assert version_spec and version_spec.loader
versions = importlib.util.module_from_spec(version_spec)
version_spec.loader.exec_module(versions)


class DocumentationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        old_root = versions.ROOT
        versions.ROOT = self.root
        self.addCleanup(setattr, versions, "ROOT", old_root)
        self.write("zensical.toml", '''[project]
site_name = "Hubuum documentation"
site_url = "https://hubuum.github.io/hubuum/"
repo_url = "https://github.com/hubuum/hubuum"
edit_uri = "edit/main/docs/"
nav = [{Home = "index.md"}, {Queries = "querying.md"}]
''')

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def test_navigation_requires_every_document_once(self):
        self.write("docs/index.md", "# Home")
        self.write("docs/nested/guide.md", "# Guide")
        cases = [
            (["index.md"], "missing from navigation"),
            (["index.md", "nested/guide.md", "gone.md"], "does not exist"),
            (["index.md", "nested/guide.md", "index.md"], "more than once"),
        ]
        for nav, expected in cases:
            with self.subTest(nav=nav):
                errors = docs.check_navigation(self.root, {"docs_dir": "docs", "nav": nav})
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_navigation_supports_nested_sections_and_external_projects(self):
        self.write("docs/index.md", "# Home")
        self.write("docs/nested/guide.md", "# Guide")
        nav = [{"Home": "index.md"}, {"Guides": [{"Guide": "nested/guide.md"}]}, {"CLI": "https://example.org/cli"}]
        self.assertEqual(docs.check_navigation(self.root, {"docs_dir": "docs", "nav": nav}), [])

    def test_rendered_links_support_project_prefix_and_assets(self):
        self.write("index.html", '<a href="/hubuum/guide/#topic">Guide</a><a href="openapi.json">API</a>')
        self.write("openapi.json", "{}")
        self.write("guide/index.html", '<h1 id="topic">Guide</h1><a href="../">Home</a><img src="../logo.svg">')
        self.write("logo.svg", "<svg/>")
        self.assertEqual(docs.check_site(self.root, "https://hubuum.github.io/hubuum/"), [])

    def test_rendered_links_reject_broken_targets_and_base_paths(self):
        self.write("guide/index.html", '<h1 id="topic">Guide</h1>')
        cases = [
            ("gone/", "missing target"),
            ("guide/#gone", "missing anchor"),
            ("/guide/", "escapes site base path"),
            ("../outside.html", "escapes site directory"),
            ("missing.svg", "missing target"),
        ]
        for link, expected in cases:
            with self.subTest(link=link):
                self.write("index.html", f'<a href="{link}">Target</a>')
                errors = docs.check_site(self.root, "https://hubuum.github.io/hubuum/")
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_empty_build_fails(self):
        self.assertEqual(docs.check_site(self.root, "https://hubuum.github.io/hubuum/"), ["Built site is missing index.html"])

    def test_latest_release_is_default_even_when_main_is_updated(self):
        self.write("build/index.html", "release")
        archive = self.root / "archive"
        for version in ("v0.0.9", "v0.0.16", "main", "v0.0.10"):
            versions.assemble(self.root / "build", archive, version, "a" * 40)
        self.assertIn('url=v0.0.16/', (archive / "index.html").read_text())
        manifest = json.loads((archive / "versions.json").read_text())
        self.assertEqual([entry["version"] for entry in manifest], ["v0.0.16", "v0.0.10", "v0.0.9", "main"])

    def test_development_alone_does_not_become_public_default(self):
        self.write("build/index.html", "development")
        versions.assemble(self.root / "build", self.root / "archive", "main", "a" * 40)
        self.assertFalse((self.root / "archive/index.html").exists())

    def test_release_snapshot_is_immutable_across_renderer_changes(self):
        self.write("build/index.html", "original")
        versions.assemble(self.root / "build", self.root / "archive", "v0.0.16", "a" * 40)
        self.write("build/index.html", "different renderer")
        versions.assemble(self.root / "build", self.root / "archive", "v0.0.16", "a" * 40)
        self.assertEqual((self.root / "archive/v0.0.16/index.html").read_text(), "original")

    def test_retargeted_release_tag_is_rejected(self):
        self.write("build/index.html", "original")
        versions.assemble(self.root / "build", self.root / "archive", "v0.0.16", "a" * 40)
        with self.assertRaisesRegex(ValueError, "source commit changed"):
            versions.assemble(self.root / "build", self.root / "archive", "v0.0.16", "b" * 40)

    def test_shared_style_refresh_preserves_all_other_archived_bytes(self):
        self.write("build/index.html", "released prose")
        self.write("build/openapi.json", '{"release": "original"}')
        self.write("build/assets/stylesheets/extra.css", "old shared CSS")
        self.write("build/assets/stylesheets/renderer.css", "original renderer CSS")
        self.write("build/assets/javascripts/versions.js", "original script")
        self.write("build/build.json", '{"source_sha": "original"}')
        archive = self.root / "archive"
        for edition in ("v0.0.15", "v0.0.16", "main"):
            versions.assemble(self.root / "build", archive, edition, "a" * 40)
        # A directory not in the version manifest must not be refreshed.
        self.write("archive/untracked/assets/stylesheets/extra.css", "custom CSS")
        style_paths = {
            archive / edition / "assets/stylesheets/extra.css"
            for edition in ("v0.0.15", "v0.0.16", "main")
        }
        retained = {
            path.relative_to(archive): path.read_bytes()
            for path in archive.rglob("*")
            if path.is_file() and path not in style_paths
        }
        versions.refresh_styles(archive)
        self.assertEqual(retained, {
            path.relative_to(archive): path.read_bytes()
            for path in archive.rglob("*")
            if path.is_file() and path not in style_paths
        })
        shared_css = (versions.TOOLING / "theme/assets/stylesheets/extra.css").read_bytes()
        for path in style_paths:
            self.assertEqual(path.read_bytes(), shared_css)

    def test_shared_style_refresh_supports_unversioned_landing_site(self):
        self.write("archive/index.html", "ecosystem")
        self.write("archive/assets/stylesheets/extra.css", "old shared CSS")
        versions.refresh_styles(self.root / "archive")
        self.assertEqual((self.root / "archive/index.html").read_text(), "ecosystem")
        self.assertEqual(
            (self.root / "archive/assets/stylesheets/extra.css").read_bytes(),
            (versions.TOOLING / "theme/assets/stylesheets/extra.css").read_bytes(),
        )

    def test_shared_style_refresh_rejects_paths_outside_archive(self):
        archive = self.root / "archive"
        self.write("outside/assets/stylesheets/extra.css", "outside CSS")
        for edition in ("../outside", "v0.0.16"):
            with self.subTest(edition=edition):
                self.write("archive/versions.json", json.dumps([{"version": edition}]))
                if edition == "v0.0.16":
                    (archive / edition).symlink_to(self.root / "outside", target_is_directory=True)
                with self.assertRaises(ValueError):
                    versions.refresh_styles(archive)
                self.assertEqual((self.root / "outside/assets/stylesheets/extra.css").read_text(), "outside CSS")

    def test_retained_stylesheet_links_migrate_without_changing_content(self):
        archive = self.root / "archive"
        original = ("<!doctype html>\r\n<link data-href='keep' title='href=unchanged' rel='stylesheet' href='../assets/stylesheets/extra.css'>"
                    '<link rel="stylesheet" href="../assets/stylesheets/renderer.css">'
                    '<link rel="stylesheet" href="https://other.example/assets/stylesheets/extra.css">'
                    '<p>Unchanged prose: assets/stylesheets/extra.css</p>'
                    '<script>const text = "<link rel=stylesheet href=extra.css>";</script>')
        page = archive / "v0.0.16/guide/index.html"
        self.write("archive/versions.json", '[{"version": "v0.0.16"}]')
        self.write("archive/v0.0.16/guide/index.html", original)
        versions.refresh_styles(archive)
        expected = original.replace("href='../assets/stylesheets/extra.css'", f"href='{versions.LIVE_STYLESHEET}'")
        self.assertEqual(page.read_bytes(), expected.encode())
        versions.refresh_styles(archive)
        self.assertEqual(page.read_bytes(), expected.encode())

    def test_local_templates_overlay_shared_templates(self):
        self.write("docs/index.md", "# Home")
        self.write("overrides/home.html", "<!doctype html>Production homepage")
        with (self.root / "zensical.toml").open("a") as config:
            config.write('\n[tool.hubuum_docs]\ntheme_overrides = "overrides"\n')
        versions.prepare(self.root, self.root / "staged", "main", "a" * 40)
        self.assertEqual((self.root / "staged/docs-theme/overrides/home.html").read_text(),
                         "<!doctype html>Production homepage")
        self.assertTrue((self.root / "staged/docs-theme/overrides/main.html").is_file())
        project = tomllib.loads((self.root / "staged/zensical.toml").read_text())["project"]
        self.assertEqual(project["extra_css"], [versions.LIVE_STYLESHEET])

    def test_local_templates_use_tagged_source_not_current_checkout(self):
        self.write("old/docs/index.md", "# Old release")
        self.write("overrides/home.html", "Current only")
        with (self.root / "zensical.toml").open("a") as config:
            config.write('\n[tool.hubuum_docs]\ntheme_overrides = "overrides"\n')
        versions.prepare(self.root / "old", self.root / "staged", "v0.0.16", "a" * 40)
        self.assertFalse((self.root / "staged/docs-theme/overrides/home.html").exists())
        with self.assertRaisesRegex(ValueError, "overrides are missing"):
            versions.prepare(self.root / "old", self.root / "staged", "main", "a" * 40)

    def test_local_template_symlinks_cannot_escape_source(self):
        self.write("source/docs/index.md", "# Home")
        self.write("outside/home.html", "Outside")
        (self.root / "source/overrides").symlink_to(self.root / "outside", target_is_directory=True)
        with (self.root / "zensical.toml").open("a") as config:
            config.write('\n[tool.hubuum_docs]\ntheme_overrides = "overrides"\n')
        with self.assertRaisesRegex(ValueError, "escapes repository"):
            versions.prepare(self.root / "source", self.root / "staged", "main", "a" * 40)

    def test_main_can_be_replaced_without_changing_release_snapshots(self):
        self.write("build/index.html", "original")
        archive = self.root / "archive"
        versions.assemble(self.root / "build", archive, "v0.0.16", "a" * 40)
        versions.assemble(self.root / "build", archive, "main", "a" * 40)
        self.write("build/index.html", "updated")
        versions.assemble(self.root / "build", archive, "main", "b" * 40)
        self.assertEqual((archive / "main/index.html").read_text(), "updated")
        self.assertEqual((archive / "v0.0.16/index.html").read_text(), "original")

    def test_invalid_versions_cannot_escape_archive(self):
        for version in ("../escape", "v1.2", "v1.2.3-beta", "v01.2.3", "/tmp/escape"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                versions.validate_version(version)

    def test_legacy_release_uses_only_its_own_documents(self):
        self.write("source/docs/querying.md", "# Original release query guide\n")
        self.write("source/docs/retired.md", "# Retired guide\n")
        stage = self.root / "stage"
        versions.prepare(self.root / "source", stage, "v0.0.1", "a" * 40)
        project = tomllib.loads((stage / "zensical.toml").read_text())["project"]
        self.assertEqual(docs.check_navigation(stage, project), [])
        self.assertEqual((stage / "docs/querying.md").read_text(), "# Original release query guide\n")
        self.assertFalse((stage / "docs/credential_approvals.md").exists())
        self.assertEqual(project["site_url"], "https://hubuum.github.io/hubuum/v0.0.1/")

    def test_imported_readme_links_to_staged_guides_and_preserves_edit_origin(self):
        with (self.root / "zensical.toml").open("a") as config:
            config.write('\n[tool.hubuum_docs.source_files]\n"README.md" = "getting-started.md"\n')
        self.write("source/docs/querying.md", "# Querying\n[Overview](../README.md)\n")
        self.write("source/README.md", "# Client\n[Queries](docs/querying.md)\n")
        stage = self.root / "stage"
        versions.prepare(self.root / "source", stage, "main", "a" * 40)
        readme = (stage / "docs/getting-started.md").read_text()
        self.assertIn('[Queries](querying.md)', readme)
        self.assertIn('edit_path: "../README.md"', readme)
        self.assertIn('[Overview](getting-started.md)', (stage / "docs/querying.md").read_text())

    def test_org_home_is_unversioned_and_has_no_release_selector(self):
        with (self.root / "zensical.toml").open("a") as config:
            config.write('\n[tool.hubuum_docs]\nversioned = false\n')
        self.write("source/docs/index.md", "# Ecosystem\n")
        stage = self.root / "stage"
        versions.prepare(self.root / "source", stage, "main", "a" * 40)
        project = tomllib.loads((stage / "zensical.toml").read_text())["project"]
        self.assertFalse(project["extra"]["docs_versioned"])
        self.assertEqual(project["site_url"], "https://hubuum.github.io/hubuum/")
        self.write("build/index.html", "ecosystem")
        versions.assemble(self.root / "build", self.root / "archive", "main", "a" * 40)
        self.assertEqual((self.root / "archive/index.html").read_text(), "ecosystem")
        self.assertFalse((self.root / "archive/versions.json").exists())

    def test_python_api_sources_come_from_selected_source(self):
        with (self.root / "zensical.toml").open("a") as config:
            config.write('\n[tool.hubuum_docs]\nsource_trees = ["src"]\n')
        self.write("source/docs/index.md", "# Python client\n")
        self.write("source/src/client.py", "class OriginalClient: pass\n")
        stage = self.root / "stage"
        versions.prepare(self.root / "source", stage, "v1.0.0", "a" * 40)
        self.assertEqual((stage / "src/client.py").read_text(), "class OriginalClient: pass\n")


if __name__ == "__main__":
    unittest.main()
