INSERT INTO public.environments (name) values ('Local');

INSERT INTO public.users (username, email, password_hash, display_name)
VALUES ('admin', 'admin@local.lan', '$argon2id$v=19$m=65536,t=3,p=1$YXsvwfwtk/Bdezcpgwnong$WlqwBAMwhwBUGBEt7OZ/W8RPWjl119ZF+hIbubjqShI', 'Administrator');

UPDATE public.auth_settings SET auth_enabled=true WHERE id=1;
