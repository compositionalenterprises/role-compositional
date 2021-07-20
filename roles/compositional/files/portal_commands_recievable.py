#!/usr/local/lib/docker/virtualenv/bin/python3 -u

import os
import docker
import socket
import subprocess
from ast import literal_eval
from systemd.daemon import listen_fds;


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
        command = 'ansible-playbook -i localhost, '
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


def ssh_keys(action):
    '''
    Idiot-suseptible way to create and delete ssh keys
    '''
    if action == 'create':
        os.chdir('/root/.ssh')
        subprocess.call('ssh-keygen -t ed25519', shell=True)
    else:
        subprocess.call('rm -rf /root/.ssh/ed25519*', shell=True)


def set_entrypoint_path(container_image):
    # Set the script dict for the options we have to choose amongst.
    scripts = {
        'ubuntu': (
            "#!/bin/bash -e\n"
            "apt-get update\n"
            "DEBIAN_FRONTEND=noninteractive apt-get install -y "
            "git dnsutils python3 libffi-dev libssl-dev python3-dev "
            "python3-distutils python3-pip\n"
            "pip3 install 'ansible>=2.10,<2.11' ansible-vault requests "
            "tabulate packaging\n"
            "git clone https://gitlab.com/compositionalenterprises/"
            "play-compositional.git /var/ansible\n"
            "cd /var/ansible\n"
            "ln -sT /portal_storage/ansible/environment /var/ansible/environment\n"
            "sed -i 's/, plays@.\/.vault_pass//' ansible.cfg\n"
            "rm -rf playbooks/group_vars/\n"
            "echo $VAULT_PASSWORD > environment/.vault_pass\n"
            "ansible-galaxy install -fr requirements.yml\n"
            'exec "$@" \n'
            ),
        'commands_recievable': (
            '#!/bin/bash -e\n'
            "ln -sT /portal_storage/ansible/environment /var/ansible/environment\n"
            "cd /var/ansible\n"
            "echo $VAULT_PASSWORD > environment/.vault_pass\n"
            'exec "$@"'
            )
        }

    # Write out a demo entrypoint script
    os.makedirs('/tmp/entrypoint', exist_ok=True)
    entrypoint_path = '/tmp/entrypoint/entrypoint.sh'
    with open(entrypoint_path, 'w') as entrypoint_script:
        entrypoint_script.write(scripts[container_image])

    st = os.stat(entrypoint_path)
    os.chmod(entrypoint_path, 0o755)


def get_container_image():
    return 'ubuntu:20.04'


def run_docker_command(spec):
    """
    Takes the spec that the server passes us and runs docker-compose based off
    of it.
    """
    client = docker.from_env()
    container_image = get_container_image()
    set_entrypoint_path(container_image.split(':')[0]),
    print('Running Container')
    # TODO Deal with local/remove pathing
    container = client.containers.run(
        image=get_container_image(),
        command=build_command(spec),
        entrypoint='/entrypoint/entrypoint.sh',
        network_mode='host',
        detatch=True,
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
    #ssh_keys('create')
    if os.environ.get("LISTEN_FDS", None) != None:
        systemd_socket_response()
    #ssh_keys('remove')
