# dind

Docker-in-Docker: a second Docker daemon in a container, its API published
on port 2375 of the host it runs on.

Deploy it, then add `tcp://<host-ip>:2375` as a host in the Deployer web UI
(Docker hosts → Add host) to get a second deployment target. Plain TCP with
no TLS — lab network only.

Keep it on the default bridge network: with host networking the inner
daemon's iptables management runs in the host's namespace and clobbers the
host's own Docker port publishing.
