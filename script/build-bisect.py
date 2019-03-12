#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import errno
import hashlib
import math
import os
import requests
import re
import shutil
import subprocess
import sys
import json

from io import StringIO
from lib.config import get_env_var
from lib.github import GitHub
from lib.helpers import *
from lib.util import download, execute, tempdir


tag_names = []
releases = {}
is_mac_os = True


def parse_args():
    parser = argparse.ArgumentParser(description='create PRs for all branches given branch against master')
    parser.add_argument('--bad',
                        help='optional version which is known to be bad',
                        default=None)
    parser.add_argument('--good',
                        help='optional version which is known to be good',
                        default=None)
    parser.add_argument('--branch',
                        help='optional branch where the problem is occurring',
                        default=None)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='extra logging')

    parser.add_argument('--fresh-profile', action='store_true',
                        help='if true, move the existing profile directory out of the way. \
                              can\'t be combined with `--use-profile`.')

    parser.add_argument('--use-profile',
                        help='url of a zipped profile to unzip/use for each install',
                        default=None)

    return parser.parse_args()


def get_releases(repo):
    global releases
    global tag_names

    releases = {}
    tag_names = []
    page = 1
    done = False
    draft_count = 0

    print('fetching releases from GitHub...')

    while not done:
        # for more info, see: https://developer.github.com/v3/guides/traversing-with-pagination/
        get_data = {
            'page': page,
            'per_page': 100
        }
        # get all the releases and index them
        response = repo.releases.get(params=get_data)
        if len(response) == 0:
            done = True
            break

        for release in response:
            # skip releases in draft status
            if release['draft']:
                draft_count = draft_count + 1
                continue
            tag_name = str(release['tag_name'].strip().replace('v', ''))
            tag_names.append(tag_name)
            releases[tag_name] = release
        page = page + 1

    print('fetch complete; ' + str(len(tag_names)) + ' versions found (excluding ' + str(draft_count) + ' drafts)')


def filter_releases(args):
    global tag_names

    filtered_tag_names = []

    print('filtering out versions which are not relevant...')

    # find all unique MINOR versions
    for tag in tag_names:
        version = tag.split('.')
        if len(version) != 3:
            continue

        major_version = str(version[0])
        minor_version = str(version[1])
        branch_version = major_version + '.' + minor_version + '.x'

        # remove entries which don't match optional branch (if present)
        if args.branch is not None and branch_version != args.branch:
            print(' - skipping "' + tag + '" (' + branch_version + ' != ' + args.branch + ')')
            continue

        # remove entries which don't have installer binary
        if not get_release_asset(tag, False):
            print(' - skipping "' + tag + '" (installer not found)')
            continue

        filtered_tag_names.append(tag)

    print('filtering complete (' + str(len(tag_names) - len(filtered_tag_names)) + ' versions removed)')
    tag_names = filtered_tag_names


def get_release_asset(version, verbose=True):
    global releases
    global is_mac_os

    release_id = releases[version]['id']
    if verbose:
        print('getting installer for  "' + version + '" (release id ' + str(release_id) + ')...')

    # find correct asset for platform
    for asset in releases[version]['assets']:
        if str(asset['name']).endswith('.dmg') and is_mac_os:
            if verbose:
                print('- binary found: ' + asset['browser_download_url'])
            return asset

    if verbose:
        print('- binary not found')
    return None


def install(download_dir, path):
    global is_mac_os

    if is_mac_os:
        print('- installing binary from DMG')
        print('-> mounting "' + path + '"')
        result = execute(['hdiutil', 'attach', path])

        # parse out the mounted volume
        volume = None
        result_lines = result.splitlines()
        for x in result_lines:
            x = x.strip()
            index = x.find('/Volumes/Brave')
            if index > -1:
                volume = x[index:]
                break

        if volume is None:
            raise Exception('[ERROR] did not find "/Volumes/Brave" sub-string in mount list!\n \
                             Full response from "hdiutil":\n' + result)

        print('-> mounted as "' + volume + '"')

        # in case volumes are already mounted, remove trailing " 1" or " 2" (etc)
        binary_name = volume.replace("/Volumes/", "")
        binary_name = re.sub("^\\d+\\s|\\s\\d+\\s|\\s\\d+$", "", binary_name) + '.app'
        volume_path = os.path.join(volume, binary_name)

        # copy binary to a temp folder
        print('-> copying "' + volume_path + '" to "' + download_dir + '"')
        result = execute(['cp', '-rp', volume_path, download_dir])
        print('-> copy complete')

        print('-> unmounting "' + volume + '"')
        result = execute(['hdiutil', 'detach', volume])

        return os.path.join(download_dir, binary_name)


def setup_profile_directory(args):
    global is_mac_os

    if is_mac_os:
        print('- processing changes for profile directory')
        if args.fresh_profile:
            print('-> clearing existing profile')
        elif args.use_profile:
            print('-> downloading profile: "' + args.use_profile + '"')


def test_version(args, attempt, tag):
    global tag_names

    # get the OS specific installer
    asset = None
    while len(tag_names) > 0 and not asset:
        print('\nattempt ' + str(attempt) + '] getting installer for  "' + tag +
              '" (release id ' + str(releases[tag]['id']) + ')')
        asset = get_release_asset(tag)
        if not asset:
            return False

    download_dir = tempdir('build-bisect_')
    download_path = os.path.join(download_dir, asset['name'])
    print('- downloading to ' + download_path)
    # download(tag, asset['browser_download_url'], download_path)

    # install_path = install(download_dir, download_path)

    setup_profile_directory(args)

    print('- running binary')
    # execute(['open', '-a', install_path])

    first = True
    while True:
        if not first:
            print('please type either `y` for yes or `n` for no!')
        answer = raw_input('Did this version work?: y/n\n')
        first = False
        if answer == 'y' or answer == 'n':
            break

    return answer == 'y'


def get_github_token():
    github_token = get_env_var('GITHUB_TOKEN')
    if len(github_token) == 0:
        result = execute(['npm', 'config', 'get', 'BRAVE_GITHUB_TOKEN']).strip()
        if result == 'undefined':
            raise Exception('`BRAVE_GITHUB_TOKEN` value not found!')
        return result


def get_good_index(version):
    global tag_names

    try:
        index = tag_names.index(version)
        print('- starting at ' + tag_names[index])
    except Exception as e:
        print('- `good` value "' + version + '" not found. ' + str(e))
        versions = version.split('.')
        if len(versions) != 3:
            return 0

        versions.pop()
        results = [i for i in tag_names if i.startswith('.'.join(versions) + '.')]
        if len(results) == 0:
            return 0

        print('-> using "' + results[0] + '" for the `good` value')
        return tag_names.index(results[0])


def get_bad_index(version):
    global tag_names

    try:
        index = tag_names.index(version)
        print('- ending at ' + tag_names[index])
    except Exception as e:
        print('- `bad` value "' + version + '" not found. ' + str(e))
        versions = version.split('.')
        if len(versions) != 3:
            return 0

        versions.pop()
        results = [i for i in tag_names if i.startswith('.'.join(versions) + '.')]
        if len(results) == 0:
            return 0

        print('-> using "' + results[-1] + '" for the `bad` value')
        return tag_names.index(results[-1])


def find_first_broken_version(args):
    global tag_names

    print('bisecting: total of ' + str(len(tag_names)) + ' versions in search set')

    left_index = 0
    right_index = len(tag_names) - 1

    if left_index >= right_index:
        raise Exception('[ERROR] Not enough versions to perform search')

    if args.good:
        left_index = get_good_index(args.good)
        if left_index == 0:
            args.good = None

    if args.bad:
        right_index = get_bad_index(args.bad)
        if right_index == len(tag_names) - 1:
            args.bad = None

    if args.good or args.bad:
        print('- search set narrowed down to ' + str(right_index - left_index) +
              ' versions using provided good/bad version(s)')

    attempt_number = 1

    # left should be working
    if not args.good:
        left_tag = tag_names[left_index]
        result = test_version(args, attempt_number, left_tag)
        attempt_number = attempt_number + 1
        if result is False:
            raise Exception('[ERROR] Version "' + left_tag + '" is expected to work but doesn\'t')

    # right should be NOT working
    if not args.bad:
        right_tag = tag_names[right_index]
        result = test_version(args, attempt_number, right_tag)
        attempt_number = attempt_number + 1
        if result is True:
            raise Exception('[ERROR] Version "' + right_tag + '" is expected to fail but doesn\'t')

    # perform search
    while left_index < right_index:
        test_index = int(math.floor((left_index + right_index) / 2))
        test_tag = tag_names[test_index]

        gap = right_index - left_index
        if gap <= 1:
            return test_tag, attempt_number

        if args.verbose:
            print('\n[DEBUG] L=' + str(left_index) + ', R=' + str(right_index) +
                  ', M=' + str(test_index) + ', gap=' + str(gap))
        result = test_version(args, attempt_number, test_tag)

        if result:
            left_index = test_index + 1
        else:
            right_index = test_index - 1

        attempt_number = attempt_number + 1

    return tag_names[left_index], attempt_number


def main():
    global tag_names

    args = parse_args()
    if args.fresh_profile and args.use_profile:
        print('[ERROR] you can\'t use both `--fresh-profile` AND `--use-profile` at the same time.')
        return 1

    github_token = get_github_token()
    repo = GitHub(github_token).repos(BRAVE_REPO)

    get_releases(repo)
    tag_names.sort(key=lambda s: map(int, s.split('.')))

    filter_releases(args)
    first_broken_version, attempts = find_first_broken_version(args)
    print('DONE: issue first appeared in "' + str(first_broken_version) + '" (found in ' + str(attempts) + ' attempts)')

    try:
        broken_index = tag_names.index(first_broken_version)
        if broken_index > 0:
            previous_release = tag_names[broken_index - 1]
            versions = 'v' + previous_release + '..v' + first_broken_version
            if args.verbose:
                print('[INFO] finding commits using "git log --pretty=oneline ' + versions + '"')
            commits = execute(['git', 'log', '--pretty=oneline', versions]).strip()
            commit_lines = commits.split('\n')
            print('Commits specific to tag "v' + first_broken_version + '" (' + str(len(commit_lines)) + ' commit(s)):')
            print(commits)
    except Exception as e:
        print('[ERROR] ' + str(e))


if __name__ == '__main__':
    import sys
    sys.exit(main())
