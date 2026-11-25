"""
Author: Bart Sjerps
Last modified: 2026-11-25
Purpose: Shadow Lab Deployer — web UI that registers this repo's compose
stacks in Dockhand as git-tracked stacks and deploys them through Dockhand.

Run: uvicorn main:app --host 0.0.0.0 --port 8080
Single worker is required (jobs live in memory).
"""

import os

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import catalog
import dockhand
from jobs import JobManager

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
VERSION = "0.2.0"
IMAGE = "ghcr.io/dirty-cache/shadowlab/deployer"

TOKEN = os.environ.get("DEPLOYER_TOKEN", "").strip()

app = FastAPI(title="Shadow Lab Deployer", version=VERSION, docs_url=None, redoc_url=None)
jobs = JobManager()


def require_token(request: Request):
    if not TOKEN:
        return
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.headers.get("x-deployer-token", "")
    if token != TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


api = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


class ActionIn(BaseModel):
    env_id: str
    volumes: bool = False


def _dockhand_http(exc):
    status = 502 if not exc.status or exc.status >= 500 else exc.status
    if exc.status == 404:
        status = 404
    raise HTTPException(status_code=status, detail=str(exc))


def _environment(env_id):
    try:
        env = dockhand.get_environment(env_id)
    except dockhand.DockhandError as e:
        _dockhand_http(e)
    if env is None:
        raise HTTPException(status_code=404, detail="unknown environment")
    return env


def _project(name):
    try:
        project = catalog.get_project(name)
    except catalog.CatalogError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if project is None:
        raise HTTPException(status_code=404, detail="unknown project")
    return project


def _require_mutable(project):
    if project["protected"]:
        raise HTTPException(status_code=400, detail="this stack is not deployed from here")


def _start(name, env, action, description, run):
    if jobs.running_for(name, env["id"]):
        raise HTTPException(status_code=409, detail="a job for this project is already running")
    job = jobs.start(name, env["id"], env["name"], action, description, run)
    return {"job": job.to_dict()}


def _source_view(name, source, git_row, compose_path):
    source = source or {}
    git_row = git_row or {}
    repo = source.get("repository") or {}
    if not isinstance(repo, dict):
        repo = {}
    return {
        "source_type": source.get("sourceType") or source.get("source_type") or ("git" if git_row else None),
        "repository_name": repo.get("name") or git_row.get("repositoryName") or "",
        "repository_url": repo.get("url") or git_row.get("repositoryUrl") or "",
        "branch": git_row.get("branch") or repo.get("branch") or "",
        "compose_path": source.get("composePath") or compose_path,
        "sync_status": git_row.get("syncStatus") or repo.get("syncStatus") or repo.get("repository_sync_status") or "",
        "git_stack_id": git_row.get("id"),
    }


@api.get("/health")
def health():
    return {
        "ok": True,
        "version": VERSION,
        "auth": bool(TOKEN),
        "dockhand": dockhand.configured(),
        "repo": catalog.GIT_REPO_URL,
        "branch": catalog.GIT_BRANCH,
        "image": IMAGE,
    }


@api.get("/environments")
def list_environments():
    try:
        return {"environments": dockhand.environments()}
    except dockhand.DockhandError as e:
        _dockhand_http(e)


@api.get("/overview")
def overview(env: str):
    environment = _environment(env)
    dockhand_error = None
    runtime = {}
    source_map = {}
    git_by_name = {}
    try:
        for row in dockhand.stacks(environment["id"]):
            if isinstance(row, dict) and row.get("name"):
                runtime[row["name"]] = row
        source_map = dockhand.sources(environment["id"])
        for row in dockhand.git_stacks(environment["id"]):
            key = row.get("stackName") or row.get("name")
            if key:
                git_by_name[key] = row
    except dockhand.DockhandError as e:
        dockhand_error = str(e)

    catalog_error = None
    try:
        defined = catalog.list_projects()
    except catalog.CatalogError as e:
        defined = []
        catalog_error = str(e)

    projects = []
    for project in defined:
        row = runtime.get(project["name"])
        entry = {
            "name": project["name"],
            "description": project["description"],
            "compose_path": project["compose_path"],
            "services": project["services"],
            "protected": project["protected"],
            "source": _source_view(
                project["name"], source_map.get(project["name"]),
                git_by_name.get(project["name"]), project["compose_path"],
            ),
            "status": dockhand.service_status(row) if row else {},
            "stack_status": (row or {}).get("status") or "",
            "status_error": dockhand_error,
        }
        projects.append(entry)
    return {
        "environment": environment,
        "dockhand_ok": dockhand_error is None and environment["ok"],
        "dockhand_error": dockhand_error,
        "catalog_error": catalog_error,
        "repo": catalog.GIT_REPO_URL,
        "branch": catalog.GIT_BRANCH,
        "projects": projects,
    }


@api.get("/projects/{name}/file")
def project_file(name: str):
    project = _project(name)
    return PlainTextResponse(project["compose"])


@api.get("/projects/{name}/logs")
def project_logs(name: str, env: str, service: str = "", tail: int = 400):
    _project(name)
    environment = _environment(env)
    try:
        text = dockhand.logs(environment["id"], name, service=service, tail=max(1, min(tail, 2000)))
    except dockhand.DockhandError as e:
        _dockhand_http(e)
    return PlainTextResponse(text or "(no logs)")


@api.post("/projects/{name}/deploy")
def deploy(name: str, body: ActionIn):
    environment = _environment(body.env_id)
    project = _project(name)
    _require_mutable(project)

    def run(job):
        return dockhand.deploy(project, environment["id"], job.output.append, job)

    return _start(name, environment, "deploy", f"deploy {name} on {environment['name']}", run)


@api.post("/projects/{name}/stop")
def stop(name: str, body: ActionIn):
    environment = _environment(body.env_id)
    project = _project(name)
    _require_mutable(project)
    action = "down" if body.volumes else "stop"
    kind = "stop + remove volumes" if body.volumes else "stop"

    def run(job):
        return dockhand.stack_action(
            name, environment["id"], action, job.output.append, job, remove_volumes=body.volumes,
        )

    return _start(name, environment, "stop", f"{kind} {name} on {environment['name']}", run)


@api.post("/projects/{name}/restart")
def restart(name: str, body: ActionIn):
    environment = _environment(body.env_id)
    project = _project(name)
    _require_mutable(project)

    def run(job):
        return dockhand.stack_action(name, environment["id"], "restart", job.output.append, job)

    return _start(name, environment, "restart", f"restart {name} on {environment['name']}", run)


@api.get("/jobs/{job_id}")
def job_status(job_id: str, tail: int = 400):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return {"job": job.to_dict(tail=tail)}


app.include_router(api)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
