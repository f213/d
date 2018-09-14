#!/bin/sh
set -e

if [ -z $D_RELEASE ]; then
    echo Please set D_RELEASE environment variable
    exit 127
fi

mkdir -p .d
wget -o /dev/null -O - https://github.com/f213/d/archive/$D_RELEASE.tar.gz | tar zxp -C .d '*/d.py'

if [ ! -d ".d/d-${D_RELEASE}" ]; then
    echo "Problem with downloading, check D_RELEASE environment variable (you've got ${D_RELEASE}) and github connectivity"
    exit 127
fi

mv .d/d-$D_RELEASE/d.py d

chmod +x ./d

rm -Rf .d
