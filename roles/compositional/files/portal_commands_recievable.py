#!/usr/bin/python3 -u

import os
import socket
from systemd.daemon import listen_fds;

def systemd_socket_response():
    """
    Accepts every connection of the listen socket provided by systemd, send the
    HTTP Response 'OK' back.
    """
    try:
        fds = listen_fds()
    except ImportError:
        fds = [3]

    for fd in fds:
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0)

        try:
            while True:
              conn, addr = sock.accept()
              conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 3\r\n\r\nOK\n")
              with open('/tmp/socket_test', 'w') as socket_test:
                  socket_test.write("Second OK!")
        except socket.timeout:
            pass
        except OSError as e:
            # Connection closed again? Don't care, we just do our job.
            print(e)

if __name__ == "__main__":
    with open('/tmp/socket_test', 'w') as socket_test:
        socket_test.write("First OK!")

    if os.environ.get("LISTEN_FDS", None) != None:
        systemd_socket_response()
