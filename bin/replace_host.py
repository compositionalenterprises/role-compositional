#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import yaml
import argparse


def eprint(*args, **kwargs):
    """Works the same as print but outputs to stderr."""
    print(file=sys.stderr, *args, **kwargs)


def json_print(data):
    print(json.dumps(data, indent=4, sort_keys=True))


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Updates an entry in ClouDNS")
    parser.add_argument('-i', '--ipaddress',
                        help="The IP Address to add to this hosts.yml file",
                        required=False)
    parser.add_argument('-f', '--filename',
                        help='The path to the hosts.yml file',
                        required=False)

    args = vars(parser.parse_args())

    #
    # Prompt for the args if they were not provided
    #
    if not args['ipaddress']:
        args['ipaddress'] = input("IP Address: ")
    if not args['filename']:
        args['filename'] = input("Filename: ")

    return args


def main():
    """Updates the file"""
    # Get the args
    args = parse_args()

    #
    # Read the file in
    #
    with open(args['filename'], 'r') as stream:
        try:
            inventory = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            eprint("Could not parse {} as YAML...".format(args['filename']))
            sys.exit(2)

    #
    # Handle the replacement
    #
    # Here we set the ipaddress to a blank string. We will handle that later
    new_host = { args['ipaddress']: '' }
    inventory['all']['children']['compositional']['hosts'] = new_host

    #
    # Write the file back out
    #
    with open(args['filename'], 'w') as outfile:
        yaml_string = yaml.dump(inventory, width=50, indent=2)
        # Replace the blank string with nothing so it outputs correctly
        yaml_string = yaml_string.replace(" ''", '')
        outfile.write(yaml_string)

    print("Updated {} with {}".format(args['filename'], args['ipaddress']))


if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
