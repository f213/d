#!/usr/bin/env python

from __future__ import print_function

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Iterable
from datetime import datetime
from os import path


class BaseCommand(object):
    def add_arguments(self, parser):
        """Implement this to define custom arguments, which you will receive in the `run` method
        as keyword arguments.

        NOTE: all unparsed arguments you will receive as the `remainder` kwarg
        """
        pass

    def pre_add_arguments(self, parser):
        """Add app-wide arguments"""
        pass

    def pre_run_check(self):
        """Implement this to check if your command is run in correct environment"""
        pass

    def __init__(self):
        parser = argparse.ArgumentParser(prog=self.name())

        self.pre_add_arguments(parser)
        self.add_arguments(parser)

        parser.add_argument('remainder', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

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


class ManagerCommand(BaseCommand):
    """A command that runs on a cluster manager"""
    def pre_add_arguments(self, parser):
        parser.add_argument('manager', help='Manager address')

    def __init__(self):
        super(ManagerCommand, self).__init__()

        self.host = Host(self.args.get('manager'))


class ImageCommand(BaseCommand):
    """A command that handles docker image commands"""
    TAGGING_METHODS = {
        'sha1': lambda: os.environ['CIRCLE_SHA1'],
        'date': lambda: datetime.now().strftime('%Y%m%d%H%M'),
    }

    @classmethod
    def label(cls, label, tag=None, tagging_method='sha1'):
        if ':' in label and tag is None:
            return label

        if ':' in label and tag is not None:  # replace existing tag
            label, _ = label_and_tag(label)
            return ':'.join([label, tag])

        return ':'.join([label, tag or cls.TAGGING_METHODS[tagging_method]()])

    @classmethod
    def image_is_present(cls, label):
        """Check if image is present in the local host"""
        return len([img for img in run_with_output('docker', 'image', 'ls', '-q', label) if len(img)]) > 0


def flatten_args(args):
    """Recursively flatten an array of args, changing ('docker', 'build', ['-f', 'Dockerfile']) to ('docker', 'build', '-f', 'Dockerfile')"""
    flattened = list()
    for arg in args:
        if isinstance(arg, str) or isinstance(arg, int):
            flattened.append(str(arg))

        elif isinstance(arg, Iterable):
            flattened += flatten_args(arg)

        else:
            raise TypeError('Nor string, nor iterable arg added to flatten_args')

    return flattened


def run(*args):
    return subprocess.check_call(flatten_args(args))


def run_with_output(*args):
    return subprocess.check_output(flatten_args(args)).decode()


def label_and_tag(name):
    got = name.split(':')
    if len(got) == 1:
        got.append(None)
    return got


class Host(object):
    """Represents a remote host you can ssh to

    Usage:
        host = Host('manager.my.cluser.com')

        host.run('echo', 'i am a host')
        host.run('echo', '`hostname`')

    """
    LOCALHOST = [
        'localhost',
    ]

    def is_local(self):
        return self.name in self.LOCALHOST

    def __init__(self, name):
        self.name = name

    def add_prefix(self, remote, cmd):
        if self.is_local():
            return cmd

        return remote + list(cmd)

    def run(self, *args):
        """Run SSH command"""
        return run(*self.add_prefix(remote=['ssh', self.name], cmd=args))

    def get_output(self, *args):
        """Run SSH command and get output as a list of strings"""
        output = run_with_output(*self.add_prefix(remote=['ssh', self.name], cmd=args))

        return [line for line in output.split('\n') if len(line)]

        return output

    def get_json(self, *args):
        output = ''.join(self.get_output(*args))

        return json.loads(output)

    def cp(self, src, dst):
        """Copy local file to the host"""
        if self.is_local():
            return run('cp', src, dst)

        return run('scp', src, '{hostname}:{dst}'.format(hostname=self.name, dst=dst))

    def __str__(self):
        return self.name


class DeployStack(ManagerCommand):
    """Deploy or update a stack, using docker stack deploy"""
    def add_arguments(self, parser):
        parser.add_argument('-c', '--config', help='Stack description in docker-compose format', default='docker-compose.prod.yml')

        parser.add_argument('name', help='Stack name')

    def stack_path(self):
        stack_dir = os.environ.get('STACK_DIR', '/srv')
        return '{dir}/{path}'.format(dir=stack_dir, path=self.args['name'])

    def stack_config_path(self, path='docker-compose.prod.yml'):
        return '{dir}/{path}'.format(dir=self.stack_path(), path=path)

    def handle(self, config, name, remainder, **kwargs):
        self.host.run('mkdir', '-p', self.stack_path())
        self.host.cp(config, self.stack_config_path())

        self.host.run(
            'docker', 'stack', 'deploy',
            '--prune',
            '-c', self.stack_config_path(),
            remainder, name,
        )


class BuildImage(ImageCommand):
    """Build docker image and label it with HEAD commit hash"""

    def pre_run_check(self):
        assert 'CIRCLECI' in os.environ, 'This script is intended to run inside the circleci.com'

    def add_arguments(self, parser):
        parser.add_argument('label', help='Docker image label, like you/prj')
        parser.add_argument('ctx', help='Build context path')
        parser.add_argument('-t', '--tag-method', help="Image taggging method, 'sha1' (from circleci) or 'date'", default='sha1')

    def docker_build(self, label, ctx, tagging_method, remainder, **kwargs):
        label = self.label(label, tagging_method=tagging_method)
        print('Building', label)

        run(
            'docker', 'build',
            '-t', label,
            remainder,
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


class PushImage(ImageCommand):
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
        print('Pushing', label, '...')
        run('docker', 'push', label)

    def handle(self, label, **kwargs):
        self.docker_login()
        labels = [label]

        tag = label_and_tag(label)[1]

        if tag is None:  # if no tag given -- push the latest AND sha1 tag if present
            labels[0] = self.label(label, 'latest')
            if 'CIRCLECI' in os.environ:
                latest_tagged = self.label(label, tagging_method='sha1')
                if self.image_is_present(latest_tagged):
                    labels.append(latest_tagged)

        for label in labels:
            self.docker_push(label, **kwargs)


class UpdateImage(ManagerCommand):
    """Update image in the running stack"""
    def add_arguments(self, parser):
        parser.add_argument('name', help='Stack name')
        parser.add_argument('image', help='Image name')

    def fetch_services(self, stack_name):
        for service in self.host.get_output(
            'docker', 'stack', 'services',
            stack_name,
            '--format', '"{{ .Name }}|{{ .Image }}"',
        ):
            yield service.split('|')

    def get_services(self, name, image):
        image, _ = label_and_tag(image)  # only image name

        for service, image_name in self.fetch_services(name):
            service_image, _ = label_and_tag(image_name)

            if service_image == image:
                yield service

    def handle(self, name, image, remainder, **kwargs):
        for service in self.get_services(name, image):
            print('Updating', service, 'to image', image)
            self.host.run(
                'docker', 'service', 'update',
                '--with-registry-auth',
                '--image', image,
                remainder, service,
            )


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


class RunCommand(ManagerCommand):
    """Run command one the host machine within specified container"""
    def add_arguments(self, parser):
        parser.add_argument('--env-from', help='Take envirnoment variables from specified service', default='')
        parser.add_argument('-i', '--image', help='Image to run the command')
        parser.add_argument('command', help='Command to run within container')

    def handle(self, env_from, image, command, remainder, **kwargs):
        """TODO(f213): add an ability to attach to a network"""
        env = self.get_env(env_from) if len(env_from) else {}
        env = ["-e{key}={value}".format(key=key, value=value) for key, value in env.items()]

        self.host.run(
            'docker', 'run', '-t',
            env, image, command,
            remainder,
        )

    def get_env(self, env_from):
        got = self.host.get_json('docker', 'service', 'inspect', env_from)[0]
        env = got['Spec']['TaskTemplate']['ContainerSpec']['Env']
        return {left: right for [left, right] in map(lambda a: a.split('='), env)}

    def get_node(self, service):
        nodes = self.host.get_output('docker', 'service', 'ps', service, '-f', 'desired-state=running', '--format', '"{{.Node}}"')

        if not len(nodes):
            print('No running nodes with service {} found, exiting'.format(service))
            exit(127)

        return nodes[0]


def get_command_registry():
    def get_subclasses(klass):
        """Recursively get subclasses"""
        for c in klass.__subclasses__():
            if len(c.__subclasses__()):
                for subclass in get_subclasses(c):
                    yield subclass

            else:
                yield c

    return {klass.cmd_name(): klass for klass in get_subclasses(BaseCommand)}


def main(command):
    """Determine command to launch"""
    command_registry = get_command_registry()

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
