#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import yaml
import argparse
import subprocess


def eprint(*args, **kwargs):
    """Works the same as print but outputs to stderr."""
    print(file=sys.stderr, *args, **kwargs)


def json_print(data):
    print(json.dumps(data, indent=4, sort_keys=True))


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Updates an entry in ClouDNS")
    parser.add_argument('-domain', '--domain',
                        help="The domain to create this environment for",
                        required=False)
    parser.add_argument('-v', '--vaultpass',
                        help='The vault pass to use to encrypt things',
                        required=False)

    args = vars(parser.parse_args())

    #
    # Prompt for the args if they were not provided
    #
    if not args['domain']:
        args['domain'] = input("Domain: ")
    if not args['vaultpass']:
        args['vaultpass'] = input("Vault Password: ")

    return args


def main():
    """Updates the file"""
    # Get the args
    args = parse_args()

    vault = subprocess.run(["ansible-vault", "view", "./vault1"],
            capture_output=True, encoding='utf-8', env={"ANSIBLE_VERBOSITY":
                '0'})
    vault = yaml.safe_load(vault.stdout)
    print(vault)


if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
