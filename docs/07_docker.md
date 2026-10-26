# Setting up Docker

## Description

We want a server to run Docker for our administration tools. We are going to use Rocky Linux on a dedicated admin VM.

We assume Rocky Linux is already running on the VM and pre-configured with the ```setup-rocky``` script.

## Running Docker install script

From the ```bin``` directory, run ```install-docker <IP>``` and ```setup-firewall```.

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

Dockhand is now running on the host, port 3000: [Dockhand](http://192.168.70.2:3000)
