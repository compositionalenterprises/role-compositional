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
        exit


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
    if args['collection_version'].startswith('v'):
        # Build the full tag
        image_tag = build_container_images(args['collection_version'])

        # Build the major version
        maj_ver = '.'.join(args['collection_version'][1:].split('.')[:2])
        image_maj_ver = build_container_images("stable-" + maj_ver)
