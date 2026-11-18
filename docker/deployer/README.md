# deployer

Web UI for deploying the compose stacks in this `docker/` directory to one or
more Docker hosts.

- Installs to `/opt/docker/deployer` (see `bin/install-container`), then
  `docker compose up -d`.
- With the default `.env` it scans `/opt/docker` for every stack and serves
  the UI on port 8080 of the host it runs on.
- The **Docker hosts** panel in the UI is where you add further hosts
  (e.g. `tcp://<ip>:2375`); hosts persist in the `deployer-data` volume.
- A stack that needs a `.env` (see `.env.example` in its folder) must have
  that file created before it can be deployed or shown.
