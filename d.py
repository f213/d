#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from os import path

STACK_DIR = os.environ.get('STACK_DIR', '/srv')


class BaseCommand(object):
    def add_arguments(self, parser):
        """Implement this to define custom arguments, which you will receive in the `run` method
        as keyword arguments.

        NOTE: all unparsed arguments you will receive as the `remainder` kwarg
        """
        pass

    def pre_run_check(self):
        """Implement this to check if your command is run in correct environment"""
        pass

    def __init__(self):
        parser = argparse.ArgumentParser(prog=self.name())

        self.add_arguments(parser)

        parser.add_argument('remainder', nargs=argparse.REMAINDER)

        self.args = vars(parser.parse_args())

    @classmethod
    def name(cls):
        return '{prog} {cmd}'.format(
            prog=sys.argv[0],
            cmd=cls.cmd_name(),
        )

    @classmethod
    def cmd_name(cls):
        class_name = cls.__name__
        class_name = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', class_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', class_name).lower()

    def __call__(self):
        self.pre_run_check()
        self.handle(**self.args)

    def handle(self):
        raise NotImplementedError()


def run(*args):
    return subprocess.check_call(args)


def run_with_output(*args):
    return subprocess.check_output(args).decode()


def label_and_tag(name):
    got = name.split(':')
    if len(got) == 1:
        got.append(None)
    return got


class Host(object):
    """Represents a remote host you can ssh to

    Usage:
        host = Host('manager.my.cluser.com')

        host.ssh('echo', 'i am a host')
        host.ssh('echo', '`hostname`')

    """
    def __init__(self, name):
        self.name = name

    def ssh(self, *args):
        """Run SSH command"""
        return run('ssh', self.name, *args)

    def ssh_output(self, *args):
        """Run SSH command and get output as a list of strings"""
        output = run_with_output('ssh', self.name, *args)

        return [line for line in output.split('\n') if len(line)]

        return output

    def scp(self, src, dst):
        """Copy local file to the host"""
        return run('scp', src, '{hostname}:{dst}'.format(hostname=self.name, dst=dst))

    def __str__(self):
        return self.name


class DeployStack(BaseCommand):
    """Deploy or update a stack, using docker stack deploy"""
    def add_arguments(self, parser):
        parser.add_argument('-c', '--config', help='Stack description in docker-compose format', default='docker-compose.prod.yml')

        parser.add_argument('manager', help='Manager')
        parser.add_argument('name', help='Stack name')

    def stack_path(self):
        return '{dir}/{path}'.format(dir=STACK_DIR, path=self.args['name'])

    def stack_config_path(self, path='docker-compose.prod.yml'):
        return '{dir}/{path}'.format(dir=self.stack_path(), path=path)

    def handle(self, config, name, manager, remainder):
        manager = Host(manager)

        manager.ssh('mkdir', '-p', self.stack_path())
        manager.scp(config, self.stack_config_path())

        delploy_args = [
            'docker', 'stack', 'deploy',
            '--prune',
            '-c', self.stack_config_path(),
        ] + remainder + [name]

        manager.ssh(*delploy_args)


class BuildImage(BaseCommand):
    """Build docker image and label it with HEAD commit hash"""
    TAGGING_METHODS = {
        'sha1': lambda: os.environ['CIRCLE_SHA1'],
        'date': lambda: datetime.now().strftime('%Y%m%d%H%M'),
    }

    def pre_run_check(self):
        assert 'CIRCLECI' in os.environ, 'This script is intended to run inside the circleci.com'

    def add_arguments(self, parser):
        parser.add_argument('label', help='Docker image label, like you/prj')
        parser.add_argument('ctx', help='Build context path')
        parser.add_argument('-t', '--tag-method', help="Image taggging method, 'sha1' (from circleci) or 'date'", default='sha1')

    @classmethod
    def label(cls, label, tag=None, tag_method='sha1'):
        if ':' in label and tag is None:
            return label

        if ':' in label and tag is not None:  # replace existing tag
            label, _ = label_and_tag(label)
            return ':'.join([label, tag])

        return ':'.join([label, tag or cls.TAGGING_METHODS[tag_method]()])

    def docker_build(self, label, ctx, tag_method, **kwargs):
        label = self.label(label, tag_method=tag_method)
        print('Building', label)

        run(
            'docker', 'build',
            '-t', label,
            ctx,
        )
        return label

    def tag_as_latest(self, label):
        versioned = self.label(label)
        latest = self.label(label, 'latest')
        print('Tagging', versioned, 'as', latest)

        run('docker', 'tag', versioned, latest)

    def handle(self, **kwargs):
        label = self.docker_build(**kwargs)
        self.tag_as_latest(label)


class PushImage(BaseCommand):
    """Push previously built image to the dockerhub"""
    def pre_run_check(self):
        assert 'DOCKER_USER' in os.environ and 'DOCKER_PASSWORD' in os.environ, \
            'You should have $DOCKER_USER and $DOCKER_PASSWORD defined in your build env'

    def add_arguments(self, parser):
        parser.add_argument('label', help='Docker image label, like you/prj')

    @staticmethod
    def docker_login():
        run(
            'docker', 'login',
            '-u', os.environ['DOCKER_USER'],
            '-p', os.environ['DOCKER_PASSWORD'],
        )

    @staticmethod
    def docker_push(label, **kwargs):
        run('docker', 'push', label)

    def handle(self, **kwargs):
        self.docker_login()
        self.docker_push(**kwargs)


class UpdateImage(BaseCommand):
    """Update image in the running stack"""
    def add_arguments(self, parser):
        parser.add_argument('manager', help='Manager')
        parser.add_argument('name', help='Stack name')
        parser.add_argument('image', help='Image name')

    def find_services(self, manager, name, image):
        image, _ = label_and_tag(image)  # only image name

        for service in manager.ssh_output(
            'docker', 'stack', 'services',
            name,
            '--format', '"{{ .Name }}|{{ .Image }}"',
        ):

            service, image_name = service.split('|')
            service_image, _ = label_and_tag(image_name)

            if service_image == image:
                yield service

    def handle(self, manager, name, image, remainder):
        manager = Host(manager)
        for service in self.find_services(manager, name, image):
            print('Updating', service, 'to image', image)
            manager.ssh(*[
                'docker', 'service', 'update',
                '--with-registry-auth',
                '--image', image,
            ] + remainder + [service])


class AddHostKey(BaseCommand):
    """Add host key to .ssh/known_hosts storage"""
    def add_arguments(self, parser):
        parser.add_argument('-k', '--key', help='Key path', default='.circleci/known_hosts')
        parser.add_argument('--force', help='Overwrite existing host key', action='store_true')

    def handle(self, key, force=False, **kwargs):
        assert path.exists(key), '{} does not exist'.format(key)

        if not force:
            assert not path.exists(self.destination), '~/.ssh/known_hosts file already exists'

        run('mkdir', '-p', path.dirname(self.destination))
        run('cp', key, self.destination)

    @property
    def destination(self):
        return path.expanduser('~/.ssh/known_hosts')


def main(command):
    """Determine command to launch"""
    command_registry = {klass.cmd_name(): klass for klass in BaseCommand.__subclasses__()}

    if command.lower() not in command_registry.keys():
        print('Usage: %s COMMAND <OPTIONS>' % sys.argv[0])
        print('\n\nWhere COMMAND is one of the following:')
        for command, command_class in command_registry.items():
            print('     ', command, '\t', '{}.'.format(command_class.__doc__))

        exit(127)

    klass = command_registry[command.lower()]
    klass()()


def _get_initial_command():
    try:
        return sys.argv.pop(1)
    except IndexError:
        return ''


if __name__ == '__main__':
    command = _get_initial_command()
    main(command)
