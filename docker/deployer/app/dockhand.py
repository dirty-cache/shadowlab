"""
Author: Bart Sjerps
Last modified: 2026-11-25
Purpose: Dockhand REST client. Registers shadowlab compose stacks as git
stacks (source tracking) and runs deploy, stop, restart, and down there.
Docker itself is never called from this process.
"""

import json
import os
import time

import httpx

DOCKHAND_URL = os.environ.get("DOCKHAND_URL", "").rstrip("/")
DOCKHAND_TOKEN = os.environ.get("DOCKHAND_TOKEN", "").strip()
GIT_REPO_URL = os.environ.get("GIT_REPO_URL", "https://github.com/dirty-cache/shadowlab.git")
GIT_BRANCH = os.environ.get("GIT_BRANCH", "master")
GIT_CREDENTIAL_ID = os.environ.get("GIT_CREDENTIAL_ID", "").strip()
POLL_INTERVAL = 1.0


class DockhandError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def configured():
    return bool(DOCKHAND_URL)


def _headers():
    headers = {"Accept": "*/*", "User-Agent": "shadowlab-deployer"}
    if DOCKHAND_TOKEN:
        headers["Authorization"] = f"Bearer {DOCKHAND_TOKEN}"
    return headers


def _url(path):
    if not DOCKHAND_URL:
        raise DockhandError("DOCKHAND_URL is not set")
    return DOCKHAND_URL + path


def _error_detail(response):
    text = (response.text or "").strip()
    if not text:
        return response.reason_phrase or "request failed"
    try:
        body = response.json()
    except ValueError:
        return text.splitlines()[-1][:300]
    if isinstance(body, dict):
        for key in ("error", "detail", "message"):
            if body.get(key):
                return str(body[key])
    return text.splitlines()[-1][:300]


def request(method, path, params=None, json_body=None, timeout=60):
    """Call Dockhand. Raises DockhandError on transport or HTTP errors."""
    try:
        response = httpx.request(
            method, _url(path), params=params, json=json_body,
            headers=_headers(), timeout=timeout,
        )
    except httpx.HTTPError as e:
        raise DockhandError(f"Dockhand unreachable: {e}") from e
    if response.status_code >= 400:
        raise DockhandError(_error_detail(response), status=response.status_code)
    if not response.content:
        return None
    content_type = response.headers.get("content-type", "")
    if "json" in content_type or response.text.lstrip().startswith(("{", "[")):
        try:
            return response.json()
        except ValueError:
            return response.text
    return response.text


def _as_list(data, label):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in (label, "items", "data"):
            if isinstance(data.get(key), list):
                return data[key]
    raise DockhandError(f"unexpected {label} response from Dockhand")


def environments():
    """Normalized Dockhand environments: id, name, address, status, ok."""
    rows = _as_list(request("GET", "/api/environments"), "environments")
    found = []
    for row in rows:
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        status = str(row.get("status") or row.get("state") or "")
        lowered = status.lower()
        if lowered in ("offline", "error", "unreachable", "down", "disconnected"):
            ok = False
        elif row.get("online") is False or row.get("connected") is False:
            ok = False
        else:
            ok = True
        address = row.get("host") or row.get("url") or row.get("socketPath") or row.get("connectionType") or ""
        found.append({
            "id": str(row["id"]),
            "name": row.get("name") or str(row["id"]),
            "address": str(address),
            "status": status,
            "ok": ok,
        })
    return found


def get_environment(env_id):
    for env in environments():
        if env["id"] == str(env_id):
            return env
    return None


def stacks(env_id):
    return _as_list(request("GET", "/api/stacks", params={"env": env_id}), "stacks")


def sources(env_id):
    """Map stack name -> source record from GET /api/stacks/sources."""
    data = request("GET", "/api/stacks/sources", params={"env": env_id})
    if isinstance(data, list):
        mapped = {}
        for item in data:
            if isinstance(item, dict):
                key = item.get("stackName") or item.get("stack_name") or item.get("name")
                if key:
                    mapped[key] = item
        return mapped
    if isinstance(data, dict):
        if "error" in data and not any(isinstance(v, dict) for v in data.values()):
            raise DockhandError(str(data.get("error")))
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    return {}


def git_stacks(env_id):
    data = request("GET", "/api/git/stacks", params={"env": env_id})
    return _as_list(data, "stacks")


def _repo_name():
    text = GIT_REPO_URL.rstrip("/").rsplit("/", 1)[-1]
    return text[:-4] if text.endswith(".git") else text or "shadowlab"


def _norm_url(url):
    return (url or "").strip().rstrip("/").removesuffix(".git").lower()


def ensure_repository():
    """Return the Dockhand git repository id for GIT_REPO_URL, creating it if needed."""
    rows = _as_list(request("GET", "/api/git/repositories"), "repositories")
    target = _norm_url(GIT_REPO_URL)
    for row in rows:
        if _norm_url(row.get("url")) == target:
            return row.get("id")
    body = {"name": _repo_name(), "url": GIT_REPO_URL, "branch": GIT_BRANCH}
    if GIT_CREDENTIAL_ID:
        body["credentialId"] = int(GIT_CREDENTIAL_ID)
    created = request("POST", "/api/git/repositories", json_body=body)
    if not isinstance(created, dict) or created.get("id") is None:
        raise DockhandError("Dockhand did not return a repository id")
    return created["id"]


def _git_stack_id(env_id, name):
    for row in git_stacks(env_id):
        if row.get("stackName") == name or row.get("name") == name:
            return row.get("id")
    return None


def _line_text(entry):
    if not isinstance(entry, dict):
        return None
    data = entry.get("data")
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return None
    if data.get("line"):
        return str(data["line"])
    if entry.get("event") != "result":
        return None
    deploy_result = data.get("deployResult")
    if isinstance(deploy_result, dict) and deploy_result.get("error"):
        return "error: " + str(deploy_result["error"])
    if data.get("error"):
        return "error: " + str(data["error"])
    return None


def _result_ok(status, result):
    if status == "error":
        return False
    if not isinstance(result, dict):
        return status == "done"
    if result.get("success") is False:
        return False
    deploy_result = result.get("deployResult")
    if isinstance(deploy_result, dict) and deploy_result.get("success") is False:
        return False
    if result.get("error") and result.get("success") is not True and "deployResult" not in result:
        return False
    return True


def follow(payload, emit, job, timeout=60):
    """Stream a Dockhand job (or a finished JSON result) into emit(line). Returns 0 or 1."""
    if isinstance(payload, str):
        emit(payload)
        return 0
    if not isinstance(payload, dict):
        emit(str(payload))
        return 0
    job_id = payload.get("jobId")
    if not job_id:
        text = _line_text({"event": "result", "data": payload})
        if text:
            emit(text)
        return 0 if _result_ok("done", payload) else 1

    seen = 0
    deadline = time.time() + int(os.environ.get("DEPLOYER_JOB_TIMEOUT", "1800"))
    while True:
        if job.cancel:
            emit("cancelled")
            return 1
        if time.time() > deadline:
            emit("timed out waiting for Dockhand")
            return 1
        current = request("GET", f"/api/jobs/{job_id}", timeout=timeout)
        if not isinstance(current, dict):
            raise DockhandError("unexpected Dockhand job response")
        lines = current.get("lines") or []
        for entry in lines[seen:]:
            text = _line_text(entry)
            if text:
                emit(text)
        seen = len(lines)
        status = current.get("status")
        if status in ("done", "error"):
            result = current.get("result")
            if not _result_ok(status, result):
                if isinstance(result, dict) and result.get("error"):
                    emit("error: " + str(result["error"]))
                return 1
            return 0
        time.sleep(POLL_INTERVAL)


def deploy(project, env_id, emit, job):
    """Create the git stack when missing, then deploy it. Returns 0 or 1."""
    env_id_num = int(env_id)
    repository_id = ensure_repository()
    existing = _git_stack_id(env_id_num, project["name"])
    if existing is None:
        body = {
            "stackName": project["name"],
            "environmentId": env_id_num,
            "repositoryId": repository_id,
            "composePath": project["compose_path"],
            "branch": GIT_BRANCH,
            "deployNow": True,
        }
        try:
            payload = request("POST", "/api/git/stacks", json_body=body, timeout=60)
        except DockhandError as e:
            if e.status != 409:
                raise
            existing = _git_stack_id(env_id_num, project["name"])
            if existing is None:
                raise
        else:
            return follow(payload, emit, job)
    payload = request("POST", f"/api/git/stacks/{existing}/deploy", timeout=60)
    return follow(payload, emit, job)


def stack_action(name, env_id, action, emit, job, remove_volumes=False):
    """Stop, restart, or down a stack Dockhand already knows. Returns 0 or 1."""
    body = {"removeVolumes": True} if action == "down" and remove_volumes else None
    payload = request(
        "POST", f"/api/stacks/{name}/{action}",
        params={"env": env_id}, json_body=body, timeout=60,
    )
    return follow(payload, emit, job)


def _ports(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return [str(value)]
    ports = []
    for item in value:
        if isinstance(item, str):
            ports.append(item)
        elif isinstance(item, dict):
            published = item.get("public") or item.get("published") or item.get("PublishedPort")
            private = item.get("private") or item.get("target") or item.get("TargetPort")
            ports.append(str(published or private or item))
    return ports


def service_status(stack_row):
    """Map compose service name -> state from a GET /api/stacks row."""
    status = {}
    details = stack_row.get("containerDetails") or stack_row.get("containers") or []
    for container in details:
        if not isinstance(container, dict):
            continue
        key = container.get("service") or container.get("serviceName") or container.get("name")
        if not key:
            continue
        health = container.get("health") or ""
        status[key] = {
            "state": (container.get("state") or "").lower(),
            "status": container.get("status") or "",
            "health": health.lower() if isinstance(health, str) else "",
            "image": container.get("image") or "",
            "ports": _ports(container.get("ports")),
        }
    return status


def _container_matches(container, stack, service):
    names = {
        container.get("stack"), container.get("stackName"),
        container.get("composeProject"), container.get("project"),
    }
    if stack not in names:
        return False
    if not service:
        return True
    return service in {container.get("service"), container.get("serviceName"), container.get("name")}


def logs(env_id, stack, service="", tail=400):
    """Recent container logs for a stack, via Dockhand."""
    data = request("GET", "/api/containers", params={"env": env_id})
    try:
        containers = _as_list(data, "containers")
    except DockhandError:
        containers = []
    matched = [c for c in containers if isinstance(c, dict) and _container_matches(c, stack, service)]
    if not matched:
        for row in stacks(env_id):
            if row.get("name") != stack:
                continue
            for container in row.get("containerDetails") or []:
                if isinstance(container, dict) and (not service or service in {
                    container.get("service"), container.get("serviceName"), container.get("name"),
                }):
                    matched.append(container)
    if not matched:
        return "(no containers)"
    parts = []
    for container in matched:
        cid = container.get("id") or container.get("Id")
        label = container.get("name") or container.get("service") or stack
        if not cid:
            parts.append(f"--- {label} ---\n(no container id)")
            continue
        payload = request(
            "GET", f"/api/containers/{cid}/logs",
            params={"env": env_id, "tail": tail}, timeout=60,
        )
        if isinstance(payload, dict):
            text = payload.get("logs") or payload.get("log") or json.dumps(payload)
        else:
            text = payload or ""
        parts.append(f"--- {label} ---\n{str(text).strip()}")
    return "\n".join(parts).strip() or "(no logs)"
