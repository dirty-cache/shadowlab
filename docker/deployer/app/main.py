"""
Author: Bart Sjerps
Last modified: 2026-11-18
Purpose: Shadow Lab Deployer — web UI backend for deploying Docker Compose
stacks from the repo's docker/ directory to one or more configured Docker
hosts.

Run: uvicorn main:app --host 0.0.0.0 --port 8080
Single worker is required (jobs live in memory).
"""

import os

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import composeops
from store import HostsStore, normalize_address

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
VERSION = "0.1.0"

TOKEN = os.environ.get("DEPLOYER_TOKEN", "").strip()

app = FastAPI(title="Shadow Lab Deployer", version=VERSION, docs_url=None, redoc_url=None)
store = HostsStore()
jobs = composeops.JobManager()


def require_token(request: Request):
    if not TOKEN:
        return
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.headers.get("x-deployer-token", "")
    if token != TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


api = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


# ---------- models ----------

class HostIn(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    address: str = ""
    description: str = ""


class ActionIn(BaseModel):
    host_id: str
    pull: bool = False
    build: bool = False
    volumes: bool = False


# ---------- helpers ----------

def _host(host_id: str):
    host = store.get(host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="unknown host")
    return host


def _project(name: str):
    try:
        path = composeops.project_paths(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    cf = composeops.compose_file(path)
    if cf is None:
        raise HTTPException(status_code=404, detail="not a compose project")
    info = next((p for p in composeops.list_projects() if p["name"] == name), None)
    return path, cf, info


def _start_job(name: str, host: dict, action: str, argv: list, cwd: str, description: str):
    if jobs.running_for(name, host["id"]):
        raise HTTPException(status_code=409, detail="a job for this project is already running")
    job = jobs.start(name, host["id"], host, action, argv, cwd, description)
    return {"job": job.to_dict()}


# ---------- health ----------

@api.get("/health")
def health():
    return {
        "ok": True,
        "version": VERSION,
        "auth": bool(TOKEN),
        "compose": composeops.cli_version(),
        "projects_dir": composeops.PROJECTS_DIR,
    }


# ---------- hosts ----------

@api.get("/hosts")
def list_hosts():
    return {"hosts": store.list()}


@api.post("/hosts", status_code=201)
def add_host(body: HostIn):
    try:
        return {"host": store.add(body.name, body.address, body.description)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.put("/hosts/{host_id}")
def update_host(host_id: str, body: HostIn):
    try:
        updated = store.update(host_id, body.name, body.address, body.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if updated is None:
        raise HTTPException(status_code=404, detail="unknown host")
    return {"host": updated}


@api.delete("/hosts/{host_id}")
def delete_host(host_id: str):
    try:
        removed = store.remove(host_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if removed is None:
        raise HTTPException(status_code=404, detail="unknown host")
    return {"ok": True}


class HostTestIn(BaseModel):
    address: str = ""


@api.post("/hosts/test")
def test_host(body: HostTestIn):
    """Ping a daemon address without saving it (used by the add-host dialog)."""
    try:
        address = normalize_address(body.address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return composeops.daemon_info({"address": address})


@api.get("/hosts/{host_id}/info")
def host_info(host_id: str):
    return composeops.daemon_info(_host(host_id))


# ---------- overview ----------

@api.get("/overview")
def overview(host_id: str):
    host = _host(host_id)
    info = composeops.daemon_info(host)
    projects = []
    for p in composeops.list_projects():
        entry = dict(p)
        entry["status"] = {}
        entry["status_error"] = None
        if info.get("ok"):
            try:
                entry["status"] = composeops.project_status(host, p["name"])
            except Exception as e:
                entry["status_error"] = str(e)
        projects.append(entry)
    return {"host": host, "info": info, "projects": projects}


# ---------- projects ----------

@api.get("/projects/{name}/file")
def project_file(name: str):
    _, cf, _ = _project(name)
    with open(cf) as f:
        return PlainTextResponse(f.read())


@api.get("/projects/{name}/logs")
def project_logs(name: str, host_id: str, service: str = "", tail: int = 400):
    host = _host(host_id)
    try:
        base, _ = composeops.compose_base_argv(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="not a compose project")
    argv = base + ["logs", "--tail", str(max(1, min(tail, 2000))), "--no-color"]
    if service:
        argv += ["--service", service]
    try:
        p = composeops.run_cli(host, argv, timeout=60)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    text = (p.stdout or "") + (p.stderr or "")
    return PlainTextResponse(text.strip() or "(no logs)")


# ---------- actions ----------

@api.post("/projects/{name}/deploy")
def deploy(name: str, body: ActionIn):
    host = _host(body.host_id)
    path, cf, info = _project(name)
    if body.build and not (info and info["has_build"]):
        raise HTTPException(status_code=400, detail="this project has no build steps")
    argv = ["compose", "-f", cf, "up", "-d", "--wait", "--remove-orphans"]
    if body.pull:
        argv += ["--pull", "always"]
    if body.build:
        argv += ["--build"]
    kind = "deploy" + (" + pull" if body.pull else "") + (" + build" if body.build else "")
    return _start_job(name, host, "deploy", argv, path, f"{kind} {name} on {host['name']}")


@api.post("/projects/{name}/stop")
def stop(name: str, body: ActionIn):
    host = _host(body.host_id)
    path, cf, _ = _project(name)
    argv = ["compose", "-f", cf, "down", "--remove-orphans"]
    if body.volumes:
        argv += ["--volumes"]
    kind = "stop" + (" + remove volumes" if body.volumes else "")
    return _start_job(name, host, "stop", argv, path, f"{kind} {name} on {host['name']}")


@api.post("/projects/{name}/restart")
def restart(name: str, body: ActionIn):
    host = _host(body.host_id)
    path, cf, _ = _project(name)
    argv = ["compose", "-f", cf, "restart"]
    return _start_job(name, host, "restart", argv, path, f"restart {name} on {host['name']}")


# ---------- jobs ----------

@api.get("/jobs/{job_id}")
def job_status(job_id: str, tail: int = 400):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return {"job": job.to_dict(tail=tail)}


# ---------- static ----------

app.include_router(api)  # after all @api routes are registered
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
