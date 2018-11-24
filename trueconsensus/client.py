#!/bin/env python

import os
import sys
import grpc
import struct
import select
import time
from concurrent import futures

from trueconsensus.dapps.bank import Bank, Users
from trueconsensus.proto import request_pb2, \
    request_pb2_grpc, \
    proto_message as message
from trueconsensus.fastchain.config import CLIENT_ADDRESS, \
    CLIENT_ID, \
    CLIENT_ADDRESS, \
    RL, \
    client_logger, \
    config_general, \
    config_yaml
    # pbft_master_id, \

kill_flag = False
start_time = time.time()
GRPC_REQUEST_TIMEOUT = config_yaml["grpc"]["timeout"]


def send_ack(_id):
    # TODO: verifications/checks
    return 200


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
    request_pb2_grpc.add_ClientReceiverServicer_to_server(ClientReceiverServicer(), server)
    rc = server.add_insecure_port('%s:%s' % (ip, port)) # TODO: setup SSL/TLS
    # TODO: if you change client port, server should have a way of knowing.
    # Also, client sending the request shouldn't be DDOS vulnerable. / sybil attack
    # if rc == 0 and try_new is True:
    #     port = 0 # "port 0 trick"
    #     # TODO: check if you can use add_insecure_port twice in a row
    #     # TODO: register these ports somehwere in a registry for nodes to automagically pick up replica sets
    #     # TODO: temporary hack for running a multi node setup locally
    #     # https://github.com/grpc/grpc/blob/master/src/python/grpcio/grpc/__init__.py#L1279-L1290
    #     port = server.add_insecure_port('%s:%s' % (ip, port)) # TODO: setup SSL/TLS
    # elif rc == 0 and try_new is False:
    #     raise OSError

    server.start()
    # import pdb; pdb.set_trace()
    return server


class ClientReceiverServicer(request_pb2_grpc.ClientReceiverServicer):
    def PbftReplyReceiver(self, request, context):
        response = request_pb2.PbftBlock()
        stamp_to_chain(request)
        return response

    def Check(self, request, context):
        response = request_pb2.GenericResp()
        response.msg = request.inner.type
        response.status = send_ack(request.inner.id)
        stamp_to_chain(request, test_connection=True)
        return response

# def recv_response():

def stamp_to_chain(req, test_connection=False):
    client_msg = "[%s] SEQUENCE: 0 REPLICA: 0 START\n" % (time.time())
    # f.write(client_msg)
    client_logger.debug(client_msg)
    import pdb; pdb.set_trace()
    client_msg = "[%s] SEQUENCE: %s - REPLICA: %s\n" % \
        (time.time(), req.inner.seq, req.inner.id)
    # f.write(client_msg)
    client_logger.info(client_msg)
    count += 1
    if req.inner.seq % 100 == 0:
    #if True:
        client_logger.debug("CLIENT [%s] SEQUENCE: %s" % (CLIENT_ID, req.inner.seq))
    #if req.inner.seq == n:
    if count == N * len(RL):
        kill_flag = True
        end_time = time.time()
        client_logger.debug('CLIENT [%s] total time spent with chain: %s' % (end_time - start_time))
        # f.close()


def gen_requests():
    client_key_pub = ecdsa_sig.get_asymm_key(CLIENT_ID-1, ktype='verify')
    client_key_pem = ecdsa_sig.get_asymm_key(CLIENT_ID-1, ktype='sign')
    keys_to_seq_tracker = defaultdict.fromkeys(range(len(RL)), 0)


def dial_committee(channel, target_node):
    # generate bank ids and add 1000 to every account
    # bank = bank.bank(id, 1000)
    # TODO: check if bi directional channel is needed
    stub = request_pb2_grpc.FastChainStub(channel)
    new_txn = request_pb2.Transaction()
    # nonce, price, gas_limit, _to, fee, asset_bytes
    new_txn.dest = target_node
    new_txn.source = CLIENT_ID
    # new_txn.data =
    message.gen_txn_data(new_txn.data)
    response = stub.NewTxnRequest(new_txn, timeout=GRPC_REQUEST_TIMEOUT)
    return response


def send_requests(total, pbft_master_id, all_done=False):
    UserTap = Users()
    UserTap.open_db_conn()
    UserTap.gen_accounts(len(RL))
    start_time = time.time()

    print("Replica List: %s" % RL)
    print("Client address: %s" % CLIENT_ADDRESS)
    RL_REQUEST_TRACKER = dict.fromkeys(range(len(RL)), False)

    for i in range(total):
        print("Request #%s" % str(i+1))
        # default to sending to all nodes if unable to reach primary
        target_node = pbft_master_id
        # import pdb; pdb.set_trace()
        try:
            channel = grpc.insecure_channel(":".join(RL[target_node]))
            # import pdb; pdb.set_trace()
            response = dial_committee(channel, target_node)

            # signify request being sent
            # RL_REQUEST_TRACKER[target_node] += 1
            print("Target Node: %s, Response: %s" % (target_node, response))
        except Exception as e:  # broad catch
            # import pdb; pdb.set_trace()
            client_logger.error("Msg: [failed to send to primary node], Target: %s, Error => {%s}" % \
                                (RL[target_node], e))
            client_logger.info("Attempting to broadcast message to replica list..")
            for target_node in range(len(RL)):
                # RL_REQUEST_TRACKER = dict.fromkeys(range(len(RL)), 0)
                channel = grpc.insecure_channel(":".join(RL[target_node]))
                # RL_REQUEST_TRACKER[target_node] += 1
                try:
                    response = dial_committee(channel, target_node)
                    print("Target Node: %s, Response: %s" % (target_node, response))
                except Exception as e:  # broad catch
                    msg = "Msg: [also failed to send to replica node], Target: %s, Error => {%s}"
                    client_logger.error(msg % (RL[target_node], e))

        # if all(RL_REQUEST_TRACKER.values()):
        #         all_done = True
        time.sleep(0.5)

    client_logger.info("Done sending... wait for receives")
    UserTap.close_db_conn()


if __name__ == '__main__':
    try:
        # import pdb; pdb.set_trace()
        if len(sys.argv) > 2:
            master = int(sys.argv[1])
            # number of requests
            n = int(sys.argv[2])
        else:
            master = 0
            # number of requests
            n = 50

        send_requests(n, master)
        client_serv = init_grpc_server(*CLIENT_ADDRESS)

        while True:
            time.sleep(1)
            if kill_flag:
                # give laggy requests some time to show up
                time.sleep(1)
                sys.exit()

        # ClientReceiverServicer

    except KeyboardInterrupt:
        quit("Ctrl-C'ed. Exiting..")
