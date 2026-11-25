# Setting up Docker

## Description

We want a server to run Docker for our administration tools. We are going to use Rocky Linux on a dedicated admin VM.

We assume Rocky Linux is already running on the VM and pre-configured with the ```setup-rocky``` script.

## Installing Docker

From the repo root, with root SSH to the VM:

```
ansible-playbook -i ansible/hosts ansible/rocky/docker.yml -k
```

The playbook targets the docker VM in `ansible/hosts` (192.168.70.5). `-k` prompts for the SSH password.

The Docker environment now runs on the server.

## Setting up services

From the ```bin``` directory, run ```install-compose```. This will copy the Docker Compose files to ```/opt/local```.

### Install Technitium DNS Server

Run:
```
cd /opt/docker/dns
docker compose up -d
```

Technitium is now running on the host, port 5380: [Technitium](http://192.168.70.2:5380)

Go to [Technitium](08_technitium.md) for setting it up.

### Install Dockhand

Dockhand is a tool for managing docker containers on multiple hosts.

Run:
```
cd /opt/docker/dockhand
docker compose up -d
```

Dockhand is now running on the host, port 3000: [Dockhand](http://192.168.70.2:3000)

### Install Homepage

Homepage.dev is a server running a nice home page for labs.

Run:
```
cd /opt/docker/homepage
docker compose up -d
```

Homepage is now running on the host, port 80: [Homepage](http://192.168.70.2:80)

### Install Deployer

Deployer is a web UI that registers the compose stacks in this repo as
Dockhand git stacks and deploys them through Dockhand. It does not use the
local Docker socket.

The deployer source lives in its own repo, checked out at
`/home/bart/fdelab/deployer` (`ssh://git@forgejo.lan/homelab/deployer.git`).
The image is still published to the shadowlab packages
([shadowlab packages](https://github.com/dirty-cache/shadowlab/packages))
and compose pulls `ghcr.io/dirty-cache/shadowlab/deployer`. The host that
runs it does not build the image and does not need a checkout to update it
(`docker compose pull`). Log in to `ghcr.io` first when the package is private.

Copy `.env.example` from the deployer repo to `.env` on the host and set
`DOCKHAND_URL`, `DOCKHAND_TOKEN`, and `GITHUB_TOKEN`. Give Dockhand a git
credential that can clone this repo and put its id in `GIT_CREDENTIAL_ID`.

Run:
```
cd /opt/docker/deployer
docker compose pull
docker compose up -d
```

Deployer is now running on the host, port 8080: [Deployer](http://192.168.70.78:8080)

Choose a Dockhand environment in the sidebar. Deploy registers the stack
with source tracking (`docker/<name>/compose.yaml` on `master`) and asks
Dockhand to deploy it. The `dockhand` stack itself is not offered for deploy.
