# dind

Docker-in-Docker: a second Docker daemon in a container, on the host network.

Deploy it, then add `tcp://<host-ip>:2375` as a host in the Deployer web UI
(Docker hosts → Add host) to get a second deployment target. Plain TCP with
no TLS — lab network only.
