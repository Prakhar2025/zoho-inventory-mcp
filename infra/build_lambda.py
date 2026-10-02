"""Build the Lambda deployment bundle for the console backend.

Produces infra/.aws-lambda-build/bundle.zip containing:
  - third-party deps (fastapi, uvicorn, httpx, mcp, pydantic, strands, ...)
    compiled for manylinux2014 x86_64 / Python 3.12
  - our packages: zoho_inventory_mcp/, agent/runner.py, console/ (backend,

 boto3/botocore are deleted from the bundle because the Lambda runtime ships
 them (learned from the antares build).

    .venv/Scripts/python infra/build_lambda.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

INFRA_DIR = Path(__file__).resolve().parent
REPO_ROOT = INFRA_DIR.parent
BUILD_DIR = INFRA_DIR / ".aws-lambda-build"
ZIP_PATH = BUILD_DIR / "bundle.zip"

# Lambda runtime provides these; bundling our own copies risks version drift.
RUNTIME_PROVIDED = ("boto3", "botocore")

PACKAGES = [
    "fastapi",
    "uvicorn",
    "httpx",
    "mcp",
    "pydantic",
    "pydantic-settings",
    "strands-agents",
    "mangum",
]


def build(fresh: bool = True) -> Path:
    if ZIP_PATH.exists() and not fresh:
        print(f"reusing existing bundle: {ZIP_PATH} ({ZIP_PATH.stat().st_size / 1e6:.1f} MB)")
        return ZIP_PATH
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    print("installing dependencies for manylinux2014 x86_64 / py3.12 ...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--platform",
            "manylinux2014_x86_64",
            "--python-version",
            "3.12",
            "--only-binary=:all:",
            "--target",
            str(BUILD_DIR / "pkg"),
            *PACKAGES,
        ],
        check=True,
    )
    pkg = BUILD_DIR / "pkg"
    for name in RUNTIME_PROVIDED:
        for candidate in pkg.glob(name + "*"):
            shutil.rmtree(candidate) if candidate.is_dir() else candidate.unlink()

    # Our code at the zip root so both the parent process and the MCP child
    # process resolve them (child cwd is /var/task).
    shutil.copytree(REPO_ROOT / "src" / "zoho_inventory_mcp", BUILD_DIR / "bundle" / "zoho_inventory_mcp")
    agent_dir = BUILD_DIR / "bundle" / "agent"
    agent_dir.mkdir()
    shutil.copy2(REPO_ROOT / "agent" / "runner.py", agent_dir / "runner.py")
    console_dir = BUILD_DIR / "bundle" / "console"
    console_dir.mkdir()
    shutil.copy2(REPO_ROOT / "console" / "backend.py", console_dir / "backend.py")
    shutil.copy2(REPO_ROOT / "console" / "events.py", console_dir / "events.py")
    shutil.copy2(REPO_ROOT / "console" / "handler.py", console_dir / "handler.py")
    shutil.copytree(REPO_ROOT / "console" / "static", console_dir / "static")

    bundle_root = BUILD_DIR / "bundle"
    # Dependencies go at the zip root: /var/task is the child process's cwd and
    # the parent's sys.path entry, so root-level imports resolve everywhere.
    shutil.copytree(pkg, bundle_root, dirs_exist_ok=True)
    shutil.rmtree(pkg)

    print("zipping bundle ...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(bundle_root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(bundle_root).as_posix())

    print(f"bundle ready: {ZIP_PATH} ({ZIP_PATH.stat().st_size / 1e6:.1f} MB)")
    return ZIP_PATH


if __name__ == "__main__":
    build()
