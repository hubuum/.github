#!/usr/bin/env python3
"""Combine validated editions with this project's retained Pages archive."""

import json
from pathlib import Path
import subprocess
import sys

preview = Path("target/docs-preview")
manifest = preview / "versions.json"
editions = json.loads(manifest.read_text()) if manifest.exists() else [json.loads((preview / "build.json").read_text())]
for edition in editions:
    source = preview / edition["version"] if manifest.exists() else preview
    subprocess.run([
        sys.executable, str(Path(__file__).with_name("docs-versions.py")), "assemble",
        "--site", str(source), "--archive", "target/docs-published/site",
        "--version", edition["version"], "--source-sha", edition["source_sha"],
    ], check=True)

subprocess.run([
    sys.executable, str(Path(__file__).with_name("docs-versions.py")),
    "refresh-styles", "--archive", "target/docs-published/site",
], check=True)
