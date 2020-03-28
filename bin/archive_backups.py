#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import common
import argparse
import datetime


def get_promotion(args, generation, domain_backups):
    """
    Determine whether or not to promote the generation or not given how much
    time is left before its next expiration.
    """
    lifespan = datetime.timedelta(days=args['interval'])
    expirations = {
            'son': datetime.timedelta(days=7),
            'father': datetime.timedelta(days=30),
            'grandfather': datetime.timedelta(days=90)
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
    domain_backup = get_backups([domain_backups[generation]])
    backup_datetime = domain_backup[domain_backups[generation]]
    expiration_date = backup_datetime + expirations[generation]
    expiration_delta = expiration_date - datetime.datetime.now()
    common.eprint("In another {} days, {} will expire."
             .format(expiration_delta.days, generation))
    if datetime.datetime.now() + lifespan >= expiration_date:
        common.eprint('Which means we need to promote its replacement now.')
        return True

    return False


def get_backups(backup_objects):
    """Gets the snapshots that are currently archived"""
    # We will ultimately be returning a dict
    backups = {}

    #
    # Add a date field to the entries that parses the name
    # This is mostly for convenience's sake so that we can do date comparison
    # without having to always do this parsing later on in the script
    #
    for backup_object in backup_objects:
        # Get the date string
        datestr = backup_object.split('--')[1].split('.')[0]
        dateobj = datetime.datetime.strptime(datestr, '%Y-%m-%d-%H-%M')
        backups[backup_object] = dateobj

    return backups


def get_results(args, backups):
    """
    Determines what the end result of the backups should be.

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

    I can't think of a better system right now, so this'll have to do for now.

    We will be receiving the backups var in the following format:
    """
    #
    # Get a dict of backups for this domain that specify which one is the son,
    # the father, and the grandfather.
    #
    domain_backups = {}
    datetime_now = datetime.datetime.now()
    for backup in backups:
        datetime_diff = datetime_now - backups[backup]
        if datetime_diff.days < 7:
            domain_backups['son'] = backup
        elif datetime_diff.days > 7 and datetime_diff.days < 30:
            domain_backups['father'] = backup
        else:
            domain_backups['grandfather'] = backup

    common.eprint("The current backups are: {}".format(domain_backups))
    #
    # Determine whether or not the snapshot needs to be promoted to the next
    # generation yet.
    #
    lineage = ('grandfather', 'father', 'son')
    common.eprint("The generations will be checked again in {} days"
             .format(args['interval']))
    for generation in lineage:
        if not generation in domain_backups:
            # We don't have a backup that's old enough for this generation yet
            continue
        # Returns a bool
        promotion = get_promotion(args, generation, domain_backups)
        if promotion and generation != 'son':
            # Change the archive to reflect the change after the promotion
            replacement = lineage[lineage.index(generation) + 1]
            new_generation = domain_backups[replacement]
            domain_backups[generation] = new_generation
        elif promotion and generation == 'son':
            # Store a current backup as it is due to become the latest snapshot
            # of the son generation
            domain_backups['son'] = args['newbackup']

    #
    # Set up the results and start storing the current generations
    #
    results = {}
    results['keep'] = domain_backups
    results['delete'] = []

    #
    # Delete any snapshots that aren't specified as either a son, father or
    # grandfather generation, and show that in the results
    #
    for backup in backups:
        if backup not in list(domain_backups.values()):
            results['delete'].append(backup)

    return results


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Archives droplet snapshots")
    parser.add_argument('-b', '--backups',
                        help='''The comma-separated list of backups that are
                        already present''',
                        required=False)
    parser.add_argument('-n', '--newbackup',
                        help='The new backup that we could add if we need to',
                        required=False)
    parser.add_argument('-i', '--interval',
                        help='''The interval which we are scheduled to check
                        again in days''',
                        required=False)

    args = vars(parser.parse_args())

    args['interval'] = int(args['interval'])

    return args


def main():
    """
    Make the determination of what needs to be done
    """
    # Get the args
    args = parse_args()

    #
    # Returns a list that looks like this:
    #
    #   {
    #       'andrewcz-com--2020-01-01-01-01-01.tar.gz': 'datetime.datetime(2020, 01, 01, 01, 01, 01)',
    #       'andrewcz-com--2020-01-01-01-01-02.tar.gz': 'datetime.datetime(2020, 01, 01, 01, 01, 02)'
    #   }
    #
    if len(args['backups'].split(',')[0]) > 0:
        # If there are any backups there to get, get them now
        backups = get_backups(args['backups'].split(','))
        # Perform the API call
        results = get_results(args, backups)
    else:
        # This is the first backup we've attempted to take
        # Create a skeleton results dict
        results = {}
        results['keep'] = {}
        results['keep']['son'] = args['newbackup']
        results['delete'] = []

    # Pretty print the results to stderr
    common.json_eprint(results)
    # Output the results in parsable json, which includes surrounding
    # double-quotes
    print('"{}"'.format(results))

if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
