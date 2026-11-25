"""
Author: Bart Sjerps
Last modified: 2026-11-25
Purpose: Discover compose stacks in the shadowlab GitHub repository.
The deployer does not mount a checkout; the catalog comes from the GitHub API.
"""

import os
import re
import threading
import time

import httpx
import yaml

GIT_REPO_URL = os.environ.get("GIT_REPO_URL", "https://github.com/dirty-cache/shadowlab.git")
GIT_BRANCH = os.environ.get("GIT_BRANCH", "master")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
CACHE_TTL = int(os.environ.get("DEPLOYER_CATALOG_TTL", "60"))

COMPOSE_FILES = ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml")
# Dockhand must not be asked to redeploy itself.
PROTECTED = {"dockhand"}

_lock = threading.Lock()
_cache = {"at": 0.0, "projects": None}


class CatalogError(Exception):
    pass


def parse_github_repo(url):
    """Return (owner, repo) for a github.com clone URL."""
    text = re.sub(r"\.git$", "", (url or "").strip().rstrip("/"))
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+)$", text)
    if not match:
        raise CatalogError(f"GIT_REPO_URL is not a github.com repository: {url}")
    return match.group(1), match.group(2)


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "shadowlab-deployer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _request(client, method, url, accept=None):
    headers = _headers()
    if accept:
        headers["Accept"] = accept
    try:
        response = client.request(method, url, headers=headers)
    except httpx.HTTPError as e:
        raise CatalogError(f"GitHub request failed: {e}") from e
    if response.status_code == 404:
        hint = " Set GITHUB_TOKEN if the repository is private." if not GITHUB_TOKEN else ""
        raise CatalogError(f"GitHub returned 404 for {url}.{hint}")
    if response.status_code >= 400:
        detail = response.text.strip().splitlines()[-1] if response.text.strip() else response.reason_phrase
        raise CatalogError(f"GitHub {response.status_code}: {detail}")
    return response


def _compose_services(text):
    services = []
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return services
    for name, svc in (doc.get("services") or {}).items():
        svc = svc or {}
        image = svc.get("image")
        if not image and svc.get("build"):
            image = "build"
        services.append({
            "name": name,
            "image": image or "",
            "ports": [str(p) for p in (svc.get("ports") or [])],
        })
    return services


def _readme_blurb(text):
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line.lstrip("#").strip()[:160]
    return ""


def _load(client):
    owner, repo = parse_github_repo(GIT_REPO_URL)
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{GIT_BRANCH}?recursive=1"
    tree = _request(client, "GET", tree_url).json()
    if tree.get("truncated"):
        raise CatalogError("GitHub tree listing was truncated; the docker/ catalog is incomplete")
    paths = {item.get("path") for item in tree.get("tree") or [] if item.get("type") == "blob"}

    stacks = {}
    for path in sorted(paths):
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "docker":
            continue
        name, filename = parts[1], parts[2]
        if filename not in COMPOSE_FILES:
            continue
        current = stacks.get(name)
        if current is None or COMPOSE_FILES.index(filename) < COMPOSE_FILES.index(current):
            stacks[name] = filename

    projects = []
    for name in sorted(stacks):
        compose_path = f"docker/{name}/{stacks[name]}"
        raw_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{compose_path}?ref={GIT_BRANCH}"
        compose = _request(client, "GET", raw_url, accept="application/vnd.github.raw").text
        readme = ""
        readme_path = f"docker/{name}/README.md"
        if readme_path in paths:
            readme_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{readme_path}?ref={GIT_BRANCH}"
            readme = _request(client, "GET", readme_url, accept="application/vnd.github.raw").text
        projects.append({
            "name": name,
            "compose_path": compose_path,
            "compose": compose,
            "description": _readme_blurb(readme),
            "services": _compose_services(compose),
            "protected": name in PROTECTED,
        })
    return projects


def list_projects():
    """Cached compose stacks on GIT_BRANCH. Raises CatalogError."""
    now = time.time()
    with _lock:
        if _cache["projects"] is not None and now - _cache["at"] < CACHE_TTL:
            return _cache["projects"]
    with httpx.Client(timeout=30.0) as client:
        projects = _load(client)
    with _lock:
        _cache["at"] = time.time()
        _cache["projects"] = projects
    return projects


def get_project(name):
    for project in list_projects():
        if project["name"] == name:
            return project
    return None
