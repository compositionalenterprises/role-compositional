from portal_commands_receivable import build_container_image


def build_container_images():
    container_image = build_container_image('stable-2.7',
        'compositionalenterprises')

    try:
        while True:
            line = next(container_image[1])
            print(line)
    except StopIteration:
        exit

if __name__ == '__main__':
    args = parse_args()

    build_container_images(args)
