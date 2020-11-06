#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json

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
