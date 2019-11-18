#!/bin/bash

sed -i 's#RDECK_JVM="$RDECK_JVM#RDECK_JVM="$RDECK_JVM -Dserver.web.context=/rundeck#' /home/rundeck/etc/profile

/tini -- docker-lib/entry.sh
