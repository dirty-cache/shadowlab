# deployer

Web UI that registers the compose stacks in this repo with Dockhand and deploys
them there. The deployer does not talk to a Docker daemon.

The image is built in GitHub Actions (`.github/workflows/deployer-image.yml`) and
published to this repo's packages:

https://github.com/dirty-cache/shadowlab/packages

Compose pulls `ghcr.io/dirty-cache/shadowlab/deployer`. Updating the running UI
is `docker compose pull && docker compose up -d` on the host that runs it. That
host does not need this git checkout, and it does not build the image.

A private package needs `docker login ghcr.io` on that host (a PAT with
`read:packages`). Dockhand needs its own git credential before it can clone a
private copy of this repo (`GIT_CREDENTIAL_ID` is that credential's id).

## Configure

Copy `.env.example` to `.env` and set:

- `DOCKHAND_URL` — Dockhand API, for example `http://192.168.70.2:3001`
- `DOCKHAND_TOKEN` — personal API token (`dh_...`) from the Dockhand profile
- `GITHUB_TOKEN` — read-only token so the UI can list `docker/*/compose.yaml`
  when the repo is private

## Run

```
cd /opt/docker/deployer
docker compose pull
docker compose up -d
```

The UI is on port 8080. Pick a Dockhand environment in the sidebar. Deploy
creates a git stack (or redeploys one that already exists) with compose path
`docker/<name>/compose.yaml` on `master`, so Dockhand tracks this repository
as the source. Stop, restart, and logs go through the Dockhand API.

The `dockhand` stack is listed and cannot be deployed from here.

Env files that used to live in `/opt/docker/<name>/.env` are not copied.
Git stacks take environment from the repository plus Dockhand's own env store.
