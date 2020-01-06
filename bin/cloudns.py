#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import getpass
import argparse
import requests

def eprint(*args, **kwargs):
    """Works the same as print but outputs to stderr."""
    print(file=sys.stderr, *args, **kwargs)


def json_print(data):
    print(json.dumps(data, indent=4, sort_keys=True))


def get_record_id(args):
    url = "https://api.cloudns.net/dns/records.json"

    params = {
            'sub-auth-user': args['apiuser'],
            'auth-password': args['apipass'],
            'domain-name': '.'.join(args['fqdn'].split('.')[1:]),
            'host': args['fqdn'].split('.')[0],
            'type': 'A'
            }
    results = requests.get(url, params=params)

    return results.json()


def change_dns(args):
    """Updates a DNS A record"""
    change_type = args['type']
    if change_type == 'modify':
        change_type = 'mod'
    url = f"https://api.cloudns.net/dns/{change_type}-record.json"
    params = {
            'sub-auth-user': args['apiuser'],
            'auth-password': args['apipass'],
            'domain-name': '.'.join(args['fqdn'].split('.')[1:]),
            }

    if change_type != 'add':
        record_id = get_record_id(args)
        if len(record_id) > 1:
            eprint("Found more than one matching DNS entry. Check your records.")
            sys.exit(2)
        # This is us getting the only key that was returned in the dictionary
        params['record-id'] = list(record_id.keys())[0]
    else:
        params['record-type'] = 'A'

    if change_type != 'delete':
        params['host'] = args['fqdn'].split('.')[0]
        params['record'] = args['address']
        params['ttl'] = '900'

    # Make the API call to POST
    results = requests.post(url, params=params)

    return results.json()


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Updates an entry in ClouDNS")
    parser.add_argument('-u', '--apiuser',
                        help='The user to connect with to ClouDNS',
                        required=False)
    parser.add_argument('-p', '--apipass',
                        help='The pass to connect with to ClouDNS',
                        required=False)
    parser.add_argument('-f', '--fqdn',
                        help='The FQDN to change',
                        required=False)
    parser.add_argument('-a', '--address',
                        help='The IP Address to use for the change',
                        required=False)
    parser.add_argument('-t', '--type',
                        help='The type of change to make (add, delete, modify)',
                        required=False)

    args = vars(parser.parse_args())

    #
    # Prompt for the args if they were not provided
    #
    if not args['apiuser']:
        args['apiuser'] = input("Username: ")
    if not args['apipass']:
        args['apipass'] = getpass.getpass("Password: ")
    if not args['fqdn']:
        args['fqdn'] = input("FQDN: ")
    while not args['type'] or args['type'] not in ['add', 'delete', 'modify']:
        if args['type']:
            eprint("Invalid Type... Please try again...")
        args['type'] = input("Change Type (add, delete, modify): ")
    if not args['address'] and args['type'] != 'delete':
        args['address'] = input("IP Address: ")

    return args


def main():
    """Run the update"""
    # Get the args
    args = parse_args()

    # Perform the API call
    results = change_dns(args)

    # Display the results
    json_print(results)

if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
