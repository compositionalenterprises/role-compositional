Role Name
=========

This role sets up a VM to host what amounts to a cloud-in-a-box; a combination of various cloud services all hosted in subdirectories of a given domain.

Requirements
------------

Role Variables
--------------

### General

```yaml
# The frontend used for the reverse proxy
compositional_frontend_service: 'nginx'
# The backend used for the database
compositional_backend_service: 'mariadb'
# The enumeration of the services to be installed
compositional_services:
  - 'nextcloud'
  - 'wordpress'
  - 'kanboard'
```

### Environment

```yaml
# The domain that will be pointing to the server's IP
environment_domain: 'example.com'
# The domain that will be pointing to the server's IP
environment_admin: 'admin'
```

### Kanboard

```yaml
compositional_kanboard_backend_password: 'testpassword'
```

### Nextcloud

```yaml
compositional_nextcloud_backend_password: 'testpassword'
compositional_nextcloud_admin_user: 'admin'
compositional_nextcloud_admin_password: 'admin'
```

### Wordpress

```yaml
compositional_wordpress_backend_password: 'testpassword'
```

### Firefly

```yaml
compositional_firefly_backend_password: 'testpassword'
compositional_firefly_app_key: 'testtesttesttesttesttesttesttest'
```

Dependencies
------------

```yaml
- src: nickjj.docker
  version: 'v1.8.0'
  name: docker
- src: geerlingguy.certbot
  name: certbot
```

Example Playbook
----------------

```yaml
#
# This playbook sets up a SSL-encrypted server running nextcloud with default
# frontends and backends, and default passwords. FOR TESTING ONLY!!!
#
- hosts: all
  become: True
  vars:
    docker__pip_packages:
      - "docker"
      - "python-apt"
    certbot_auto_renew_options: "--quiet --no-self-upgrade --pre-hook='docker stop nginx' --post-hook='docker start nginx'"
    certbot_admin_email: "{{ environment_admin }}@{{ environment_domain }}"
    certbot_create_if_missing: True
    certbot_install_from_source: True
    certbot_create_standalone_stop_services: []
    certbot_certs:
      - domains:
        - "{{ environment_domain }}"
    compositional_services:
      - 'nextcloud'
  roles:
    - { role: docker }
    - { role: certbot }
    - { role: compositional, ansible_python_interpreter: "/usr/bin/env python-docker"}
```

License
-------

MIT

Author Information
------------------

Andrew Cziryak
https://andrewcz.com
