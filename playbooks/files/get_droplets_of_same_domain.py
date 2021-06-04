#!/usr/bin/env python3

import sys
import getpass
import argparse
import requests

DO_API_ENDPOINT = 'https://api.digitalocean.com/v2'
DO_TIMEOUT = 60


def eprint(*args, **kwargs):
    """Works the same as print, but outputs to stderr."""
    print(*args, file=sys.stderr, **kwargs)

def main(parser):
    args = vars(parser.parse_args())

    if not args['token']:
        args['token'] = getpass.getpass("DigitalOcean OAuth API Token: ")

    do_headers = {'Authorization': 'Bearer {0}'.format(args['token']),
                  'Content-type': 'application/json'}

    droplets_url = DO_API_ENDPOINT + '/droplets/'
    resp_data = {}
    incomplete = True
    while incomplete:
        resp = requests.get(droplets_url, headers=do_headers, timeout=DO_TIMEOUT)
        json_resp = resp.json()

        for key, value in json_resp.items():
            if isinstance(value, list) and key in resp_data:
                resp_data[key] += value
            else:
                resp_data[key] = value

        try:
            url = json_resp['links']['pages']['next']
        except KeyError:
            incomplete = False

    for droplet in resp_data['droplets']:
        print("{} {}".format(droplet['name'], droplet['id']))


def parse_args():
    parser = argparse.ArgumentParser(description="""Gets the details of droplets
            in DigitalOcean""")
    parser.add_argument('--token',
                        help="The DigitalOcean OAuth API Token")
    return parser


if __name__ == '__main__':

    #
    # Handle ^C without throwing an exception
    #
    try:
        main(parse_args())
    except KeyboardInterrupt:
        raise SystemExit
