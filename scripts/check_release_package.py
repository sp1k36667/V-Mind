"""Smoke-test an extracted release package, using only Python's standard library.

This checks a fresh isolated profile, not a real MCP host or every OS installer.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check(package):
    package = Path(package).resolve()
    binary = package / ("vmind.exe" if os.name == "nt" else "vmind")
    required = [binary, *(package / p for p in [
        "README.md", "README.de.md", "LICENSE", "CHANGELOG.md",
        "CONTRIBUTING.md", "AGENTS.md", "docs/operations.md", "prompts/start.de.md",
    ])]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Missing package file: {path}")
    links = 0
    for document in package.rglob("*.md"):
        for link in re.findall(r"\]\(([^\s)]+)", document.read_text(encoding="utf-8")):
            if link.startswith(("https:", "http:", "mailto:", "#")):
                continue
            target = document.parent / link.split("#", 1)[0]
            if not target.exists():
                raise RuntimeError(f"Broken file link in {document}: {link}")
            links += 1
    with tempfile.TemporaryDirectory(prefix="vmind-fresh-profile-") as folder:
        root = Path(folder)
        env = os.environ.copy()
        env.update(HOME=str(root), USERPROFILE=str(root), PATH="", VMIND_SCOPE="package-test")
        # Prevent inherited application settings from changing the test's semantics.
        for key in list(env):
            if key.startswith("VMIND_") and key != "VMIND_SCOPE":
                del env[key]
        calls = 0

        def run(*args, json_output=False):
            nonlocal calls
            cmd = [str(binary), *( ["--json"] if json_output else []), *map(str, args)]
            result = subprocess.run(cmd, cwd=root, env=env, text=True,
                                    encoding="utf-8", capture_output=True, timeout=30)
            if result.returncode:
                raise RuntimeError(f"Command failed: {args}: {result.stderr}")
            calls += 1
            return json.loads(result.stdout) if json_output else result.stdout

        run("--help")
        db = root / "fresh project.db"
        run("init", db)
        run("log", db, "goal", "Package restart check", "release package smoke test")
        run("task", db, "package", "in_progress", "Verify persistence", "release package smoke test")
        resumed = run("resume", db, json_output=True)
        require(resumed["goal"]["body"] == "Package restart check", "Goal was not persisted")
        require(resumed["tasks"][0]["task_key"] == "package", "Task was not persisted")
        require(run("doctor", db, json_output=True)["healthy"] is True, "Unhealthy fresh database")
        backup = root / "restored copy.db"
        require(run("backup", db, backup, json_output=True)["verified"] is True, "Backup not verified")
        require(run("doctor", backup, json_output=True)["healthy"] is True, "Unhealthy restored copy")
        restored = run("resume", backup, json_output=True)
        require(restored == resumed, "Backup does not preserve project state")
        require("Package restart check" in run("report", backup), "Report omits restored goal")
    print(f"Package passed: {links} local file links; {calls} separate process calls; "
          "isolated profile with empty PATH; restart, backup and restored report.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/check_release_package.py EXTRACTED_DIRECTORY")
    check(sys.argv[1])
