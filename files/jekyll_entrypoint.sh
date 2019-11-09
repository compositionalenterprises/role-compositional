#!/bin/bash

#
# This file provides the first setup and running of the server in Jekyll, based on a couple
# environment variables:
#
#       - JEKYLL_PORT
#       - JEKYLL_BASE_URL
#       - JEKYLL_DOMAIN
#       - JEKYLL_EXTRA_COMMANDS
#

jekyll_port="${JEKYLL_PORT:-8080}"

# Remove everything in here except for this very script
find . -not -name 'entrypoint.sh'\
       -not -name '.'\
       -not -name '..' \
       -print0 |\
       xargs -0 rm -rf --

git init
git remote add origin https://gitlab.com/smacz/docker-andrewcz-blog.git
git fetch
git reset --hard origin/master

# Test for the base URL existing and not being a blank string
if [[ ! -z "${JEKYLL_BASE_URL}" ]]; then
        # Add leading and trailing slashes as necessary
        if [[ ${JEKYLL_BASE_URL:0:1} != '/' ]]; then
                JEKYLL_BASE_URL="/${JEKYLL_BASE_URL}"
        fi
        if [[ ${JEKYLL_BASE_URL: -1} != '/' ]]; then
                JEKYLL_BASE_URL="${JEKYLL_BASE_URL}/"
        fi
        sed -i "s#baseurl:.*#baseurl:        '$JEKYLL_BASE_URL'#" _config.yml
fi

# Same with the domain name
if [[ ! -z "${JEKYLL_DOMAIN}" ]]; then
        sed -i "s#^url:.*#url:            '$JEKYLL_DOMAIN'#" _config.yml
fi

/bin/bash -c "${JEKYLL_EXTRA_COMMANDS}"

jekyll serve --no-watch -H 0.0.0.0 -P $jekyll_port
