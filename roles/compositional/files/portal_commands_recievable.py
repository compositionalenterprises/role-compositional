#!/usr/local/bin/python3-docker -u

import os
import ast
import socket
import docker
import subprocess
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
        command = 'ansible-playbook -i environment/hosts.yml '
        args_format = " -e {}={}"
    else:
        # This requires us to choose whether we enforce flag or switch passing
        # of arguments. At this point, since flags are going to be more
        # descriptive, let's use those.
        args_format = " --{} {}"


    # Add the script name
    command = command + spec['script']

    # Parse the args
    for arg in spec['args']:
        command = command + args_format.format(arg, spec['args'][arg])

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
        ubuntu: """
            apt-get update
            apt-get install -y git dnsutils python3.6 libffi-dev libssl-dev python3.6-dev python3-distutils
            unlink /usr/bin/python3
            ln -sT /usr/bin/python3.6 /usr/bin/python3
            curl https://bootstrap.pypa.io/get-pip.py | python3.6
            pip3 install ansible==2.10 ansible-vault ansible-galaxy requests tabulate packaging
            mkdir /var/ansible
            ln -sT /environment /var/ansible/environment
            git clone https://gitlab.com/compositionalenterprises/play-compositional.git /var/ansible
            cd /var/ansible
            sed 's/, plays@.\/.vault_pass//' ansible.cfg
            rm -rf playbooks/group_vars/
            ansible-galaxy install -fr requirements.yml
        """,
        commands_recievable: """
            ln -sT /environment /var/ansible/environment
            cd /var/ansible
        """
        }

    # Write out a demo entrypoint script
    os.mkdir('/tmp/entrypoint')
    entrypoint_path = '/tmp/entrypoint/entrypoint.sh'
    with open(entrypoint_path, 'w') as entrypoint_script:
        entrypoint_script.write(scripts[container_image])


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
    client.containers.run(
        image=get_container_image(),
        command=build_command(spec),
        stream=True,
        entrypoint='/entrypoint/entrypoint.sh',
        volumes={
            # TODO Deal with local/remove pathing
            '/srv/local/portal_env/': {
                'bind': '/environment',
                'mode': 'ro'
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
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0)

        try:
            while True:
                conn, addr = sock.accept()
                fragments = []
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    fragments.append(chunk)
                spec_bytes = b''.join(fragments)
                spec = literal_eval(spec_bytes.decode('utf8'))
                conn.sendall(b'Executing...')
                run_command(spec)
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 3\r\n\r\nOK\n")
        except socket.timeout:
            pass
        except OSError as e:
            # Connection closed again? Don't care, we just do our job.
            print(e)

if __name__ == "__main__":
    ssh_keys('create')
    if os.environ.get("LISTEN_FDS", None) != None:
        systemd_socket_response()
    ssh_keys('remove')
