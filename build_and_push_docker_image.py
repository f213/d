#!/usr/bin/env python
"""Build docker image and upload it to the registry"""

from __future__ import print_function

import argparse
import os
import subprocess
from datetime import datetime

_version = None


def check_environment():
    assert 'CIRCLECI' in os.environ, 'This script is intended to run inside the circleci.com'

    assert 'DOCKER_USER' in os.environ and 'DOCKER_PASSWORD' in os.environ, \
        'You should have $DOCKER_USER and $DOCKER_PASSWORD defined in your build env'


def get_build_version():
    """Build version, unique within one build"""
    global _version
    if _version is not None:
        return _version

    _version = datetime.now().strftime('%Y%m%d%H%M') + os.environ['CIRCLE_BUILD_NUM'][-3:]
    return _version


def get_tag(label, version=None):
    """Tag, unique within one build"""
    if version is None:
        version = get_build_version()

    return '%s:%s' % (label, version)


def docker_login():
    code = subprocess.call([
        'docker', 'login',
        '-u', os.environ['DOCKER_USER'],
        '-p', os.environ['DOCKER_PASSWORD'],
    ])

    if code:
        raise RuntimeError("Docker login with the login '%s' failed" % os.environ['DOCKER_USER'])


def docker_build(label, ctx):
    subprocess.check_call([
        'docker', 'build',
        '-t', get_tag(label),
        ctx,
    ])


def docker_push(label):
    subprocess.check_call(['docker', 'push', label])


def tag_as_latest(label):
    subprocess.check_call([
        'docker', 'tag',
        get_tag(label),
        get_tag(label, 'latest'),
    ])


def main():
    parser = argparse.ArgumentParser(description='Build docker image within CI')
    parser.add_argument('label', help='Docker image label, like you/prj')
    parser.add_argument('ctx', help='Build context path')

    args = vars(parser.parse_args())
    label = args['label']
    ctx = args['ctx']

    tag = get_tag(label)

    print(
        'Building image',
        Bcolors.HEADER, label,
        Bcolors.ENDC, 'with tag',
        Bcolors.HEADER, tag,
        Bcolors.ENDC,
    )

    docker_login()

    ok('Docker login is fine, building...')

    docker_build(label, ctx)
    ok('Build is fine, tagging image as latest')

    tag_as_latest(label)

    ok('Pushing image to the registry')
    docker_push(label)

    ok('Image is pushed, exiting')


def ok(msg):
    print(Bcolors.OKGREEN, msg, Bcolors.ENDC)


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


if __name__ == '__main__':
    check_environment()
    main()
