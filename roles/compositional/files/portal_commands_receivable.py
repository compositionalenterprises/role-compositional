#!/usr/local/lib/docker/virtualenv/bin/python3 -u

import os
import docker
import socket
import subprocess
from ast import literal_eval


def build_command(spec):
    """
    Spec should come in with at least one key, 'script'. This is the path to
    the script that we should run. That will also let us determine whether we
    are going to be running a python script or an ansible playbook.
    """
    # Start the command string here
    command = ''

    # Here we add the ansible-playbook command if it's an ansible run.
    # Otherwise, all of our python scripts have their shebang set up.
    #
    # Also, we add the format for the extra args
    if spec['script'].split('/')[0] == 'playbooks':
        command = 'ansible-playbook --private-key ~/.ssh/commands_receivable -i localhost, '
        args_format = " -e {}={}"
    else:
        # This requires us to choose whether we enforce flag or switch passing
        # of arguments. At this point, since flags are going to be more
        # descriptive, let's use those.
        args_format = " --{} {}"


    # Add the script name
    command = command + spec['script']

    # Parse the args
    if 'args' in spec:
        for arg in spec['args']:
            command = command + args_format.format(arg, spec['args'][arg])

    command = command.split(' ')

    return command


def set_entrypoint_path():
    # Set the script dict for the options we have to choose amongst.
    lines = [
        '#!/bin/bash -e\n',
        "ln -sT /portal_storage/ansible/environment "
        "/var/ansible/environment\n",
        "cd /var/ansible\n",
        "echo $VAULT_PASSWORD > environment/.vault_pass\n",
        'exec "$@"\n'
        ]

    # Write out a demo entrypoint script
    os.makedirs('/tmp/entrypoint', exist_ok=True)
    entrypoint_path = '/tmp/entrypoint/entrypoint.sh'
    with open(entrypoint_path, 'w') as entrypoint_script:
        for line in lines:
            entrypoint_script.write(line)

    st = os.stat(entrypoint_path)
    os.chmod(entrypoint_path, 0o755)

    return entrypoint_path

def build_container_image(collection_version, build_target):
    os.makedirs('/tmp/docker_build', exist_ok=True)
    dockerfile_path = '/tmp/docker_build/Dockerfile'
    with open(dockerfile_path, 'w') as dockerfile:
        dockerfile.write(
            "FROM ubuntu:20.04\n"
            "ENV DEBIAN_FRONTEND=noninteractive\n"
            "RUN apt-get update && \\\n"
            "    apt-get install -y "
            "git dnsutils python3 libffi-dev libssl-dev python3-dev "
            "python3-distutils python3-pip && \\\n"
            "    pip3 install 'ansible>=2.10,<2.11' ansible-vault requests "
            "tabulate packaging && \\\n"
            "    git clone https://gitlab.com/compositionalenterprises/"
            "play-compositional.git /var/ansible\n"
            "WORKDIR /var/ansible \n"
            "RUN sed -i 's/, plays@.\/.vault_pass//' ansible.cfg && \\\n"
            "    rm -rf playbooks/group_vars/ && \\\n"
            "    sed -i 's/version: master/version: "
            f"{collection_version}/' requirements.yml && \\\n"
            "    ansible-galaxy install -fr requirements.yml\n"
            )

    client = docker.from_env()
    container_image = client.images.build(
            path='/tmp/docker_build',
            tag="{}/commands_receivable:{}".format(
                build_target, collection_version),
            pull=True,
            # TODO: buildargs instead of f-string above?
            )

    return container_image

def get_container_image(spec):
    # TODO: Test for image present:
    #
    #   ➜  ~ docker images -q mariadb:latest
    #        e76a4b2ed1b4
    #   ➜  ~ docker images -q mariadb:1.10
    #   ➜  ~ echo $?
    #   0

    # TODO: Test for spec passed something for us to auth to the docker
    # registry with
    try:
        client = docker.from_env()
        client.images.pull(
                repository='compositionalenterprises/commands_receivable',
                tag=spec['collection_version']
                )
        return 'compositionalenterprises/commands_receivable:{}'.format(
                spec['collection_version'])
    except docker.errors.APIERROR:
        build_container_image(spec['collection_version'], 'local')
        return "local/commands_receivable:{}".format(
                spec['collection_version'])


def run_docker_command(spec):
    """
    Takes the spec that the server passes us and runs docker-compose based off
    of it.
    """
    client = docker.from_env()
    print('Running Container')
    # TODO Deal with local/remove pathing
    container = client.containers.run(
        image=get_container_image(spec),
        command=build_command(spec),
        entrypoint=set_entrypoint_path(),
        network_mode='host',
        detach=True,
        stream=True,
        environment={
            'VAULT_PASSWORD': spec['vault_password']
            },
        volumes={
            '/srv/local/portal_storage/': {
                'bind': '/portal_storage',
                'mode': 'rw'
                },
            '/root/.ssh/': {
                'bind': '/root/.ssh',
                'mode': 'ro'
                },
            '/tmp/entrypoint/': {
                'bind': '/entrypoint',
                'mode': 'ro'
                }
            },
        )

    return container

def systemd_socket_response():
    """
    Accepts every connection of the listen socket provided by systemd, send the
    HTTP Response 'OK' back.
    """
    try:
        fds = listen_fds()
    except ImportError:
        fds = [3]

    for fd in fds:
        with socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0)

            try:
                conn, addr = sock.accept()
                with conn:
                    fragments = []
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        fragments.append(data)
                    # We are expecting at least the following here:
                    #
                    # {
                    #     'vault_password': str(), # Required
                    #     'script': str(), # Required
                    #     'args': dict(), # Optional
                    #     'collection_version': str(), # Required
                    # }
                    spec_bytes = b''.join(fragments)
                    spec = literal_eval(spec_bytes.decode('utf8'))
                    conn.sendall(b'Executing...')
                    print('Executing...')
                    container = run_docker_command(spec)
                    container_logs = container.logs(stream=True, follow=True)
                    try:
                        while True:
                            line = next(container_logs)
                            print(line)
                            conn.send(line)
                    except StopIteration:
                        pass
                    conn.sendall(b'Executed...')
                    print('Executed...')
            except socket.timeout:
                pass
            except OSError as e:
                # Connection closed again? Don't care, we just do our job.
                print(e)

if __name__ == "__main__":
    from systemd.daemon import listen_fds;
    if os.environ.get("LISTEN_FDS", None) != None:
        systemd_socket_response()
