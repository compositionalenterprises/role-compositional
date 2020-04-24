#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import common
import random
import shutil
import string
import getpass
import pathlib
import argparse
import fileinput
import subprocess
import ansible_vault

def push_repo_to_gitlab(local_repo, domain):
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

    # Commit those files
    subprocess.run(['git', 'commit', '-am', 'Renew API Token'],
            cwd="/tmp/{}".format(environment_domain))

    # Push the repo up
    subprocess.run(['git', 'push', '-u', 'origin', environment_domain],
            cwd="/tmp/{}".format(environment_domain))

def create_apitoken():
    """
    Since we're reusing the functionality, split out here the ability to
    generate a password of a specific length
    """
    # Open the realm.properties file and read the admin password
    with open('/home/rundeck/server/config/realm.properties', 'r') as realm:
        admin_pass = [entry.split(':')[1].split(',')[0] for entry in realm if
                entry.startswith('admin')][0]

    env_vars = {}
    rd_url = 'https://compositionalenterprises.ourcompose.com/rundeck'
    env_vars['RD_URL'] = rd_url
    env_vars['RD_USER'] = 'admin'
    env_vars['RD_PASSWORD'] = admin_pass
    token_creation = subprocess.check_output(['rd', 'tokens', 'create', '-u',
        'ourcomposebot', '-r', 'user,apitoken', '-d', '30d'], env=env_vars)
    apitoken = token_creation.decode().split('\n')[1]

    return apitoken


def add_vaulted_apitoken(args, vars_dir, apitoken):
    """
    Set up the passwords for the services that we need to vault
    """
    vault_file_path = "{}/vault.yml".format(vars_dir)
    # Open up the vault and add the new entry
    vault = ansible_vault.Vault(args['vaultpass'])
    vault_content = vault.load(open(vault_file_path).read())
    vault_content['vault_ourcompose_rundeck_apitoken'] = apitoken
    vault_string = vault.dump(vault_content).decode()
    # Write the vault file back out
    with open(vault_file_path, 'w') as vault_file:
        vault_file.write(vault_string)


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

    # Clone down the template 'environment' repo with the correct branch
    subprocess.run(['git', 'clone', '--branch',
            environment_domain.replace('.', '-'),
            "{}/environment.git".format(gitlab_prefix),
            environment_domain], cwd='/tmp')

    return "/tmp/{}".format(environment_domain)


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
    if not args['vaultpass']:
        args['vaultpass'] = getpass.getpass("Vault Password: ")

    return args


def main():
    """Updates the file"""
    args = parse_args()
    # Set up the local repo
    local_repo = create_local_repo(args['domain'])

    #
    # Write the variable redirect to the all.yml file
    #
    vars_dir = "{}/group_vars/compositional".format(local_repo)
    with open("{}/all.yml".format(vars_dir), 'r') as all_comp:
        comp_vars = yaml.safe_load(all_comp.read())
    comp_vars['ourcompose_rundeck_apitoken'] = '{{ vault_ourcompose_rundeck_apitoken }}'
    with open("{}/all.yml".format(vars_dir), 'w') as all_comp:
        comp_vars = all_comp.write(yaml.dump(comp_vars))

    #
    # Create new API token
    #
    apitoken = create_apitoken()
    add_vaulted_apitoken(args, vars_dir, apitoken)
    push_repo_to_gitlab(local_repo, args['domain'])

    print("New API token created and vaulted")

    # Remove the environment
    shutil.rmtree("/tmp/{}".format(args['domain'].replace('.', '-')))


if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
