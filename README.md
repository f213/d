# d — the only tool you need within Circle CI for dealing with docker swarm

## Installation

```sh
export D_RELEASE=0.4.4  # the latest one
wget -O - https://raw.githubusercontent.com/f213/d/master/install.sh|sh
```

## Usage

The is pre-alfa, so checkout built-in help
```sh
$ ./d

Usage: ./d.py COMMAND <OPTIONS>


Where COMMAND is one of the following:
      deploy-stack 	 Deploy or update a stack, using docker stack deploy.
      update-image 	 Update image for all services in the running stack.
      push-image 	 Push previously built image to the dockerhub.
      build-image 	 Build docker image and version in based on current HEAD commit.
```
