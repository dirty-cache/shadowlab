# Setting up SSL Certificates

## Description

We want our services to use HTTPS (SSL) encryption and avoid browser certificate warnings.

For this we need to create custom SSL certificates. Creating certificates can be complex and error-prone. In this repo, pre-configured certificates are provided for uploading to various services.

Caveats

* These certificates are only secure within a private LAN environment. The private keys are included in this repo which makes it easy for anyone to validate the same URLs on another host (which is the whole point of bundling the certificates - but you should be aware)
* The Root CA Certificate is bundled __without__ the private key. This is intentional, so nobody can sign new certificates except me.
* For a more secure environment, you should create your own root CA and server certificates.

## Public Certificate Authorities

One may wonder why not to use public certificate providers such as LetsEncrypt. The problem is that these services require you to be the (single) owner of the domain that needs to be signed. We are using a non-public domain (shadowlab.lan) for which this does not hold. Furthermore, you need to have control over the DNS server serving that domain. This can work if you register your own domain and use that instead of shadowlab.lan.

## Root certificate

In order for the browser to trust certificates signed by the Shadowlab CA, we need to import the CA Certificate into our browser (Firefox/Chrome/etc) or Operating System.

You can download the root certificate here:

[Shadowlab Root Certificate](../config/certs/Shadowlab_CA.crt)

## Proxmox

Installing the Proxmox certificate on Proxmox

* Select the server (pve) and go to System - Certificates
* Click Upload Custom Certificate
* Upload the private key and certificate chain in the dialog
* Wait a few seconds for the web service to restart
* Proxmox should now use the custom SSL certificate

[Private Key](../config/certs/shadowlab.key)
[Proxmox Web Certificate](../config/certs/Proxmox.crt)