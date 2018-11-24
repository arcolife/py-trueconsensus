#!/bin/env python

import os
import sys
import yaml
import logging
import configparser
# from subprocess import check_output
# from pykwalify import core as pykwalify_core
# from pykwalify import errors as pykwalify_errors
from logging.handlers import RotatingFileHandler

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

from local_config import CFG_YAML_PATH, \
                         CFG_GENERAL_PATH, \
                         PEER_NETWORK_FILE, \
                         TEST_MODE


def load_config(path, no_val=False):
    """
    general logistics such as log file paths in logistics CFG
    """
    if no_val:
        config = configparser.ConfigParser(allow_no_value=True)
    else:
        config = configparser.ConfigParser()
    config.read(path)

    return config


def load_yaml_config(path, no_val=False):
    """
    general tunables specified in YAML
    """
    with open(path, "r") as config_file:
        pbft_config = yaml.safe_load(config_file)

    # _logger.debug("PBFT config {} yaml loaded".format(path))

    # # Validate base config for Browbeat format
    # _validate_yaml("pbft", pbft_config)
    # _logger.info("Config {} validated".format(path))
    return pbft_config

#
# def _validate_yaml(schema, config):
#     """Raises exception if config is invalid.
#     :param schema: The schema to validate with (pbft, pow, hybrid...)
#     :param config: Loaded yaml to validate
#     """
#     check = pykwalify_core.Core(
#         source_data=config,
#         schema_files=["{}/{}.yml".format(conf_schema_path, schema)])
#     try:
#         check.validate(raise_exception=True)
#     except pykwalify_errors.SchemaError as e:
#         _logger.error("Schema validation failed")
#         raise Exception("File does not conform to {} schema: {}".format(schema, e))


config_general = load_config(CFG_GENERAL_PATH)

LOG_ROOT = config_general.get("log", "root_folder")

try:
    if not os.path.exists(LOG_ROOT):
        os.makedirs(LOG_ROOT)
except PermissionError:
    quit("[Permission Denied] during creation of log file dir: %s" % LOG_ROOT)
except Exception as E:
    quit("Error: [%s] - Couldn't create log file dir: %s" % (E, LOG_ROOT))

FMT = "[%(asctime)s] [%(levelname)s ] " + \
      "[%(filename)s:%(lineno)d:%(funcName)s()] - %(message)s"
FSIZE = int(config_general.get("log", "max_log_size"))


def setup_logger(log_type, fname):
    _logger = logging.getLogger(fname)
    formatter = logging.Formatter(FMT)
    log_path = os.path.join(LOG_ROOT, fname)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=FSIZE,
        backupCount=1
    )
    handler.setFormatter(formatter)
    _logger.root.level = logging.DEBUG
    _logger.addHandler(handler)

    # _logger = logging.getLogger("pbftx.config")
    print("Storing %s logs to file: %s" % (log_type, log_path))
    return _logger


# main pbft logger
_logger = setup_logger('engine', config_general.get("log", "server_logfile"))
# client logger
client_logger = setup_logger('client', config_general.get("log", "client_logfile"))
config_yaml = load_yaml_config(CFG_YAML_PATH)
KD = config_general.get("general", "pem_keystore_path")
# pbft_master_id = config_yaml['testbed']['total'] - 1


basePort = config_yaml["general"]["base_port"]

# if 'TEST_MODE' in locals():
#     RL = [address.split(":") for address in IP_LIST]
#     CLIENT_ADDRESS = RL.pop()
#     # incase it was already part of /etc/truechain/local_config.py
#     if not 'THREADING_ENABLED' in locals():
#         THREADING_ENABLED = config_yaml["testbed"]["threading_enabled"]
if TEST_MODE:
    network_file_content = open(PEER_NETWORK_FILE+'.csv', 'r').read().split('\n')
    IP_LIST = [l.strip() for l in network_file_content if l]
    RL = [address.split(":") for address in IP_LIST]
    THREADING_ENABLED = config_yaml["testbed"]["threading_enabled"]
else:
    network_file_content = open(PEER_NETWORK_FILE, 'r').read().split('\n')
    IP_LIST = [l.strip() for l in network_file_content if l]
    RL = [(ip, basePort) for ip in IP_LIST]
    THREADING_ENABLED = False

CLIENT_ADDRESS = RL.pop()
CLIENT_ID = config_yaml["testbed"]["client_id"]  # public address essentially

# We reserve the last IP as the client
# CLIENT_ADDRESS = ((IP_LIST[CLIENT_ID-1], basePort+CLIENT_ID-1))
