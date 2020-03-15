#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import minio
import common
import getpass
import argparse
import datetime
import requests

BACKUP_URL = 'backups.compositional.enterprise'


def minio_client(args):
    """
    Abstraction to set up a minio client
    """
    client = minio.Minio(BACKUP_URL, access_key=args['apiuser'],
            secret_key=args['apipass'], secure=True)

    return client


def delete_domain_archive(args, archive):
    """
    Deletes an object in the archive.
    """
    pass


def archive_new_snapshot(args):
    """
    Stores the current DigitalOcean snapshot in the archive.
    """
    client = minio_client(args)
    pass


def get_promotion(generation, domain_archives):
    """
    Determine whether or not to promote the generation or not given how much
    time is left before its next expiration.
    """
    timelines = {
            'son': {
                'expiration': datetime.timedelta(days=7),
                'lifespan': datetime.timedelta(days=2),
                }
            'father': {
                'expiration': datetime.timedelta(days=30),
                'lifespan': datetime.timedelta(days=7)
                }
            'grandfather': {
                'expiration': datetime.timedelta(days=90),
                'lifespan': datetime.timedelta(days=30),
                }
            }

    #
    # If after another lifespan we would exceed the expiration, advance the
    # genration.
    #
    # In english, if, after the amount of time that we have in between the
    # renewals for this specific generation, we would actually go past the date
    # that we are trying to guarantee this generation of snapshot should be
    # between, go ahead and rotate it now instead of letting it just go.
    #
    # In ELI5, you can only get milk once a week. If your milk is 3.5 weeks
    # old, and it goes bad once it reaches week 4, go ahead and get new milk
    # now.
    #
    if (domain_archives[generation]['datetime'] +
            timelines[generation]['lifespan'] >=
            timelines[generation]['expiration']):
        return True

    return False


def get_archives(args, bucket):
    """Gets the snapshots that are currently archived"""

    # Add a date field to the entries that parses the name
    # This is mostly for convenience's sake so that we can do date comparison
    # without having to always do this parsing later on in the script
    for archive in dict(archives):
        datestr = archives[archive]['name'].split('--')[0]
        dateobj = datetime.datetime.strptime(datestr, '%Y-%m-%d-%H-%M-%S')
        archives[archive]['datetime'] = dateobj

    return archives


def archive_snapshots(args):
    """
    Archives the snapshots.

    We're working off of a "Son, Father, Grandfather" type model.
    That means that we're going to have a freqently updating Son snapshot,
    a less frequently updating Father snapshot, and a rarely updating
    Grandfather sanpshot. This allows us to restore to an appropriate point in
    time regardless of the need.

    To start out, we'll be putting relatively arbitrary time measurements on
    this to determine how long to keep the archives. The Son will be a weekly
    backup, the Father a quarterly backup, and the Grandfather a quarterly
    backup.

    What this script is going to be doing (the heavy lifting is in this
    section), is to replace the Son every week so that it's between 0 and 7
    days old, replace the Father whenever it's less than 7 days away from being
    4 weeks old, so that it's between 7 days and 4 weeks old and at any given
    time, and replace the Grandfather whenever it's less than 1 week away from
    becoming 3 months old, so that at any given time it's between 1 and 3
    months old.

    This ensures that we have:
        - One backup between 1 and 7 days old
        - One backup between 1 and 4 weeks old
        - One backup between 1 and 3 months old

    I can't think of a better systems right now, so this'll have to do for now.
    """
    bucket = get_bucket(args)

    # Returns a list that looks like this:
    #
    #   [
    #       {
    #           'domain': 'andrewcz.com',
    #           'datetime': 'datetime.datetime(2020, 01, 01, 01, 01, 01)'
    #           'object': '2020-01-01-01-01-01--andrewcz-com'
    #       },
    #       {
    #           'domain': 'andrewcz.com',
    #           'datetime': 'datetime.datetime(2020, 01, 01, 01, 01, 02)'
    #           'object': '2020-01-01-01-01-02--andrewcz-com'
    #       }
    #    ]
    #
    archives = get_archives(args, bucket)

    #
    # Get a dict of archives for this domain that specify which one is the son,
    # the father, and the grandfather.
    #
    domain_archives = {'son': {}, 'father': {}, 'grandfather': {}}
    datetime_now = datetime.datetime.now()
    for archive in archives:
        if archive['domain'] == args['domain']:
            datetime_diff = datetime_now - archive['datetime']
            if datetime_diff.days < 30:
                domain_archives['son'] = archive
            elif datetime_diff.days > 30 and datetime_diff.days < 90:
                domain_archives['father'] = archive
            else:
                domain_archives['grandfather'] = archive

    #
    # Determine whether or not the snapshot needs to be promoted to the next
    # generation yet.
    #
    lineage = ('grandfather', 'father', 'son')
    for generation in lineage:
        # Returns a bool
        promotion = get_promotion(generation, domain_archives)
        if promotion and generation != 'son':
            # Change the archive to reflect the change after the promotion
            new_generation = domain_archives[lineage.index(generation) + 1]
            domain_archives[generation] = new_generation
        elif promotion and generation == 'son'
            # Store the current DigitalOcean snapshot as it is due to become
            # the latest snapshot of the son generation
            domain_archives[generation] = archive_new_snapshot(args)

    #
    # Set up the results and start storing the current generations
    #
    results = {}
    results['current'] = domain_archives
    results['delete'] = {}
    #
    # Delete any snapshots that aren't specified as either a son, father or
    # grandfather generation, and show that in the results
    #
    archive_objects = [domain_archive['object'] for domain_archive in
                domain_archives]
    for archive in archives:
        if (archive['domain'] == args['domain'] and
                archive['object'] not in archive_objects):
            delete_domain_archive(args, archive)
            results['deleted'].update(archive)

    return results


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Archives droplet snapshots")
    parser.add_argument('-u', '--apiuser',
                        help='The user to connect with to the storage service',
                        required=False)
    parser.add_argument('-p', '--apipass',
                        help='The pass to connect with to the storage service',
                        required=False)
    parser.add_argument('-d', '--domain',
                        help='The domain to work on',
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

    return args


def main():
    """Run the backup"""
    # Get the args
    args = parse_args()

    # Perform the API call
    results = archive_snapshot(args)

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
