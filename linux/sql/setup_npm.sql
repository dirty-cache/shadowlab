INSERT INTO public.auth (user_id, type, secret) VALUES (1, 'password', '$2b$13$jGJfJTIo5yH0IU3c7u4APOxEjiUVJkJ03wCgj.eebq8mInIMt1iOC');

INSERT INTO public."user" (email, name, nickname, avatar, roles) VALUES ('admin@local.lan', 'Admin', 'Admin', '//www.gravatar.com/avatar/4bc95ca2c9281087a83dde0b6350a7b0?default=mm', '["admin"]');



INSERT INTO public.proxy_host (owner_user_id, domain_names, forward_host, forward_port) 
VALUES (
    (1, '["homepage.shadow.lab"]', 'docker01.shadowlab.lan', 3002),
    (1, '["dockhand.shadow.lab"]', 'docker01.shadowlab.lan', 3001),
    (1, '["pve.shadow.lab"]', 'pve.shadowlab.lan', 8006)
)


--
-- Data for Name: redirection_host; Type: TABLE DATA; Schema: public; Owner: npm
--

#INSERT INTO public.redirection_host (id, created_on, modified_on, owner_user_id, is_deleted, domain_names, forward_domain_name, preserve_path, certificate_id, ssl_forced, block_exploits, advanced_config, meta, http2_support, enabled, hsts_enabled, hsts_subdomains, forward_scheme, forward_http_code) VALUES (1, '2026-11-25 19:53:18.764+01', '2026-11-25 19:53:49.150535+01', 1, 0, '["proxmox.shadow.lab"]', 'pve.shadow.lab', 0, 1, 0, 0, '', '{"nginx_online":true,"nginx_err":null}', 0, 1, 0, 0, 'auto', 301);


