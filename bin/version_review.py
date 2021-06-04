#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import csv
import sys
import time
import yaml
import common
import shutil
import argparse
import requests
import tabulate
import traceback
import subprocess
from packaging import version


def get_latest_bugfix_version(bugfix_versions):
    version_strings = []
    for bugfix_version in bugfix_versions:
        common.eprint("Checking this bugfix version: {}".format(
            bugfix_version['name']))
        found_version_string = re.search('\d+\.\d+',
                bugfix_version['name'])
        common.eprint("Found this version string: {}".format(
            found_version_string.group()))
        version_strings.append(found_version_string.group())

    bugfix_version_string = sorted(version_strings)[-1]
    common.eprint("Looking for string: {}".format(bugfix_version_string))
    bugfix_version_tags = [bugfix_version['name'] for bugfix_version in
            bugfix_versions if re.search(bugfix_version_string,
                bugfix_version['name'])]

    if len(bugfix_version_tags) == 0:
        common.eprint("Could not find the string that we just matched with!!!")
        return bugfix_version_string
    elif len(bugfix_version_tags) == 1:
        best_bugfix_version = [bugfix_version for bugfix_version in
                bugfix_versions if bugfix_version['name'] ==
                bugfix_version_tags[0]][0]
        return best_bugfix_version
    else:
        common.eprint("Checking tag names: {}".format(bugfix_version_tags))
        best_bugfix_version_name = get_best_version(bugfix_version_tags)
        common.eprint("Best name is: {}".format(best_bugfix_version_name))
        best_bugfix_version = [bugfix_version for bugfix_version in
                bugfix_versions if bugfix_version['name'] ==
                best_bugfix_version_name][0]
        return best_bugfix_version


def get_latest_minor_version(minor_versions):
    version_strings = []
    for minor_version in minor_versions:
        # Here we're only looking for the string that matches the minor
        # version, since we weeded out any false positives earlier on by
        # excluding anything that was simply part of a bugfix version.
        common.eprint("Checking this minor version: {}".format(
            minor_version['name']))
        found_version_string = re.search('\d+\.\d+',
                minor_version['name'])
        common.eprint("Found this version string: {}".format(
            found_version_string.group()))
        version_strings.append(found_version_string.group())

    minor_version_string = sorted(version_strings)[-1]
    common.eprint("Looking for string: {}".format(minor_version_string))
    minor_version_tags = [minor_version['name'] for minor_version in
            minor_versions if re.search(minor_version_string,
                minor_version['name'])]

    if len(minor_version_tags) == 0:
        common.eprint("Could not find the string that we just matched with!!!")
        return minor_version_string
    elif len(minor_version_tags) == 1:
        best_minor_version = [minor_version for minor_version in
                minor_versions if minor_version['name'] ==
                minor_version_tags[0]][0]
        return best_minor_version
    else:
        common.eprint("Checking tag names: {}".format(minor_version_tags))
        best_minor_version_name = get_best_version(minor_version_tags)
        common.eprint("Best name is: {}".format(best_minor_version_name))
        best_minor_version = [minor_version for minor_version in
                minor_versions if minor_version['name'] ==
                best_minor_version_name][0]
        return best_minor_version


def get_best_version(versions):
    #
    # Try to find the best minor version candidate
    #
    # Try to incrementally refine the list of matches to get to something
    # that looks the most like a typical versioning scheme
    #
    # Exclude everything with letters
    versions_no_letters = [version for version in versions if not
            re.search('[a-zA-Z]', version)]
    if len(versions_no_letters) == 1:
        common.eprint("Choosing {} since it has no letters".format(
            versions_no_letters[0]))
        return versions_no_letters[0]
    else:
        # Exclude only everything with dashes
        versions_no_dashes = [version for version in versions if
                not re.search('-', version)]
        if len(versions_no_dashes) == 1:
            common.eprint("Choosing {} since it has no dashes".format(
                versions_no_dashes[0]))
            return versions_no_dashes[0]
        else:
            # Exclude only everything with a prefix
            versions_no_prefix = [version for version in versions
                    if not re.search('^\D', version)]
            if len(versions_no_prefix) == 1:
                common.eprint("Choosing {} since it has no prefix".format(
                    versions_no_prefix[0]))
                return versions_no_prefix[0]
            else:
                common.eprint("Could not find an ideal version")
                return sorted(versions)[0]


def report(service_versions):
    common.json_print(service_versions)
    common.eprint("We should do some comparisons here.")

    for service_version_key in service_versions.keys():
        # Skip comparing latest against the branches, since we're doing this
        # to explicitly compare it in the opposite direction
        if service_version_key == 'latest':
            continue
        else:
            common.eprint("Checking out {}".format(service_version_key))

        for service in service_versions[service_version_key]:
            service_version = service_versions[service_version_key][service]
            service_version = re.sub('[a-zA-Z-]', '', service_version)
            try:
                common.eprint("For {}, comparing {} to {}".format(service,
                    service_version, service_versions['latest'][service]))
                # start comparing minor versions
                if not service_version.count('.') > 1:
                    if service_versions['latest'][service]['minor']:
                        common.eprint("Using Minor Version")
                        minor_version = service_versions['latest'][service]['minor']
                        minor_version = re.sub('[a-zA-Z-]', '', minor_version)
                        comparable_version = float(minor_version)
                    else:
                        common.eprint("Using Bugfix Version")
                        bugfix_version = service_versions['latest'][service]['bugfix']
                        bugfix_version = re.sub('[a-zA-Z-]', '', bugfix_version)
                        comparable_version = float('.'.join(
                            bugfix_version.split('.')[:2]))
                    common.eprint("Comparable Version: {}".format(comparable_version))
                    if int(service_version.split('.')[0]) < int(
                            str(comparable_version).split('.')[0]):
                        warning = "WARNING: Major Version Discrepancy"
                        common.eprint(warning.format(service_version_key))
                    elif float(service_version) < comparable_version:
                        if float(service_version) - comparable_version > 1:
                            warning = "WARNING: Major Version Discrepancy"
                            common.eprint(warning.format(service_version_key))
                        else:
                            warning = "WARNING: Minor Version Discrepancy"
                            common.eprint(warning.format(service_version_key))
                else:
                    minor_service_version = float('.'.join(
                            service_version.split('.')[:2]))
                    bugfix_version = service_versions['latest'][service]['bugfix']
                    bugfix_version = re.sub('[a-zA-Z-]', '', bugfix_version)
                    comparable_version = float('.'.join(
                            bugfix_version.split('.')[:2]))
                    if int(service_version.split('.')[0]) < int(
                            bugfix_version.split('.')[0]):
                        warning = "WARNING: Major Version Discrepancy"
                        common.eprint(warning.format(service_version_key))
                    elif minor_service_version < comparable_version:
                        warning = "WARNING: Minor Version Discrepancy"
                        common.eprint(warning.format(service_version_key))
                    elif int(service_version.split('.')[-1]) < int(
                            bugfix_version.split('.')[-1]):
                        warning = "WARNING: Bugfix Version Discrepancy"
                        common.eprint(warning.format(service_version_key))
            except KeyError:
                common.eprint(
                        "Could not find latest version tag for {}".format(
                            service))


    tabulate_table = []
    with open("/tmp/report.csv", 'w') as csvfile:
        writer = csv.writer(csvfile)
        all_service_versions = [service_version_key for service_version_key in
                service_versions.keys()]
        all_service_versions.reverse()
        writer.writerow(['Service\\Tag'] + all_service_versions)
        for service in common.SERVICES.keys():
            this_service_versions = []
            for all_service_version in all_service_versions:
                try:
                    this_service_version = service_versions[
                            all_service_version][service]
                    if isinstance(this_service_version, dict):
                        if this_service_version['bugfix']:
                            this_service_versions.append(
                                    this_service_version['bugfix'])
                        elif this_service_version['minor']:
                            this_service_versions.append(
                                    this_service_version['minor'])
                        else:
                            this_service_versions.append('')
                            common.eprint("Could not find {} for {}".format(
                                all_service_version, service))
                    else:
                        this_service_versions.append(this_service_version)

                except KeyError:
                    common.eprint(
                            "Could not find {} version tag for {}".format(
                                all_service_version, service))
                    this_service_versions.append('')
            writer.writerow([service] + this_service_versions)
            tabulate_table.append([service] + this_service_versions)

    headers = [service_version_key for service_version_key in
            service_versions.keys()]
    headers.reverse()
    headers.insert(0, 'Service')
    print("\n\n")
    print(tabulate.tabulate(tabulate_table, headers, tablefmt='github'))

    # TODO: Email out the csv file, and clean up after ourselves.

    # TODO: if any of the services are running on an earlier minor version
    # that the latest (e.g. 3.2.1 when the latest is 3.3.3), do a check to make
    # sure that they're running the latest of the bugfix version of that minor
    # release (e.g. 3.2.3 when they're running 3.2.1) At that point, we should
    # report that we are not on the latest bugfix version of that minor release

    # TODO: report on the difference in versions if we are running an older
    # minor release than what is available on master.

    # TODO: report on if we are running the correct minor release, but are
    # running on an older bugfix version on master.

    # TODO: get all available release notes (links are preferable) to versions
    # of things that we have not yet upgraded to


def get_latest_tag(registry):
    url = common.REGISTRY_SOURCES[registry['source']]['tags']
    page_count = 1
    request = requests.get(url.format(registry['path'], page_count))

    try:
        tags = request.json()['results']
        while request.json()['next']:
            page_count += 1
            request = requests.get(url.format(registry['path'], page_count))
            if 'detail' in request.json().keys():
                common.eprint("Exceeded the rate limit. Sleeping...")
                time.sleep(30)
                request = requests.get(url.format(registry['path'], page_count))
            tags.extend(request.json()['results'])
    except KeyError as e:
        common.eprint("Could not find registry.")
        return False

    latest_tags = [tag for tag in tags if tag['name'] == 'latest']
    latest_tag_names = {}

    if len(latest_tags) == 0:
        #
        # This is a hacky work-around for beta testing where we just
        # get the first tag, or skip if we aren't able to get it.
        #
        #
        common.eprint('Could not find tag named latest')
        if request.status_code == 200 and len(tags) > 0:
            # Get anything that has a minor version or bugfix version in their
            # strings
            latest_tag_name = {}
            minor_version = re.compile('[^\.]\d+\.\d+(^\.|$)')
            minor_versions = [tag for tag in tags if minor_version.search(
                tag['name'])]
            if len(minor_versions) == 1:
                latest_tag_name['minor'] = minor_versions[0]['name']
            elif len(minor_versions) > 1:
                latest_minor_version = get_latest_minor_version(minor_versions)
                latest_tag_name['minor'] = latest_minor_version['name']
            else:
                common.eprint("Could not find any minor version tags.")

            # Do the same thing, but with bugfix versions
            bugfix_version = re.compile('\d+\.\d+\.\d+')
            bugfix_versions = [tag for tag in tags if bugfix_version.search(
                tag['name'])]
            if len(bugfix_versions) == 1:
                latest_tag_name['bugfix'] = bugfix_versions[0]['name']
            elif len(bugfix_versions) > 1:
                latest_bugfix_version = get_latest_bugfix_version(bugfix_versions)
                latest_tag_name['bugfix'] = latest_bugfix_version['name']
            else:
                common.eprint("Could not find any bugfix version tags.")

            # Return false if we couldn't find any matches
            if len(latest_tag_name) == 0:
                common.eprint("Could not find bugfix or minor version tags")
                return False
        else:
            common.eprint("ERROR: Failed to parse registry tags.")
            return False
    elif len(latest_tags) > 1:
        common.eprint("There should never be more than one 'latest' tag")
        return False
    else:
        # Get latest tag version here based on the sha hash, and get the
        # actual version name that this 'latest' tag is pointing to
        if len(latest_tags[0]['images']) > 1:
            common.eprint("WARNING: More than 1 image tagged with latest")
        for image in latest_tags[0]['images']:
            if image['architecture'] == 'amd64':
                latest_image_digest = image['digest']
        latest_tag_names = [tag['name'] for tag in tags if any(
            image.get('digest', False) == latest_image_digest for image in tag['images'])
            and tag['name'] != 'latest']

        if len(latest_tag_names) > 1:
            common.eprint(
                    "More than 1 image with same sha as latest: {}".format(
                        latest_tag_names)
                    )

            # Find any versions of latest that look like minor versions or
            # bugfix versions
            minor_version = re.compile('\d+\.\d+(\D|$)')
            minor_versions = []
            bugfix_version = re.compile('\d+\.\d+\.\d+(\D|$)')
            bugfix_versions = []
            for latest_tag_name in latest_tag_names:
                if bugfix_version.search(latest_tag_name):
                    common.eprint("{} looks like a bugfix version".format(
                            latest_tag_name))
                    bugfix_versions.append(latest_tag_name)
                elif minor_version.search(latest_tag_name):
                    common.eprint("{} looks like a minor version".format(
                            latest_tag_name))
                    minor_versions.append(latest_tag_name)

            latest_tag_name = {}
            if len(bugfix_versions) > 1:
                latest_tag_name['bugfix'] = get_best_version(bugfix_versions)
            elif len(bugfix_versions) == 1:
                latest_tag_name['bugfix'] = bugfix_versions[0]

            if len(minor_versions) > 1:
                latest_tag_name['minor'] = get_best_version(minor_versions)
            elif len(minor_versions) == 1:
                latest_tag_name['minor'] = minor_versions[0]

        elif len(latest_tag_names) == 1:
            common.eprint("Only one matching tag: {}".format(
                    latest_tag_names[0]))
            if latest_tag_names[0].count('.') == 2:
                latest_tag_type = 'bugfix'
                found_version = True
            elif latest_tag_names[0].count('.') == 1:
                latest_tag_type = 'minor'
                found_version = True
            elif latest_tag_names[0].count('.') == 0 and not re.search(
                    '[a-z]', latest_tag_names[0]):
                latest_tag_names[0] = "{}.0".format(latest_tag_names[0])
                latest_tag_type = 'minor'
                found_version = True
            else:
                common.eprint("""Could not identify {} as a major, minor, or
                        bugfix version""".format(latest_tag_names[0]))
                latest_tag_name = {}
                found_version = False

            # We were able to find either a major, minor, or bugfix version
            if found_version:
                latest_tag_name = {}
                latest_tag_name[latest_tag_type] = latest_tag_names[0]
        elif len(latest_tag_names) == 0:
            # Implement a way to check for latest tags by semantic
            # versioning
            common.eprint("WARNING: No matching other tags!!!")
            minor_version_regex = re.compile('\d+\.\d+(\D|$)')
            all_minor_versions = []
            bugfix_version_regex = re.compile('\d+\.\d+\.\d+(\D|$)')
            all_bugfix_versions = []
            for tag_name in [tag['name'] for tag in tags]:
                if (bugfix_version_regex.search(tag_name) and not
                        tag_name in all_bugfix_versions):
                    common.eprint("{} looks like a bugfix version".format(
                            tag_name))
                    all_bugfix_versions.append(tag_name)
                elif (minor_version_regex.search(tag_name) and not
                        tag_name in all_bugfix_versions):
                    common.eprint("{} looks like a minor version".format(
                            tag_name))
                    all_minor_versions.append(tag_name)

            # Get the raw/trimmed versions of the regex matches, a.k.a the
            # 3.9.1 out of a tag that is named demo_3.9.1-stable-beta2
            trimmed_minor_versions = []
            trimmed_bugfix_versions = []
            for bugfix_version in all_bugfix_versions:
                trimmed_bugfix_version = bugfix_version_regex.search(
                        bugfix_version)
                if not trimmed_bugfix_version.group() in trimmed_bugfix_versions:
                    trimmed_bugfix_versions.append(
                            trimmed_bugfix_version.group())

            for minor_version in all_minor_versions:
                trimmed_minor_version = minor_version_regex.search(
                        minor_version)
                if not trimmed_minor_version.group() in trimmed_minor_versions:
                    trimmed_minor_versions.append(trimmed_minor_version.group())

            # Get the latest version for each of bugfix and minor versions,
            # based on the list generated above
            if len(trimmed_bugfix_versions) > 0:
                latest_parsed_trimmed_bugfix_versions = [version.parse(
                    trimmed_bugfix_version) for trimmed_bugfix_version in
                    trimmed_bugfix_versions]
                latest_bugfix_version = str(sorted(
                        latest_parsed_trimmed_bugfix_versions)[-1])
            else:
                common.eprint("Could not find any bugfix versions.")
                latest_bugfix_version = None

            if len(trimmed_minor_versions) > 0:
                latest_parsed_trimmed_minor_versions = [version.parse(
                    trimmed_minor_version) for trimmed_minor_version in
                    trimmed_minor_versions]
                latest_minor_version = str(sorted(
                        latest_parsed_trimmed_minor_versions)[-1])
            else:
                common.eprint("Could not find any minor versions.")
                latest_minor_version = None

            # Create lists of tag names that contain the string that was
            # determined to be the latest above
            latest_minor_versions = []
            latest_bugfix_versions = []
            for tag in tags:
                if (latest_bugfix_version and
                        latest_bugfix_version in tag['name']):
                    latest_bugfix_versions.append(tag['name'])
                elif (latest_minor_version and
                        latest_minor_version in tag['name']):
                    latest_minor_versions.append(tag['name'])

            # Pass those tags through the function defined above
            latest_tag_name = {}
            if len(latest_bugfix_versions) > 1:
                latest_tag_name['bugfix'] = get_best_version(
                        latest_bugfix_versions)
            elif len(latest_bugfix_versions) == 1:
                latest_tag_name['bugfix'] = latest_bugfix_versions[0]

            if len(latest_minor_versions) > 1:
                latest_tag_name['minor'] = get_best_version(
                        latest_minor_versions)
            elif len(latest_minor_versions) == 1:
                latest_tag_name['minor'] = latest_minor_versions[0]

        common.eprint("Latest tag found is: {}".format(latest_tag_name))

    return latest_tag_name


def get_latest_versions():

    services = {}
    for service in common.SERVICES:
        common.eprint("Getting latest tag for {}".format(service))
        latest_tag = get_latest_tag(common.SERVICES[service]['registry'])
        # Here we have to test if the above returned false due to a sub-par
        # data structure in common for our services, or just not parsing it the
        # right way or something. IDK. This part needs work.
        if latest_tag:
            services[service] = latest_tag

    return services


def get_branch_versions(supported_branch, role_path):

    # Check out the branch that we're going to be comparing
    git_branches = subprocess.run(['git', 'checkout', supported_branch],
            cwd=role_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Load the YAML of the defaults/main.yml variable file
    comp_path = 'group_vars/compositional'
    with open("{}/defaults/main.yml".format(role_path), 'r') as all_comp:
        comp_vars = yaml.safe_load(all_comp.read())

    # Make a dictiontionary of the service name/version value key-value keypair
    services = {}
    for service in common.SERVICES:
        common.eprint("Checking Service {}".format(service))
        var_name = "compositional_{}_version".format(service)
        try:
            services[service] = comp_vars[var_name]
            common.eprint("Default Version: {}".format(comp_vars[var_name]))
        except KeyError:
            common.eprint("No default named: {} -- skipping".format(var_name))

    return services


def get_supported_branches(role_path):

    # Get a listing of the git branches
    git_branches = subprocess.run(['git', 'branch', '-a'],
            stdout=subprocess.PIPE, encoding='utf-8', cwd=role_path,
            stderr=subprocess.DEVNULL)
    # Add all of the stable branches into a list
    stable_branches = []
    for git_branch in git_branches.stdout.split():
        if (git_branch.startswith('remotes/origin') and
                git_branch.split('/')[2].startswith('stable')):
            stable_branches.append(git_branch.split('/')[2])

    # Take the latest three stable branches by semantic name
    supported_branches = sorted(stable_branches)[-3:]
    # Add master onto the list because we want to check that too
    supported_branches.append('master')

    return supported_branches


def get_service_versions(args):

    # Clone down the compositional repo to inspect and comapare against
    role_path = "/tmp/{}".format(args['role_url'].split('/')[-1].split('.')[0])
    subprocess.run(['git', 'clone', args['role_url']], cwd="/tmp",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        # Get a list of the currently supported branches, a.k.a the three most
        # recent stable branches and 'master'
        supported_branches = get_supported_branches(role_path)

        common.eprint("Supported Branches: {}".format(supported_branches))

        # check the currently available services for both the three most recent
        # stable branches as well as master.
        service_versions = {}
        for supported_branch in supported_branches:
            common.eprint("Checking Branch: {}".format(supported_branch))
            service_versions[supported_branch] = get_branch_versions(
                    supported_branch, role_path)

        # Clean up after ourselves
        shutil.rmtree(role_path)

    except Exception as e:

        #
        # Clean up after ourselves
        #
        # Show the error
        common.eprint(traceback.format_exc())
        # Remove the git repo directory
        shutil.rmtree(role_path)
        # Exit with an error code of 3
        sys.exit(3)

    # Get the latest upstream registry version
    service_versions['latest'] = get_latest_versions()

    return service_versions



def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="""Reports on available
            versions of the upstream projects for OurCompose""")
    parser.add_argument('-r', '--role-url',
                        help='The url to the compositional role',
                        default='https://gitlab.com/compositionalenterprises/role-compositional.git',
                        required=False)

    args = vars(parser.parse_args())

    return args


def main():
    """Run the update"""
    # Get the args
    args = parse_args()

    # main function to get the results dictionary showing all of the versions
    # of the various services on the various branches and the various upstream
    # registries
    service_versions = get_service_versions(args)

    # Put together a comprehensive report on the results
    report(service_versions)

if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
