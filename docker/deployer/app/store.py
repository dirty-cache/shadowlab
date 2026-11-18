"""
Author: Bart Sjerps
Last modified: 2026-11-18
Purpose: Persistent registry of Docker hosts for the Shadow Lab Deployer.

Hosts are stored in a single JSON file under DEPLOYER_DATA_DIR (mounted volume).
The default host is seeded from the DEPLOYER_DEFAULT_HOST_NAME /
DEPLOYER_DEFAULT_DOCKER_HOST environment variables on first start; after that
hosts are managed from the web UI and survive container restarts.
"""

import json
import os
import re
import threading

DATA_DIR = os.environ.get("DEPLOYER_DATA_DIR", "/data")
HOSTS_FILE = os.path.join(DATA_DIR, "hosts.json")

ADDR_RE = re.compile(r"^([A-Za-z0-9._-]+|\[[0-9a-fA-F:]+\])(:\d+)?$")


def normalize_address(address):
    """Return a canonical DOCKER_HOST value, or raise ValueError."""
    address = (address or "").strip()
    if not address:
        return "unix:///var/run/docker.sock"
    scheme = re.match(r"^([a-z]+)://", address)
    if not scheme or scheme.group(1) not in ("unix", "tcp", "tls"):
        raise ValueError("address must start with unix://, tcp:// or tls://")
    rest = address[scheme.end():]
    if scheme.group(1) == "unix":
        if not rest.startswith("/"):
            raise ValueError("unix socket path must be absolute")
        return address
    if not ADDR_RE.match(rest):
        raise ValueError("invalid host address (expected host:port)")
    return address


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "host"


class HostsStore:
    """Thread-safe CRUD over the hosts JSON file."""

    def __init__(self, path=HOSTS_FILE):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data = None

    def _load(self):
        if self._data is not None:
            return self._data
        if os.path.exists(self.path):
            with open(self.path) as f:
                self._data = json.load(f)
        else:
            self._data = {"version": 1, "hosts": []}
            self._data["hosts"].append({
                "id": slugify(os.environ.get("DEPLOYER_DEFAULT_HOST_NAME", "lab")),
                "name": os.environ.get("DEPLOYER_DEFAULT_HOST_NAME", "lab"),
                "address": normalize_address(os.environ.get("DEPLOYER_DEFAULT_DOCKER_HOST", "")),
                "description": "Default host, configured at deploy time",
            })
            self._persist()
        return self._data

    def _persist(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
            f.write("\n")
        os.replace(tmp, self.path)

    def _validate(self, name, address):
        name = (name or "").strip()
        if not name or len(name) > 32:
            raise ValueError("name must be 1-32 characters")
        try:
            address = normalize_address(address)
        except ValueError as e:
            raise ValueError(f"address: {e}")
        return name, address

    def list(self):
        with self._lock:
            return list(self._load()["hosts"])

    def get(self, host_id):
        with self._lock:
            for h in self._load()["hosts"]:
                if h["id"] == host_id:
                    return h
        return None

    def add(self, name, address, description=""):
        name, address = self._validate(name, address)
        with self._lock:
            data = self._load()
            host = {
                "id": slugify(name),
                "name": name,
                "address": address,
                "description": (description or "").strip()[:200],
            }
            for h in data["hosts"]:
                if h["name"].lower() == name.lower():
                    raise ValueError(f"a host named {name!r} already exists")
                if h["id"] == host["id"]:
                    n = 2
                    while f"{host['id']}-{n}" in [x["id"] for x in data["hosts"]]:
                        n += 1
                    host["id"] = f"{host['id']}-{n}"
            data["hosts"].append(host)
            self._persist()
            return host

    def update(self, host_id, name, address, description=""):
        name, address = self._validate(name, address)
        with self._lock:
            data = self._load()
            for h in data["hosts"]:
                if h["id"] == host_id:
                    for other in data["hosts"]:
                        if other["id"] != host_id and other["name"].lower() == name.lower():
                            raise ValueError(f"a host named {name!r} already exists")
                    h["name"] = name
                    h["address"] = address
                    h["description"] = (description or "").strip()[:200]
                    self._persist()
                    return h
        return None

    def remove(self, host_id):
        with self._lock:
            data = self._load()
            if len(data["hosts"]) <= 1:
                raise ValueError("cannot remove the last host")
            for i, h in enumerate(data["hosts"]):
                if h["id"] == host_id:
                    del data["hosts"][i]
                    self._persist()
                    return h
        return None
