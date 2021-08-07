import docker
import argparse
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


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Updates an entry in ClouDNS")
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
    if args['collection_version'].startswith('v'):
        maj_ver = '.'.join(args['collection_version'][1:].split('.')[:2])
        # Build the full tag
        image_tag = build_container_images(args['collection_version'])
        # Tag that image as stable and minor version
        image_tag[0].tag(
                repository=repository,
                tag='stable-' + maj_ver
                )
        image_tag[0].tag(
                repository=repository,
                tag='v' + maj_ver
                )

        tags = [args['collection_version'], 'stable-' + maj_ver, 'v' + maj_ver]
        for tag in tags:
            pushed_image_tag = client.images.push(
                    repository=repository,
                    tag=tag,
                    )
            for line in pushed_image_tag:
                print(line)

    # TODO: handle master
    elif args['collection_version'] == 'master':
        # Build the full tag
        image_tag = build_container_images(args['collection_version'])
        image_tag[0].tag(
                repository=repository,
                tag='latest'
                )
        pushed_image_tag = client.images.push(
                repository=repository,
                tag='latest',
                )
        print(pushed_image_tag:)
            print(line)
