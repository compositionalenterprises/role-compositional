#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import common
import shutil
import getpass
import argparse
import ansible_vault


def add_new_passwords(args, local_repo, services, comp_vars):
    """Enter a password into the environment"""
    passwords_needed = {}
    for service in services:
        passwords_needed[service] = []
        # Skip if we don't need any passwords for this service
        if not 'passwords' in common.SERVICES[service]:
            continue
        # Get all of the ones that weren't in the list we compiled above
        for password_var in common.SERVICES[service]['passwords'].keys():
            if not password_var in comp_vars.keys():
                with open(
                        "{}/group_vars/compositional/all.yml"
                        .format(local_repo), 'a') as vars_file:
                    vars_file.write('\n{0}: "{{{{ vault_{0} }}}}"'.format(password_var))
                # Set the password length
                pass_len = 16
                if 'length' in common.SERVICES[service]['passwords'][password_var]:
                    pass_len = common.SERVICES[service]['passwords'][password_var]['length']

                new_pass = common.create_pass(pass_len=pass_len)

                vault_file_path = "{}/group_vars/compositional/vault.yml".format(local_repo)
                # Open up the vault and add the new entry
                vault = ansible_vault.Vault(args['vaultpass'])
                vault_content = vault.load(open(vault_file_path).read())
                vault_content["vault_{}".format(password_var)] = new_pass
                vault_string = vault.dump(vault_content)
                with open(vault_file_path, 'w') as vault_file:
                    vault_file.write(vault_string)


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Updates an entry in ClouDNS")
    parser.add_argument('-d', '--domain',
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
    args['domain'] = args['domain'].lower()
    if not args['vaultpass']:
        args['vaultpass'] = getpass.getpass("Vault Password: ")

    return args


def main():
    """Updates the file"""
    # Get the args
    args = parse_args()

    # Set up the local repo
    local_repo = common.create_local_repo(args['domain'])

    # Gather list of services
    with open("{}/group_vars/compositional/all.yml".format(local_repo), 'r') as all_comp:
        comp_vars = yaml.safe_load(all_comp.read())
    services = comp_vars['compositional_services']

    add_new_passwords(args, local_repo, services, comp_vars)

    # Push the repo up to gitlab
    common.put_repo_in_gitlab(local_repo, args['domain'])
    print("Environment {} updated!".format(args['domain']))

    # Clean up after ourselves
    shutil.rmtree(local_repo)


if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
