# Setting up Tailscale

## Description

We are going to create a Tailscale network to manage our private FDE lab.

We will use a dedicated desktop to manage our lab environment. Ideally this is a VM (Fresh Linux or Windows install)

## Requirements

* A [Tailscale](https://login.tailscale.com/start) login
* A dedicated desktop (VM) to manage the lab network
* A Lab network (in our case, 192.168.70.0/24 - may be configured later) 
* A DNS server in the lab network (192.168.70.2 - may be configured later)

## Initial setup

* Login to [Tailscale](https://login.tailscale.com/login) (On a regular browser  primary desktop or from the VM)

## Tailscale Admin

* Check if you have Tailscale access and can see the Network - Machines page. There should be no machines yet on the first login

## Connecting the VM

* On the VM, install Tailscale: ```curl -fsSL https://tailscale.com/install.sh | sh```
* Login to Tailscale: ```sudo tailscale login```
* Open the URL that is shown on the console
* On the Tailscale page, click the CONNECT button
* On the VM console, a Success message should be shown
* Allow tailscale to use the Lab DNS: ```tailscale set --accept-dns```

## Tailscale network setup
* On the [Tailscale console](https://console.tailscale.com/admin/machines) you should see the VM connected
* We want our client VMs to use the DNS in the lab network
* Go to Network - DNS
* Under Nameservers, click Add Nameserver, select Custom
* Enter the Lab DNS IP address (192.168.70.2)

