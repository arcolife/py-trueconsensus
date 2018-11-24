#!/bin/env python

import sys
import socket

try:
    CFG_ROOT = '/etc/truechain'
    sys.path.append(CFG_ROOT)
    import local_config
    print("loaded local_config.py from %s" % CFG_ROOT)
except ImportError:
    print("Attempting to load local_config.py from %s" % CFG_ROOT)
    from trueconsensus import local_config
except Exception as E:
    quit("Failed to load local_config.py!")

from local_config import PEER_NETWORK_FILE


def reserve_free_port(count=1):
    """
    Return a list of n free port numbers on localhost

    # Credits:
    1. David North's https://www.dnorth.net/2012/03/17/the-port-0-trick/
    """

    # TODO: either connect this to a registry
    # or launch these local nodes in containers with same port
    # hold #DNSregistry/committee election for snailchain and fastchain
    # and work out what the actual port number it's bound to is
    results = []
    sockets = []
    for x in range(count):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        # work out what the actual port number it's bound to is
        addr, port = s.getsockname()
        results.append(str(port))
        sockets.append(s)

    for s in sockets:
        s.close()

    return results


# print(PEER_NETWORK_FILE)
network_file_content = open(PEER_NETWORK_FILE, 'r').read().split('\n')
# print(network_file_content)
# TODO: configure this in future if the code is running in containers
# on different ports vs if its on different ports vs if its on different Nodes
# vs if this is a test network vs the actual one.
IP_LIST = [l.strip() for l in network_file_content if l]

# print(IP_LIST)
# replica list
# TODO: mature implementation once code is stabilitized
# RL = [(l, basePort+i) for i, l in enumerate(IP_LIST[:pbft_master_id])]
RL = zip(IP_LIST, reserve_free_port(len(IP_LIST)))

# for l in RL:
#     print(":".join(l))
# print(list(RL))
# [print(":".join(l)+"\n") for l in RL]
# modify the same network file with ports attached to IP addresses
with open(PEER_NETWORK_FILE+'.csv', 'w') as nwf:
    [nwf.write(':'.join(l)+"\n") for l in RL]
