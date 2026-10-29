# Network diagram

Topology of the Shadow Lab: an isolated LAN, a WAN uplink, and remote access through Tailscale (or Headscale). Addresses and roles match [Network Settings](01_network.md).

The WAN prefix `192.168.60.0/24` is the example from the OPNsense setup and may differ per site.

```mermaid
flowchart RL
  internet[Internet]
  remote["Remote users (Tailscale/Headscale)"]
  wan["WAN 192.168.60.0/24"]
  subgraph proxmox ["Proxmox pve.shadowlab.lan 192.168.70.1"]
    direction RL
    wannic["WAN NIC<br/>DHCP or 192.168.60.254/24"]
    opnsense["OPNsense Router<br/>HAProxy<br/>Tailscale exit node"]
    lannic["LAN NIC<br/>192.168.70.254<br/>Proxy 192.168.70.3"]
    mgt["Management mgt.shadowlab.lan 192.168.70.2<br/>Rocky Linux and Docker<br/>Technitium DNS/DHCP, Containers"]
  end
  lan["Private LAN 192.168.70.0/24 (Shadowlab)"]
  bootstrap[initial setup only]
  internet --- wan
  remote --- wan
  wan --- wannic
  wannic --- opnsense
  opnsense --- lannic
  lannic --- lan
  mgt --- lannic
  bootstrap --- lan
```
