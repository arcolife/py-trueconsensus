#!/usr/bin/env python
#
# Copyright (c) 2018 TrueChain Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import unicode_literals

# import os
import sys
# import yaml
import signal
import grpc
# import struct
import time
# import select
from datetime import datetime
# from random import random
from threading import Timer, active_count
from concurrent import futures

from trueconsensus.fastchain import node
from trueconsensus.fastchain.config import config_yaml, \
    THREADING_ENABLED, \
    CLIENT_ADDRESS, \
    _logger, \
    RL

from trueconsensus.snailchain import SnailChain
from trueconsensus.fastchain.bft_committee import NodeBFT, \
    LedgerLog, \
    BFTcommittee

from trueconsensus.fastchain.subprotocol import SubProtoDailyBFT, \
    Mempools

from trueconsensus.proto import request_pb2, \
    request_pb2_grpc

from trueconsensus.utils.interruptable_thread import InterruptableThread


LOCALHOST = '127.0.0.1'
BUF_SIZE = 4096 * 8 * 8
node_instances = {}
NODE_ID = None

# recv_mask = select.EPOLLIN | select.EPOLLPRI | select.EPOLLRDNORM
# send_mask = select.EPOLLOUT | select.EPOLLWRNORM

# class GracefulExit(object):
#     def __enter__(self):
#         # set up signals here
#         # store old signal handlers as instance variables

#     def __exit__(self, type, value, traceback):
#         # restore old signal handlers


def send_ack(_id):
    # TODO: verifications/checks
    return 200


class FastChainServicer(request_pb2_grpc.FastChainServicer):
    # send_ack is exposed here
    def Send(self, request, context):
        """
        Used for intra committee phase communication
        """
        response = request_pb2.GenericResp()
        response.msg = request.inner.type
        response.status = send_ack(request.inner.id)
        NODE_ID = request.dest
        # print("%s => %s" % (_id, NODE_ID))
        n = node_instances[NODE_ID] # NODE_ID is server's ID, that invoked its Check() with RPC
        n.incoming_buffer_map[_id].append(request)
        # n.parse_request(request) # TODO: do this in thread.run()
        # TODO: add request to node's outbuffmap and log this request
        return response

    def Check(self, request, context):
        """
        Liveness probes between replica
        # TODO: replace by devp2p/kadelmia style ping pongs
        """
        global node_instances
        response = request_pb2.GenericResp()
        response.msg = request.inner.type
        # import pdb; pdb.set_trace()
        response.status = send_ack(request.inner.id)
        # TODO: add request to node's log
        _id = request.inner.id # id of server that sent the request (from)
        NODE_ID = request.dest
        # print("%s => %s" % (_id, NODE_ID))
        n = node_instances[NODE_ID] # NODE_ID is server's ID, that invoked its Check() with RPC
        # n.incoming_buffer_map[_id].append(request)
        n.parse_request(request)
        return response

    def NewTxnRequest(self, request, context):
        """
        Client sends transaction to this interface
        """
        # actually receive data
        # recv_flag = True
        # except Exception as E:
        #     _logger.error("Node: [%s], Msg: [%s]" % (n._id, E))
        #     n.clean(fd)
        response = request_pb2.GenericResp()
        NODE_ID = request.dest

        # TODO:
        # empty data -> close conn / check if applicable,
        # now that we have gRPC instead of socket
        # import pdb; pdb.set_trace()
        if not request.data:  # and recv_flag:
            # print("%s => %s" % (_id, NODE_ID))
            _logger.debug("Node: [%s], Msg: [Received Empty Data in Transaction]" % (NODE_ID))
            # n.clean(NODE_ID)
            response.msg = "No Content"
            response.status = 204
        else:
            n = node_instances[NODE_ID] # NODE_ID is server's ID, that invoked its Check() with RPC
            # TODO: segregate into receiever
            # finally got data on receval
            # _logger.debug("Node: [%s], ChunkLength: [%s]" % (NODE_ID, len(data)))
            n.txpool.append(request)
            response.msg = "received transaction"
            response.status = 200
        _logger.debug("Node: [%s], Msg: [Received Client Request for Acc Nonce %s for Recipient %s]" %
            (NODE_ID, request.data.AccountNonce, request.data.Recipient))
        # TODO: Add txn to node's txnpool, regardless of bad request. Keep track
        return response


def suicide():
    """
    #TODO
    add code for trapping continue signal (custom code)
    to avoid stopping the server.
    """
    print("Active Thread Count: ", active_count())
    print("End time: ", datetime.now())
    # os.kill(os.getpid(), signal.SIGINT)
    return


def signal_handler(event, frame):
    sys.stdout.write("handling signal: %s\n" % event)
    sys.stdout.flush()
    countdown = 0  # seconds, TODO: configurable
    if event == signal.SIGINT:
        print("Committing deliberate suicide in %s seconds" % countdown)
        t = Timer(countdown, suicide)
        t.start()
        sys.exit(130)  # Ctrl-C for bash


def init_grpc_server(ip, port, try_new=False):
    """
    initiates the gRPC server for the node
    """
    # try:
    #     ip, port = RL[_id]
    # except IndexError as E:
    #     quit("%s Ran out of replica list. No more server config to try" % E)

    # import pdb; pdb.set_trace()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    request_pb2_grpc.add_FastChainServicer_to_server(FastChainServicer(), server)
    rc = server.add_insecure_port('%s:%s' % (ip, port)) # TODO: setup SSL/TLS
    if rc == 0 and try_new is True:
        port = 0 # "port 0 trick"
        # TODO: check if you can use add_insecure_port twice in a row
        # TODO: register these ports somehwere in a registry for nodes to automagically pick up replica sets
        # TODO: temporary hack for running a multi node setup locally
        # https://github.com/grpc/grpc/blob/master/src/python/grpcio/grpc/__init__.py#L1279-L1290
        port = server.add_insecure_port('%s:%s' % (ip, port)) # TODO: setup SSL/TLS
    elif rc == 0 and try_new is False:
        raise OSError

    server.start()
    # import pdb; pdb.set_trace()
    return server, port


def get_pbft_primary_replica():
    # TODO
    pass


class NonThreadedExecution(object):
    '''
    Finds sockets that aren't busy and attempts to establish and
    launches test nodes as individual processes
    '''
    def __init__(self, node_id=None):
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        self._id = node_id

    def init_server_socket(self):
        """
        triggers setup using testbed. Increments given server id
        if that (ip, socket) from Replica List RL is already in use.
        """
        s = None
        for address in RL:
            try:
                # TODO: find use of try_new=True in init_grpc_server()
                s = init_grpc_server(*address)
                break
            except OSError as err:
                msg = "{} -- while contending for gRPC server address: [{}]"
                _logger.error(msg.format(err, address))

        if not s:
            quit("Couldn't find a gRPC address to pair with, Replica List")

        return s, RL.index(address)

    def launch(self):
        """
        call flow graph:

        -> server_loop() -> parse_request() ->
        self.request_types[req.inner.type]() -> [] process_client_request() ->
        execute_in_order() -> execute() ->
            - self.bank.process_request()
            - client_sock.send()
            - record()
        -> suicide() when Max Requests reached..
        """
        # currently a hack for mapping ID to IP:PORT availability
        if self._id is None:
            self.gsock, self._id = self.init_server_socket()
        else:
            # TODO: handle inconsistency in id allotment throguh
            # init_server_socket() vs init_grpc_server() if using try_new
            self.gsock, port = init_grpc_server(*RL[self._id])

        if port != RL[self._id][1]:
            RL[self._id][1] = port
        msg = "Node: [%s], Msg: [Firing up gRPC channel], Address: %s"
        print(msg % (self._id, RL[self._id]))
        _logger.debug(msg % (self._id, RL[self._id]))

        # this is overriden by the vacant server ID check in init_grpc_server() itself
        # if self.server is None:
        #     _logger.error("Unable to find free socket. Last tried id: %s" % _id)
        #     return

        block_size = config_yaml["bft_committee"]["block_size"]
        # todo: find out primary N by election instead of hardcoding
        n = node.Node(
            self._id,
            0,
            len(RL),
            block_size=block_size,
            max_requests=config_yaml['testbed']['requests']['max'],
            max_retries=config_yaml['testbed']['max_retries']
        )

        global node_instances
        node_instances[self._id] = n

        global NODE_ID
        NODE_ID = self._id

        # n.init_replica_map(self.server)
        replica_tracker = n.init_replica_map(self.gsock)

        # if healthy replica above 2f+1 threshold  (33% fault tolerance)
        # are up, continue to function as it would, normally
        faulty = [i for i in replica_tracker if
                  replica_tracker[i] is False]

        healthy_nodes = [i for i in replica_tracker if
                         replica_tracker[i] is True]
        if faulty:
            # TODO: if the ratio is nearing a failure, take actions
            if len(healthy_nodes) < 2 * len(faulty) + 1:
                n.declare_committee_ambush()
                _logger.error("Committee corrupted. Faulty Node IDs:"
                              "=> {%s}" % faulty)
            # if the replica are unreachable then hold committee election
            # from snailchain
            # TODO: wait on furthre operations until committee replenished
            n.replace_faulty_replica()
        # # grpc instance
        # s = n.replica_map[n._id]
        _logger.info("Node: [%s], Current Primary: [%s]" % (n._id, n.primary))
        msg = "Node: [%s], Msg: [INIT SERVER LOOP]" % (n._id)
        print(msg)
        _logger.info(msg)
        # t = Timer(5, n.try_client)
        # t.start()

        while True:
            # trigger events based on flags ?
            data = None

            # import pdb; pdb.set_trace()

            # send data
            # TODO: send this reply to all slowchain members
            for target_node in healthy_nodes:
                if len(n.outgoing_buffer_map) > 0:
                    try:
                        # TODO: integrate with config_yaml["bft_committee"]["block_frequency"]
                        response = n.send_reply_to_client(target_node)
                        n.outgoing_buffer_map.pop(-1)
                        _logger.info("Node: [%s], Msg: [Block sent to client], Status: [%d], Response: [%s]"
                            % (n._id, response.status, response.value))
                        # new_txn = request_pb2.NewTxnRequest()
                        # new_txn.data = message.gen_txn(nonce, price, gas_limit, _to, fee, asset_bytes)
                    except IndexError:
                        pass
                    except:
                        #raise
                        n.clean(target_node)


                # process outmap /inmap in the same loop?
                if n.primary is n._id: #and n.invalid_primary is not True:
                    while(len(n.txpool) > config_yaml["bft_committee"]["block_size"]):
                        # if n.clear_for_next_block:
                        # form a REQU type request from here on,
                        # previously handled by generate_requests_dat script
                        # req = message.add_sig(current_key, _id, seq, view, "REQU", msg, i)
                        block_pool = n.txpool[-block_size:]
                        n.process_client_request(block_pool)
                        del n.txpool[-block_size:]
                        n.last_block_pool = block_pool # but keep n.block_pool for backup
                        # n.parse_request(n.incoming_buffer_map[target_node][-1])
                        # n.incoming_buffer_map[target_node].pop(-1)
                        # else:
                        #     _logger.info("Node: [%s], Msg: [Block in Wait queue]" % (n._id))
                        #     continue

            time.sleep(4)
            _logger.debug("Node: [%s], Waiting for next batch.." % (n._id))


# class ThreadedExecution(InterruptableThread):
#     '''
#     Launches test nodes as threads
#     '''
#     def __init__(self, _id):
#         self._id = _id
#         self.countdown = 3 # time taken before node stops itself
#         InterruptableThread.__init__(self)
#
#     # def server_loop(self):
#     def run(self):
#         """
#         call flow graph:
#
#         -> server_loop() -> parse_request() ->
#         self.request_types[req.inner.type]() -> [] process_client_request() ->
#         execute_in_order() -> execute() ->
#             - self.bank.process_request()
#             - client_sock.send()
#             - record()
#         -> suicide() when Max Requests reached..
#         """
#         sys.stdout.write("run started\n")
#         sys.stdout.flush()
#         block_size = config_yaml["bft_committee"]["block_size"]
#         n = node.Node(
#             self._id,
#             0,
#             pbft_master_id,
#             block_size=block_size,
#             max_requests=config_yaml['testbed']['requests']['max'],
#             max_retries=config_yaml['testbed']['max_retries']
#         )
#
#         print("Active Thread Count: ", active_count())
#
#         global node_instances
#         node_instances[self._id] = n
#
#         global NODE_ID
#         NODE_ID = self._id
#
#         self.server = init_grpc_server(self._id)
#
#         replica_status = n.init_replica_map(self.server)
#         # import pdb; pdb.set_trace()
#         if not all(replica_status.values()):
#             _logger.warn("Couldn't reach all replica in the list. Unreachable => {%s}" %
#                 [i for i in replica_status if replica_status[i] is False])
#
#         # # grpc instance
#         # s = n.replica_map[n._id]
#         _logger.info("Node: [%s], Current Primary: [%s]" % (n._id, n.primary))
#         msg = "Node: [%s], Msg: [INIT SERVER LOOP]" % (n._id)
#         print(msg)
#         _logger.info(msg)
#         # t = Timer(5, n.try_client)
#         # t.start()
#
#         while not self.is_stop_requested():
#             # trigger events based on flags ?
#             data = None
#
#             for target_node in range(pbft_master_id):
#                 if target_node == self._id:
#                     continue
#
#                 # send data
#                 # TODO: send this reply to all slowchain members
#                 if len(n.outgoing_buffer_map[target_node]) > 0:
#                     try:
#                         # TODO: integrate with config_yaml["bft_committee"]["block_frequency"]
#                         response = n.send_reply_to_client(target_node)
#                         n.outgoing_buffer_map[target_node].pop(-1)
#                         _logger.info("Node: [%s], Msg: [Block sent to client], Status: [%d], Response: [%s]"
#                             % (n._id, response.status, response.value))
#                         # new_txn = request_pb2.NewTxnRequest()
#                         # new_txn.data = message.gen_txn(nonce, price, gas_limit, _to, fee, asset_bytes)
#                     except IndexError:
#                         pass
#                     except Exception as E:
#                         _logger.debug("Node [%s], ErrorMsg: [%s]"
#                                       % (n._id, E))
#                         n.clean(target_node)
#
#                 # process outmap /inmap in the same loop?
#                 if n.primary is n._id: #and n.invalid_primary is not True:
#                     # threaded?
#                     while(len(n.txpool) > config_yaml["bft_committee"]["block_size"]):
#                         # if n.clear_for_next_block:
#                         # form a REQU type request from here on,
#                         # previously handled by generate_requests_dat script
#                         # req = message.add_sig(current_key, _id, seq, view, "REQU", msg, i)
#                         block_pool = n.txpool[-block_size:]
#                         n.process_client_request(block_pool)
#                         del n.txpool[-block_size:]
#                         n.last_block_pool = block_pool # but keep n.block_pool for backup
#                         # n.parse_request(n.incoming_buffer_map[target_node][-1])
#                         # n.incoming_buffer_map[target_node].pop(-1)
#                         # else:
#                         #     _logger.info("Node: [%s], Msg: [Block in Wait queue]" % (n._id))
#                         #     continue
#
#             time.sleep(4)
#             msg = "Node: [%s], Waiting for next batch.. Current primary - [%s]"
#             _logger.debug(msg % (n._id, n.primary))
#
#         self.server.stop(0)
#         # n.debug_print_bank()
#         sys.stdout.write("run exited\n")
#         sys.stdout.flush()


def main(node_id=None):
    print("Start time: ", datetime.now())
    print("Threading enabled: ", THREADING_ENABLED)

    # signal.signal(signal.SIGINT, self.debug_print_bank)

    # with GracefulExit():
    #     pass
    print("Replica List: %s" % RL)
    print("Expected Client address: %s" % CLIENT_ADDRESS)


    # import pdb; pdb.set_trace()
    NonThreadedExecution(node_id=node_id).launch()

    # if THREADING_ENABLED:
    #
    #     # signal.signal(signal.SIGINT, signal_handler)
    #     # signal.signal(signal.SIGTERM, signal_handler)
    #     thread_pool = []
    #
    #     for _id in range(pbft_master_id):
    #         # sys.stdout.write("Active Thread Count: ", active_count())
    #         node_instance = ThreadedExecution(_id)
    #         node_instance.start()
    #         thread_pool.append(node_instance)
    #
    #     for thread in thread_pool:
    #         thread.join()
    #
    #     sys.stdout.write("all exited\n")
    #     sys.stdout.flush()
    # else:
    #     # TODO: add gunicorn worker id based logic here
    #     NonThreadedExecution(node_id=node_id).launch()

    print("End time: ", datetime.now())


if __name__ == "__main__":
    # import pdb; pdb.set_trace()
    try:
        main()
    except KeyboardInterrupt:
        quit("Ctrl-C'ed. Exiting..")
