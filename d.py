#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys

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


def parse_image(name):
    got = name.split(':')
    if len(got) == 1:
        got[1] = None
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
    def pre_run_check(self):
        assert 'CIRCLECI' in os.environ, 'This script is intended to run inside the circleci.com'

    def add_arguments(self, parser):
        parser.add_argument('label', help='Docker image label, like you/prj')
        parser.add_argument('ctx', help='Build context path')

    @staticmethod
    def label_with_tag(label, tag=None):
        if ':' in label:
            return label

        return ':'.join([label, tag or os.environ['CIRCLE_SHA1']])

    def docker_build(self, label, ctx, **kwargs):
        label = self.label_with_tag(label)
        print('Building', label)

        run(
            'docker', 'build',
            '-t', label,
            ctx,
        )

    def tag_as_latest(self, label, **kwargs):
        versioned = self.label_with_tag(label)
        latest = self.label_with_tag(label, 'latest')
        print('Tagging', versioned, 'as', latest)

        run('docker', 'tag', versioned, latest)

    def handle(self, **kwargs):
        self.docker_build(**kwargs)
        self.tag_as_latest(**kwargs)


class PushImage(BaseCommand):
    def pre_run_check(self):
        assert 'DOCKER_USER' in os.environ and 'DOCKER_PASSWORD' in os.environ, \
            'You should have $DOCKER_USER and $DOCKER_PASSWORD defined in your build env'

    def add_arguments(self, parser):
        parser.add_argument('label', help='Docker image label, like you/prj')
        parser.add_argument('ctx', help='Build context path')

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
    def add_arguments(self, parser):
        parser.add_argument('manager', help='Manager')
        parser.add_argument('name', help='Stack name')
        parser.add_argument('image', help='Image name')

    def find_services(self, manager, name, image):
        image, _ = parse_image(image)  # only image name

        for service in manager.ssh_output(
            'docker', 'stack', 'services',
            name,
            '--format', '"{{ .Name }}|{{ .Image }}"',
        ):

            service, image_name = service.split('|')
            service_image, _ = parse_image(image_name)

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


def main(command):
    """Determine command to launch"""
    command_registry = {klass.cmd_name(): klass for klass in BaseCommand.__subclasses__()}

    if command.lower() not in command_registry.keys():
        print('Usage: %s COMMAND <OPTIONS>' % sys.argv[0])
        print(' Where COMMAND is one of', ', '.join(command_registry.keys()))
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
