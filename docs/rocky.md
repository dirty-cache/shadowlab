# Setting up a Rocky Linux VM

## Description

We need a host to run our stuff. We are going to use [Rocky Linux](https://rockylinux.org/) for this.

We assume there is no DHCP/DNS server (yet) on the network, so we will manually enter network settings.

## Prerequisites

* Proxmox up and running

## Preparing the ISO image

* Download the ISO image from ([Rocky Linux Download]https://rockylinux.org/download). Select Rocky Linux 9 and download the [Minimal ISO](https://download.rockylinux.org/pub/rocky/9/isos/x86_64/Rocky-9.8-x86_64-minimal.iso)
* On Proxmox, go to the storage pool "local"
* Select ISO Images and click Upload
* Upload the ISO image

## Creating a VM

* On Proxmox, click "Create VM"
* Enable Advanced
* General - Name: mgt, Start at boot: Enabled
* OS: Select the ISO image under Use CD/DVD image
* System: Machine q35, Qemu Agent: Enabled
* Disk: Create a 32GiB disk
* CPU: Set Sockets=1, Cores=2, Type=host
* Memory: 4 GiB (4096 MiB) - Minimum for the installer. You may shrink to 1GiB after install
* Network: Defaults (1 NIC on vmbr0)

## Linux install

* Boot the VM. A boot menu will show on the console
* Select Install and hit Enter
* Select English (United States)
* Customize Installation
    * Time and date: Select your region
    * Software selection: Minimal install + Headless management
    * Installation destination: Seelct harddisk sda. Leave the rest default
    * KDUMP: Disable
    * Hostname: mgt
    * Ethernet: Select Enable. Click Configure
    * Select tab IPv4 Settings
    * Method: Manual
    * Add an IP address: 192.168.70.2, mask 24, gateway 192.168.70.254
    * DNS Servers: 192.168.70.254 (for now we will use the DNS from OPNSense)
    * Search domain: fdelab.lan
    * Select tab IPv6 Settings, set to Ignore
    * Click Save, Done
    * Root password: Enter a password, enable Allow root SSH login with password

* Click Begin Installation
* After completion, click Reboot
* On the console there should be a login prompt.
* Login with root and your password
* If networking is setup correctly, you can also login from a jumphost using ssh
* run ```dnf update```. Enter Y to install the updates. Enter Y if it asks to approve the Rocky GPG key. This may take a few minutes.
* Reboot: ```reboot``` or ```shutdown -r now```

## Post Install

* Clone the bootstrap repo on the host as root: ```git clone <TBD>```
* Run ```setup-rocky``` on the host