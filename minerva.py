#!/usr/bin/env python

import sys
from argparse import RawTextHelpFormatter, \
                ArgumentParser


parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                        description="""
                        Hybrid BFT based consensus - standalone engine""")


def consensus_usage():
    parser.add_argument("-i", "--nodeid", nargs='?', const=0, type=int,
                        dest="node_id", action='store',
                        help="ID of node for test mode")
    parser.add_argument("-n", "--nodes", dest="node_count", action='store',
                        help="# of PBFT nodes to be launched")
    parser.add_argument("-c", "--conf", dest="node_id",
                        action='store_true',
                        help="")
    parser.add_argument("-ts", "--tune-settings", dest="tune",
                        action='store_true',
                        help="")


if __name__ == '__main__':
    consensus_usage()
    args = parser.parse_args()
    # if not args.node_id:
    #     try:
    #         node_id = sys.argv[1]
    #     except IndexError:
    #         node_id = None
    try:
        from trueconsensus import engine
        engine.main(int(args.node_id))
        # from trueconsensus import engine_new
        # engine_new.serve()
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        raise
