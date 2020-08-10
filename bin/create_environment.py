#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import common
import common
import random
import shutil
import string
import pathlib
import argparse
import fileinput
import subprocess
import ansible_vault
import update_apitoken


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


def create_vaulted_passwords(local_repo, service, vault_pass):
    """
    Set up the passwords for the services that we need to vault
    """
    vars_dir = "{}/group_vars/compositional".format(local_repo)
    if not 'passwords' in common.SERVICES[service]:
        return

    for password_var in common.SERVICES[service]['passwords'].keys():
        # Write the reference to the password in the vars file
        with open("{}/all.yml".format(vars_dir), 'a') as vars_file:
            vars_file.write('\n{0}: "{{{{ vault_{0} }}}}"'.format(password_var))

        # Set the password length
        pass_len = 16
        if 'length' in common.SERVICES[service]['passwords'][password_var]:
            pass_len = common.SERVICES[service]['passwords'][password_var]['length']

        new_pass = create_pass(pass_len=pass_len)

        vault_file_path = "{}/vault.yml".format(vars_dir)
        if os.path.isfile(vault_file_path):
            # Open up the vault and add the new entry
            vault = ansible_vault.Vault(vault_pass)
            vault_content = vault.load(open(vault_file_path).read())
            vault_content["vault_{}".format(password_var)] = new_pass
            vault_string = vault.dump(vault_content).decode()
        else:
            # Create the vault file entirely from scratch
            create_vault_command = [
                    'ansible-vault',
                    'encrypt_string',
                    '--vault-password-file',
                    '/tmp/vault_pass_file',
                    "vault_{}: {}".format(password_var, new_pass)
                    ]
            with open('/tmp/vault_pass_file', 'w') as vault_pass_file:
                vault_pass_file.write(vault_pass)

            vault_string = subprocess.run(create_vault_command,
                    stdout=subprocess.PIPE, cwd=local_repo)
            vault_string = vault_string.stdout.decode()
            # string off the string header
            vault_string = '\n'.join(vault_string.split('\n')[1:])
            # replace the indentation
            vault_string = vault_string.replace(' ', '')

            # Remove the temporarily created vault password file
            os.remove('/tmp/vault_pass_file')

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

    # Clone down the template 'environment' repo
    subprocess.run(['git', 'clone', "{}/environment.git".format(gitlab_prefix),
        environment_domain], cwd='/tmp')
    # Checkout a new branch
    subprocess.run(['git', 'checkout', '-b', environment_domain],
            cwd="/tmp/{}".format(environment_domain))

    return "/tmp/{}".format(environment_domain)


def format_services(services):
    """
    Ensures that the service list passed in is formatted correctly and
    returned as a list
    """
    services = services.split(',')
    for index, service in enumerate(services):
        services[index] = service.strip()

    # Add portal to all of our instances
    services.append('portal')

    return services


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Updates an entry in ClouDNS")
    parser.add_argument('-d', '--domain',
                        help="The domain to create this environment for",
                        required=False)
    parser.add_argument('-v', '--vaultpass',
                        help='The vault pass to use to encrypt things',
                        required=False)
    parser.add_argument('-s', '--services',
                        help='''The list of services that should be deployed to
                        this instance, in comma-separated form''',
                        required=False)
    parser.add_argument('-e', '--email',
                        help='Email address for the main point of contact',
                        required=False)
    parser.add_argument('-z', '--dropletsize',
                        help='The size of the droplet for this instance',
                        required=False)
    parser.add_argument('-a', '--envadmin',
                        help='The admins username for this instance',
                        default='admin',
                        required=False)

    args = vars(parser.parse_args())

    #
    # Prompt for the args if they were not provided
    #
    if not args['domain']:
        args['domain'] = input("Domain: ")
    if not args['services']:
        args['services'] = input("Services: ")
    if not args['dropletsize']:
        args['dropletsize'] = 's-1vcpu-1gb'
    if not args['email']:
        args['email'] = "{{ environment_admin }}@{{ environment_domain }}"
    args['services'] = format_services(args['services'])

    return args


def main():
    """Updates the file"""
    # Get the args
    args = parse_args()

    # Set up the local repo
    local_repo = create_local_repo(args['domain'])
    all_comp_yaml_init = {
            'compositional_services': args['services'],
            'compositional_portal_admin_email': '{{ environment_email }}',
            }
    all_env_yaml_init = {
            'environment_domain': args['domain'],
            'environment_admin': args['envadmin'],
            'environment_email': args['email'],
            'do_droplet_size': args['dropletsize']
            }

    # Write the initial compositional all.yml file
    comp_path = 'group_vars/compositional'
    with open("{}/{}/all.yml".format(local_repo, comp_path), 'w') as all_comp:
        all_comp.write(yaml.safe_dump(all_comp_yaml_init, default_style=None,
                default_flow_style=False, width=float('inf')))

    # Write the initial environment all.yml file
    with open("{}/group_vars/all/all.yml".format(local_repo), 'w') as all_env:
        all_env.write(yaml.safe_dump(all_env_yaml_init, default_style=None,
                default_flow_style=False, width=float('inf')))

    # Create the master environment vault pass
    if not args['vaultpass']:
        vault_pass = create_pass()
    else:
        vault_pass = args['vaultpass']

    # Add passwords for all of the services that we need
    for service in args['services']:
        create_vaulted_passwords(local_repo, service, vault_pass)

    # Add the mysql and portal passwords too, because we need those always
    for default_service in ['mysql']:
        create_vaulted_passwords(local_repo, default_service, vault_pass)

    put_repo_in_gitlab(local_repo, args['domain'])

    print("Environment {} created!".format(args['domain']))
    if not args['vaultpass']:
        print("Vault Password: {}".format(vault_pass))
        args['vaultpass'] = vault_pass

    #
    # Update the API Token
    #
    # Write the variable redirect to the all.yml file
    #
    with open("{}/{}/all.yml".format(local_repo, comp_path), 'r') as all_comp:
        comp_vars = yaml.safe_load(all_comp.read())
    comp_vars['ourcompose_rundeck_apitoken'] = '{{ vault_ourcompose_rundeck_apitoken }}'
    with open("{}/{}/all.yml".format(local_repo, comp_path), 'w') as all_comp:
        comp_vars = all_comp.write(yaml.safe_dump(comp_vars, default_style=None,
                default_flow_style=False, width=float('inf')))
    #
    # Create new API token
    #
    apitoken = update_apitoken.create_apitoken()
    update_apitoken.add_vaulted_apitoken(args, "{}/{}".format(local_repo,
        comp_path), apitoken)
    update_apitoken.push_repo_to_gitlab(local_repo, args['domain'])

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
