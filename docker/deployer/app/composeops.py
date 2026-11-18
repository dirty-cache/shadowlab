"""
Author: Bart Sjerps
Last modified: 2026-11-18
Purpose: Docker CLI operations for the Shadow Lab Deployer — project discovery,
per-host status, daemon info and long-running deploy/stop/restart jobs.

All commands run the local `docker` / `docker compose` CLI with DOCKER_HOST
pointed at the selected host, so compose files are read from the mounted
projects directory while containers run on the chosen daemon.
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid
from collections import deque

import yaml

PROJECTS_DIR = os.environ.get("DEPLOYER_PROJECTS_DIR", "/projects")
# Directory with the installed copies (bin/install-container convention:
# /opt/docker/<name>). When a stack is installed there, compose runs from
# that copy so per-host .env files and `env_file:` entries resolve the same
# way a manual `cd /opt/docker/<name> && docker compose up` would.
INSTALLED_DIR = os.environ.get("DEPLOYER_INSTALLED_DIR", "/installed")
COMPOSE_FILES = ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml")
JOB_TIMEOUT = int(os.environ.get("DEPLOYER_JOB_TIMEOUT", "1800"))
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

_cli_version = None


def cli_version():
    global _cli_version
    if _cli_version is None:
        try:
            p = subprocess.run(["docker", "compose", "version", "--short"],
                               capture_output=True, text=True, timeout=10)
            _cli_version = p.stdout.strip() or "unknown"
        except Exception:
            _cli_version = "unknown"
    return _cli_version


def docker_env(host):
    env = dict(os.environ)
    env["DOCKER_HOST"] = host.get("address") or "unix:///var/run/docker.sock"
    return env


def run_cli(host, args, timeout=60):
    """Run a docker CLI command against the given host. Raises TimeoutExpired."""
    return subprocess.run(
        ["docker"] + args,
        env=docker_env(host),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def daemon_info(host):
    """Ping the daemon and return version/summary info, or ok=False."""
    try:
        p = run_cli(host, ["version", "-f", "{{json .Server}}"], timeout=15)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timed out"}
    if p.returncode != 0:
        err = (p.stderr or p.stdout).strip()
        return {"ok": False, "error": err.splitlines()[-1] if err else "daemon unreachable"}
    try:
        info = json.loads(p.stdout.strip())
    except (ValueError, TypeError):
        return {"ok": False, "error": "unexpected response from daemon"}
    out = {
        "ok": True,
        "version": info.get("Version"),
        "os": "/".join(filter(None, [info.get("Os"), info.get("Arch")])),
        "name": info.get("Name"),
        "containers": None,
        "containers_running": None,
        "images": None,
    }
    # `docker version` dropped the container counts in recent engines;
    # fetch them from `docker info` instead (best effort).
    try:
        pi = run_cli(host, ["info", "-f", "{{.Containers}} {{.ContainersRunning}} {{.Images}}"],
                     timeout=15)
        if pi.returncode == 0:
            parts = (pi.stdout or "").strip().split()
            if len(parts) == 3:
                for key, val in zip(("containers", "containers_running", "images"), parts):
                    out[key] = int(val)
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return out


def _safe_join(root, name):
    """Join root/name, rejecting traversal outside root. None if invalid."""
    if not name or not NAME_RE.match(name):
        return None
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, name))
    if os.path.dirname(path) != root or not os.path.isdir(path):
        return None
    return path


def project_paths(name):
    """Locate a stack's compose directory.

    Prefers the installed copy (INSTALLED_DIR/<name>) over the repo
    checkout (PROJECTS_DIR/<name>), so env resolution matches the
    install-container convention; falls back to the checkout for stacks
    added to the repo but not installed yet.
    """
    checkout = _safe_join(PROJECTS_DIR, name)
    installed = None
    if INSTALLED_DIR:
        iroot = os.path.realpath(INSTALLED_DIR)
        if iroot != os.path.realpath(PROJECTS_DIR):
            cand = _safe_join(INSTALLED_DIR, name)
            if cand and compose_file(cand):
                installed = cand
    if installed:
        return installed
    if checkout:
        return checkout
    raise ValueError("unknown project")


def compose_file(path):
    for f in COMPOSE_FILES:
        p = os.path.join(path, f)
        if os.path.isfile(p):
            return p
    return None


def _describe(name, path, cf, in_repo=True):
    services = []
    has_build = False
    try:
        with open(cf) as f:
            doc = yaml.safe_load(f) or {}
        for sname, svc in (doc.get("services") or {}).items():
            svc = svc or {}
            image = svc.get("image")
            if not image and svc.get("build"):
                image = "build"
            services.append({
                "name": sname,
                "image": image,
                "ports": [str(p) for p in (svc.get("ports") or [])],
                "profiles": svc.get("profiles") or [],
            })
            if svc.get("build"):
                has_build = True
    except Exception:
        pass  # unreadable compose file: project still listed, services empty

    description = ""
    readme = os.path.join(path, "README.md")
    if os.path.isfile(readme):
        try:
            with open(readme, errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        description = line.lstrip("#").strip()[:160]
                        break
        except OSError:
            pass

    return {
        "name": name,
        "compose_file": os.path.basename(cf),
        "description": description,
        "services": services,
        "has_build": has_build,
        "in_repo": in_repo,
        "has_env": os.path.isfile(os.path.join(path, ".env")),
        "has_env_example": in_repo and os.path.isfile(os.path.join(path, ".env.example")),
    }


def _scan_root(root):
    found = {}
    root = os.path.realpath(root)
    if not os.path.isdir(root):
        return found
    for entry in sorted(os.listdir(root)):
        path = os.path.join(root, entry)
        if not os.path.isdir(path):
            continue
        cf = compose_file(path)
        if cf is None:
            continue
        found[entry] = (path, cf)
    return found


def list_projects():
    """Known stacks: the repo checkout (PROJECTS_DIR), plus installed copies
    of stacks that are no longer in the repo. When a stack exists in both,
    the installed copy wins — that is where compose runs from, so the env
    flags reflect the directory that will actually be used."""
    repo = _scan_root(PROJECTS_DIR)
    installed = {}
    if INSTALLED_DIR and os.path.realpath(INSTALLED_DIR) != os.path.realpath(PROJECTS_DIR):
        installed = _scan_root(INSTALLED_DIR)
    projects = []
    for name in sorted(set(repo) | set(installed)):
        in_repo = name in repo
        path, cf = installed[name] if name in installed else repo[name]
        desc = _describe(name, path, cf, in_repo=in_repo)
        try:
            run_path = project_paths(name)
            desc["has_env"] = os.path.isfile(os.path.join(run_path, ".env"))
        except ValueError:
            pass
        projects.append(desc)
    return projects


def _parse_ps_output(text):
    """Compose v5 prints one JSON object per line; older versions a single
    array. Handle both."""
    text = (text or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except ValueError:
            pass
    containers = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            containers.append(json.loads(line))
        except ValueError:
            continue
    return containers


def _container_ports(c):
    """Compose v5 Publishers: URL is the bind address ("0.0.0.0", "::"),
    ports come from PublishedPort/TargetPort/Protocol."""
    ports = []
    seen = set()
    for pub in c.get("Publishers") or []:
        proto = pub.get("Protocol") or "tcp"
        pub_port = pub.get("PublishedPort")
        bind = pub.get("URL") or ""
        if pub_port:
            if bind not in ("", "0.0.0.0", "::"):
                entry = f"{bind}:{pub_port}/{proto}"
            else:
                entry = f"{pub_port}/{proto}"
        else:
            entry = f"{pub.get('TargetPort') or pub.get('PrivatePort')}/{proto} (internal)"
        if entry not in seen:
            seen.add(entry)
            ports.append(entry)
    return ports


def project_status(host, name):
    """Run `docker compose ps --format json` on the host; map service -> state."""
    base, _ = compose_base_argv(name)
    p = run_cli(host, base + ["ps", "--format", "json"], timeout=30)
    if p.returncode != 0:
        err = (p.stderr or p.stdout).strip()
        raise RuntimeError(err.splitlines()[-1] if err else "docker compose ps failed")
    status = {}
    for c in _parse_ps_output(p.stdout):
        svc = c.get("Service")
        status[svc] = {
            "state": c.get("State"),
            "status": c.get("Status") or "",
            "health": c.get("Health") or "",
            "image": c.get("Image") or "",
            "ports": _container_ports(c),
        }
    return status


def compose_base_argv(name):
    """Base compose CLI args for a stack.

    `--project-directory` points at the directory that compose will run
    from, so `env_file:` entries and .env interpolation resolve the same
    way they do for a manual `cd /opt/docker/<name> && docker compose up`.
    """
    path = project_paths(name)
    cf = compose_file(path)
    if cf is None:
        raise FileNotFoundError(name)
    return ["compose", "-f", cf, "--project-directory", path], path


def compose_argv(name, extra):
    """Compose CLI args for a project: ['compose', '-f', <file>, ..., ...extra]."""
    base, path = compose_base_argv(name)
    return base + extra, path


class Job:
    def __init__(self, project, host_id, host_name, host_address, action, description, argv, cwd):
        self.id = uuid.uuid4().hex[:12]
        self.project = project
        self.host_id = host_id
        self.host_name = host_name
        self.host_address = host_address
        self.action = action
        self.description = description
        self.argv = argv
        self.cwd = cwd
        self.status = "running"
        self.exit_code = None
        self.output = deque(maxlen=4000)
        self.started = time.time()
        self.finished = None
        self._proc = None

    def to_dict(self, tail=400):
        return {
            "id": self.id,
            "project": self.project,
            "host": self.host_name,
            "action": self.action,
            "description": self.description,
            "status": self.status,
            "exit_code": self.exit_code,
            "started": self.started,
            "finished": self.finished,
            "output": list(self.output)[-tail:],
        }


class JobManager:
    """In-memory job registry: one subprocess per deploy/stop/restart action."""

    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()
        threading.Thread(target=self._watchdog, daemon=True).start()

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def running_for(self, project, host_id):
        with self._lock:
            for j in self._jobs.values():
                if j.status == "running" and j.project == project and j.host_id == host_id:
                    return j
        return None

    def start(self, project, host_id, host, action, argv, cwd, description):
        job = Job(project, host_id, host["name"],
                  host.get("address") or "unix:///var/run/docker.sock",
                  action, description, argv, cwd)
        with self._lock:
            self._jobs[job.id] = job
            # prune old finished jobs to bound memory
            finished = [j for j in self._jobs.values() if j.status != "running"]
            if len(finished) > 100:
                for j in sorted(finished, key=lambda j: j.started)[: len(finished) - 100]:
                    del self._jobs[j.id]
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def _run(self, job):
        try:
            proc = subprocess.Popen(
                ["docker"] + job.argv,
                env=docker_env({"address": job.host_address}),
                cwd=job.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            job._proc = proc
            for line in proc.stdout:
                job.output.append(line.rstrip("\n"))
            proc.wait()
            job.exit_code = proc.returncode
        except Exception as e:
            job.exit_code = -1
            job.output.append(f"error: {e}")
        job.status = "success" if job.exit_code == 0 else "error"
        job.finished = time.time()

    def _watchdog(self):
        while True:
            time.sleep(30)
            now = time.time()
            with self._lock:
                running = [j for j in self._jobs.values() if j.status == "running"]
            for j in running:
                if now - j.started > JOB_TIMEOUT:
                    j.output.append(f"timed out after {JOB_TIMEOUT}s, killing")
                    if j._proc and j._proc.poll() is None:
                        j._proc.kill()
                    if j.status == "running":
                        j.status = "error"
                        j.exit_code = -1
                        j.finished = time.time()
