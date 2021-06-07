#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Andrew Cziryak (andrew@compositional.enterprises)'
__license__ = 'MIT'
__email__ = 'admins@compositional.enterprises'
__version__ = '0.1.0'

# Shamelessly stolen from https://github.com/birlorg/bitwarden-cli
#
# Modified to be compatible with the defaults from the latest web vault that
# ships with bitwarden. Reference implementation can be found here:
# https://bitwarden.com/help/crypto.html

import os
import hmac
import json
import base64
import pprint
import getpass
import hashlib
import argparse
import requests
import posixpath
import cryptography

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf import hkdf
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding, hashes

def encodeCipherString(enctype, iv, ct, mac):
    """return bitwarden cipherstring"""
    ret = "{}.{}|{}".format(enctype, iv.decode('utf-8'), ct.decode('utf-8'))
    if mac:
        return ret + '|' + mac.decode('utf-8')
    return ret

def encrypt(pt, key, macKey):
    """
    encrypt+mac a value with a key and mac key and random iv, return cipherString
    """
    if not hasattr(pt, 'decode'):
        pt = bytes(pt, 'utf-8')
    padder = padding.PKCS7(128).padder()
    pt = padder.update(pt) + padder.finalize()
    iv = os.urandom(16)
    #key = hashlib.sha256(key).digest()
    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(pt) + encryptor.finalize()
    mac = hmac.new(macKey, iv + ct, 'sha256').digest()
    return encodeCipherString(2, base64.b64encode(iv), base64.b64encode(ct),
                              base64.b64encode(mac))


def hashedPassword(password, salt):
    """
    base64-encode a wrapped, stretched password+salt for signup/login
    """
    if not hasattr(password, 'decode'):
        password = password.encode('utf-8')
    key = makeKey(password, salt)
    # This is just a little too nested to be my own code, but a little more
    # nested than completely necessary, so I'm leaving it there.
    return base64.b64encode(
        hashlib.pbkdf2_hmac('sha256', key, password, 1,
                            dklen=32)).decode('utf-8')


def get_stretched_key(master_key, info):
        hkdf_class = hkdf.HKDFExpand(
                algorithm=hashes.SHA256(),
                length=32,
                info=info.encode('utf-8'),
                backend=default_backend()
        )
        stretched_key = hkdf_class.derive(master_key)
        return stretched_key


def makeKey(password, salt):
    """make master key"""
    if not hasattr(password, 'decode'):
        password = password.encode('utf-8')
    if not hasattr(salt, 'decode'):
        salt = salt.lower()
        salt = salt.encode('utf-8')
    # Here we use 100,000 iterations since that is the default that the
    # bitwarden web vault uses. In the future, we can parameterize this, or at
    # least change it if updating it becomes necessary.
    #
    # I don't know where we got a dklen of 32 from.
    return hashlib.pbkdf2_hmac('sha256', password, salt, 100000, dklen=32)


def symmetricKey():
    """create symmetrickey"""
    pt = os.urandom(64)
    encryptionKey = pt[:32]
    macKey = pt[32:64]
    return encryptionKey, macKey


def register(args):
    """
    register a new account with bitwarden server
    """
    masterKey = makeKey(args['password'], args['email'])
    masterPasswordHash = hashedPassword(args['password'], args['email'])
    expectedEncryptionKey, expectedMacKey = symmetricKey()
    stretch_encryption_key = get_stretched_key(masterKey, 'enc')
    stretch_mac_key = get_stretched_key(masterKey, 'mac')
    #print("Master Key Base64: %s", base64.b64encode(masterKey))
    #print("Master Password Hash: %s", masterPasswordHash)
    #print("Stretched Symmetric Encryption Key: %s", base64.b64encode(stretch_encryption_key + stretch_mac_key))
    #print("Stretch Encryption Key: %s", base64.b64encode(stretch_encryption_key))
    #print("Stretch MAC Key: %s", base64.b64encode(stretch_mac_key))
    #print("Generated Symmetric Key: %s", base64.b64encode(expectedEncryptionKey + expectedMacKey))
    #print("Symmetric Encryption Key: %s", base64.b64encode(expectedEncryptionKey))
    #print("Symmetric MAC Key: %s", base64.b64encode(expectedMacKey))
    protectedKey = encrypt(expectedEncryptionKey + expectedMacKey, stretch_encryption_key, stretch_mac_key)
    #print("Protected Symmetric Key: %s", protectedKey)

    result = {
        "masterPasswordHash": str(masterPasswordHash),
        "key": protectedKey,
    }
    return result


def parse_args():
    """Parse the passed in arguments"""
    parser = argparse.ArgumentParser(description="Archives droplet snapshots")
    parser.add_argument('-e', '--email',
        help='Email for the user',
        required=False)
    parser.add_argument('-p', '--password',
        help='The master password for the new user',
        required=False)
    parser.add_argument('-n', '--name',
        help="Username for the new user",
        required=False)

    args = vars(parser.parse_args())

    if not args['email']:
        args['email'] = input("Email Address: ")
    if not args['password']:
        args['password'] = getpass.getpass("Master Password: ")
    if not args['name']:
        args['name'] = input("Username: ")

    return args


def main():
    args = parse_args()
    result = register(args)
    result["name"] = args['name']
    result["email"] = args['email']
    result['kdf'] = 0
    result['kdfIterations'] = 100000
    print(json.dumps(result))


if __name__ == '__main__':
    #
    # Handle ^C without throwing an exception
    #
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
