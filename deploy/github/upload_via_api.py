#!/usr/bin/env python3
"""Upload this project to GitHub without requiring git to be installed.

Required environment variable:
  GITHUB_TOKEN: a fine-grained token with Contents: Read and write permission
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
OWNER = os.getenv("GITHUB_OWNER", "kjysss2")
REPO = os.getenv("GITHUB_REPO", "fidelix-dashboard")
TOKEN = os.getenv("GITHUB_TOKEN")
API = "https://api.github.com"

INCLUDE = [
    "server.py",
    "refresh_once.py",
    "build_pages.py",
    "README.md",
    ".env.example",
    ".gitignore",
    "static",
    "data/seed.json",
    "deploy",
    ".github",
    "start.ps1",
    "start-public.ps1",
]

EXCLUDE_NAMES = {
    ".env",
    "cache.json",
    "__pycache__",
    "dist",
    "fidelix-dashboard-github-ready.tar.gz",
    "server.log",
    "server.err",
    "tunnel.log",
    "public-url.txt",
}


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN 환경변수가 필요합니다.")
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "fidelix-dashboard-uploader",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", "replace")
        if exc.code == 404:
            return 404, {}
        raise RuntimeError(f"GitHub API 오류 {exc.code}: {text}") from exc


def iter_files() -> list[Path]:
    result: list[Path] = []
    for item in INCLUDE:
        path = ROOT / item
        if not path.exists():
            continue
        if path.is_file():
            result.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and not any(part in EXCLUDE_NAMES for part in child.relative_to(ROOT).parts):
                result.append(child)
    return sorted(set(result))


def existing_sha(remote_path: str) -> str | None:
    quoted = urllib.parse.quote(remote_path.replace("\\", "/"))
    status, data = request("GET", f"/repos/{OWNER}/{REPO}/contents/{quoted}")
    if status == 404:
        return None
    if isinstance(data, dict):
        return data.get("sha")
    return None


def upload(path: Path) -> None:
    remote_path = path.relative_to(ROOT).as_posix()
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "message": f"Update {remote_path}",
        "content": content,
    }
    sha = existing_sha(remote_path)
    if sha:
        payload["sha"] = sha
    request("PUT", f"/repos/{OWNER}/{REPO}/contents/{urllib.parse.quote(remote_path)}", payload)
    print(f"uploaded {remote_path}")


def main() -> None:
    files = iter_files()
    print(f"Uploading {len(files)} files to {OWNER}/{REPO}")
    for path in files:
        upload(path)
    print("Done")


if __name__ == "__main__":
    main()
