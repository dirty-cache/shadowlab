# Network diagram

Topology of the Shadow Lab: an isolated LAN, a WAN uplink, and remote access through Tailscale (or Headscale). Addresses and roles match [Network Settings](01_network.md).

The WAN prefix `192.168.60.0/24` is the example from the OPNsense setup and may differ per site.

```mermaid
flowchart RL
  internet[Internet]
  wan["WAN 192.168.60.0/24"]
  subgraph proxmox ["Proxmox pve.shadowlab.lan 192.168.70.1"]
    opnsense["OPNsense router.shadowlab.lan<br/>LAN 192.168.70.254<br/>WAN DHCP or 192.168.60.254/24<br/>Proxy NIC 192.168.70.3 proxy.shadowlab.lan HAProxy<br/>Tailscale exit node advertises 192.168.70.0/24"]
    mgt["Management mgt.shadowlab.lan 192.168.70.2<br/>Rocky Linux and Docker<br/>Technitium DNS/DHCP, Dockhand, Homepage"]
  end
  lan["LAN 192.168.70.0/24 shadowlab.lan"]
  bootstrap[Bootstrap desktop initial setup only]
  remote["Remote users via Tailscale or Headscale<br/>lab DNS 192.168.70.2"]
  internet --- wan --- opnsense
  opnsense --- lan
  mgt --- lan
  bootstrap --- lan
  remote --- opnsense
```
