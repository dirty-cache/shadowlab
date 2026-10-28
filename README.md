# FDE Shadow Lab

## Description

The Shadow Lab provides a way to quickly setup a small collaboration lab where multiple users (customers and partners) can work together on projects, without requiring direct access to customer network or using public (cloud) services.

The Shadow Lab uses Proxmox and Tailscale to provide a lab where remote users can work and collaborate in a secure way.

The Shadow Lab is built on free (mostly Open Source) tools for management.

## Requirements

* A Tailscale account or a self-hosted Headscale environment
* An x86 server to run Proxmox (this can be as small as a mini PC)
* A network with a completely isolated LAN, and an uplink to the internet
* A "bootstrap" desktop (Windows or Linux, VM or bare metal) with access to the isolated LAN (only for initial setup)

## Components

* Proxmox - to run Virtual Machines
* OPNSense - virtual firewall/router
* Tailscale Client - to provide secure VPN connectivity
* Docker - to run containers

## Getting started

* Setup the bootstrap desktop on the private LAN
* Follow the Proxmox instructions