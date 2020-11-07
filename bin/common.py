#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import random
import string
import pathlib
import fileinput
import subprocess
import ansible_vault

def eprint(*args, **kwargs):
    """Works the same as print but outputs to stderr."""
    print(file=sys.stderr, *args, **kwargs)


def json_print(data):
    """Prints json-formatted and dictionary data in human-readable form"""
    print(json.dumps(data, indent=4, sort_keys=True))


def json_eprint(data):
    """
    Prints json-formatted and dictionary data in human-readable form to stderr
    """
    print(json.dumps(data, indent=4, sort_keys=True), file=sys.stderr)


def create_pass(pass_len=16):
    """
    Since we're reusing the functionality, split out here the ability to
    generate a password of a specific length
    """
    # Generate the new password
    new_pass = ''
    for _ in range(pass_len):
        chars = string.ascii_letters + string.digits
        new_pass += random.SystemRandom().choice(chars)

    return new_pass


def create_local_repo(domain):
    """
    Creates a local repo from the upstream environment repo
    """
    # Set up shorthand strings to use below
    environment_domain = domain.replace('.', '-')
    gitlab_domain = 'gitlab.com'
    gitlab_prefix = "git@{}:compositionalenterprises".format(gitlab_domain)
    origin_url = "{}/environment.git".format(gitlab_prefix)

    #
    # Deal with brand new ssh keys for repos
    #
    # Add the ssh key for the remote repo
    gitlab_keys = subprocess.run(['ssh-keyscan', gitlab_domain],
            stdout=subprocess.PIPE, encoding='utf-8')
    # get a list of all of the keys without any empty strings
    gitlab_keys = list(filter(None, gitlab_keys.stdout.split('\n')))
    # Format the known_hosts absolute filepath
    known_hosts = "{}/.ssh/known_hosts".format(str(pathlib.Path.home()))
    # Loop through the keys and perform a lineinfile
    for gitlab_key in gitlab_keys:
        key_found = False
        key_ident = ' '.join(gitlab_key.split(' ')[:2])
        try:
            for line in fileinput.input(known_hosts):
                if line.startswith(key_ident):
                    print(gitlab_key.strip())
                    key_found = True
                    continue
        except FileNotFoundError:
            # This file doesn't exist yet. It must be a fresh isntall
            pass
        if key_found:
            # Go to the next key if we've found this one
            continue
        else:
            # This is a new key, so append it to the file
            with open(known_hosts, 'a') as known_hosts_file:
                known_hosts_file.write("{}\n".format(gitlab_key.strip()))

    # Clone down the template 'environment' repo
    subprocess.run(['git', 'clone', "{}/environment.git".format(gitlab_prefix),
        environment_domain], cwd='/tmp')
    # Check to see if the branch exists and check it out if it does
    try:
        subprocess.check_call(['git', 'ls-remote', '--exit-code', '--heads',
            'origin', environment_domain], cwd="/tmp/{}".format(environment_domain))
        subprocess.run(['git', 'checkout', environment_domain],
                cwd="/tmp/{}".format(environment_domain))
        print("Checked out branch: {}".format(environment_domain))
    except subprocess.CalledProcessError:
        # Checkout a new branch
        subprocess.run(['git', 'checkout', '-b', environment_domain],
                cwd="/tmp/{}".format(environment_domain))

    return "/tmp/{}".format(environment_domain)


def put_repo_in_gitlab(local_repo, domain):
    #
    # It takes a lot to keep these lines to a limit of chars under 79 chars
    # long
    #
    environment_domain = domain.replace('.', '-')
    gitlab_prefix = 'git@gitlab.com:compositionalenterprises'
    origin_url = "{}/environment.git".format(gitlab_prefix)
    dirpath_to_script = os.path.dirname(os.path.realpath(__file__))
    path_to_vault = 'playbooks/group_vars/all/vault.yml'
    vault_file_path = "{}/../{}".format(dirpath_to_script, path_to_vault)
    path_to_vault_pass = "{}/../.vault_pass".format(dirpath_to_script)

    # Get the GitLab API personal oauth token
    with open(path_to_vault_pass, 'r') as plays_vault_pass_file:
        plays_vault_pass = plays_vault_pass_file.read().strip()
    vault = ansible_vault.Vault(plays_vault_pass)
    vault_content = vault.load(open(vault_file_path).read())
    private_token = vault_content['vault_gitlab_oauth_token']

    # Add all files
    subprocess.run(['git', 'add', '-A', '.'],
            cwd="/tmp/{}".format(environment_domain))

    # Commit those files
    subprocess.run(['git', 'commit', '-m', 'Setup Commit'],
            cwd="/tmp/{}".format(environment_domain))

    # Push the repo up
    subprocess.run(['git', 'push', '-u', 'origin', environment_domain],
            cwd="/tmp/{}".format(environment_domain))


SERVICES = {
        'database': {
            'registry': {
                'source': 'dockerhub',
                'path': 'library/mariadb'
                },
            'passwords': {
                'compositional_database_root_password': {}
                }
            },
        'jekyll': {
            'registry': {
                'source': 'dockerhub',
                'path': 'jekyll/jekyll'
                },
            },
        'bookstack': {
            'registry': {
                'source': 'dockerhub',
                'path': 'solidnerd/bookstack'
                },
            'passwords': {
                'compositional_bookstack_backend_password': {},
                'compositional_bookstack_admin_password': {}
                }
            },
        'bitwarden': {
            'registry': {
                'source': 'dockerhub',
                'path': 'bitwardenrs/server'
                },
            'passwords': {
                'compositional_bitwarden_admin_password': {},
                }
            },
        'kanboard': {
            'registry': {
                'source': 'dockerhub',
                'path': 'kanboard/kanboard'
                },
            'passwords': {
                'compositional_kanboard_backend_password': {},
                'compositional_kanboard_admin_password': {}
                }
            },
        'nextcloud': {
            'registry': {
                'source': 'dockerhub',
                'path': 'library/nextcloud'
                },
            'passwords': {
                'compositional_nextcloud_backend_password': {},
                'compositional_nextcloud_admin_password': {}
                }
            },
        'wordpress': {
            'registry': {
                'source': 'dockerhub',
                'path': 'library/wordpress'
                },
            'passwords': {
                'compositional_wordpress_backend_password': {},
                'compositional_wordpress_admin_password': {}
                }
            },
        'firefly': {
            'registry': {
                'source': 'dockerhub',
                'path': 'jc5x/firefly-iii'
                },
            'passwords': {
                'compositional_firefly_app_key': {
                    'length': 32
                    },
                'compositional_firefly_backend_password': {},
                'compositional_firefly_admin_password': {
                    'length': 16
                    }
                }
            },
        'rundeck': {
            'registry': {
                'source': 'dockerhub',
                'path': 'rundeck/rundeck'
                },
            'passwords': {
                'compositional_rundeck_backend_password': {},
                'compositional_rundeck_admin_password': {}
                }
            },
        'mysql': {
            'registry': {
                'source': 'dockerhub',
                'path': 'library/mariadb'
                },
            'passwords': {
                'compositional_database_root_password': {}
                }
            },
        'portal': {
            'registry': {
                'source': 'dockerhub',
                'path': 'compositionalenterprises/portal'
                },
            'passwords': {
                'compositional_portal_backend_password': {},
                'compositional_portal_admin_password': {}
                }
            },
        'commandcenter': {
            'registry': {
                'source': 'dockerhub',
                'path': 'compositionalenterprises/commandcenter'
                },
            'passwords': {
                'compositional_commandcenter_backend_password': {},
                'compositional_commandcenter_admin_password': {}
                }
            },
        }

REGISTRY_SOURCES = {
        'dockerhub': {
            'tags': "https://hub.docker.com/v2/repositories/{}/tags/?page={}",
            'containers': 'https://hub.docker.com'
            }
        }
