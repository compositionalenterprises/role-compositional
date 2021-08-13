import os
import docker
import argparse
import subprocess
from portal_commands_receivable import build_container_image


def build_container_images(collection_version):
    container_image = build_container_image(collection_version,
        'compositionalenterprises')

    try:
        while True:
            line = next(container_image[1])
            print(line)
    except StopIteration:
        return container_image


def build_and_tag(repository, collection_version):
    if collection_version.startswith('v'):
        maj_ver = '.'.join(collection_version[1:].split('.')[:2])
        tags = [collection_version, 'stable-' + maj_ver, 'v' + maj_ver]
        print("Building these tags: {}...".format(tags))
        # Build the full tag
        image_tag = build_container_images(collection_version)
        # Tag that image as stable and minor version
        image_tag[0].tag(
                repository=repository,
                tag='stable-' + maj_ver
                )
        image_tag[0].tag(
                repository=repository,
                tag='v' + maj_ver
                )

        for tag in tags:
            pushed_image_tag = client.images.push(
                    repository=repository,
                    tag=tag,
                    )
            print(pushed_image_tag)

    # TODO: handle master
    elif collection_version == 'master':
        print("Building 'latest' tag...")
        # Build the full tag
        image_tag = build_container_images(collection_version)
        image_tag[0].tag(
                repository=repository,
                tag='latest'
                )
        pushed_image_tag = client.images.push(
                repository=repository,
                tag='latest',
                )
        print(pushed_image_tag)

    elif collection_version == 'update':
        # Master playbooks got updated, so we'll want to update the docker
        # containers (the latest ones at least) with the new playbooks.
        script_dir = os.path.dirname(os.path.realpath(__file__))

        # Get the latest stable version tags. Here we're obviously just getting
        # the return of a command at the heart of it. The command gets all of
        # the branches, and lists the latest three stable branches.
        cmd1 = "git branch -a | grep 'remotes/origin/stable-[0-9.]\+$' | "
        cmd2 = "cut -d '/' -f 3 | tail -n 3"
        stable_branches = subprocess.check_output(cmd1 + cmd2, shell=True,
                text=True, cwd=script_dir).strip().split('\n')))

        # Using that list above, we get the latest tags for those three stable
        # branches.
        print("Updating branches: {}...".format(stable_branches))
        for stable_branch in stable_branches:
            version = stable_branch.split('-')[-1]
            latest_tag = subprocess.check_output(
                "git tag | grep v{} | sort -V | tail -n 1", shell=True,
                text=True, cwd=script_dir
            ).strip()

            # Now, we pass this information back to this same function (yes,
            # it's f'ing recursion) so that we can build the tags one at a time
            # again.
            print("Building updated tags for {}...".format(latest_tag))
            build_and_tag(repository, latest_tag)

    else:
        print("I don't know what to build...")
        exit(1)


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description='''Builds a commands_receivable
            container image''')
    parser.add_argument('-c', '--collection_version',
                        help="The version of the collection to build this for",
                        required=False)

    args = vars(parser.parse_args())

    #
    # Prompt for the args if they were not provided
    #
    while not args['collection_version']:
        args['collection_version'] = input("Collection Version: ")

    return args


if __name__ == '__main__':

    args = parse_args()
    client = docker.from_env()
    repository = 'compositionalenterprises/commands_receivable'
    build_and_tag(repository, args['collection_version'])
