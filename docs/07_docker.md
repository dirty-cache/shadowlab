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

Deployer is a web UI for deploying the compose stacks in this repo to one or
more Docker hosts. It discovers every stack in the `docker/` directory
automatically, so new stacks appear without a redeploy.

Run:
```
cd /opt/docker/deployer
docker compose up -d
```

Deployer is now running on the host, port 8080: [Deployer](http://192.168.70.78:8080)

Additional Docker hosts are added in the UI (Docker hosts panel), e.g.
`tcp://<ip>:2375` — the `docker/dind` stack provides a second daemon for
that. A stack whose folder has a `.env.example` needs a `.env` created (and
filled in) before it can be deployed.
