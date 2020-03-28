#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json

def eprint(*args, **kwargs):
    """Works the same as print but outputs to stderr."""
    print(file=sys.stderr, *args, **kwargs)


def json_print(data):
    """Prints json-formatted and dictionary data in human-readable form"""
    print(json.dumps(data, indent=4, sort_keys=True))


def json_eprint(data):
    """
    Prints json-formatted and dictionary data in human-readable form to stderr
    """
    print(json.dumps(data, indent=4, sort_keys=True), file=sys.stderr)
