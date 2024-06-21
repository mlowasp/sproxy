import argparse
import sys
import time
import configparser

from modules import sproxy_server as Server
from modules import sproxy_console as Console

if __name__ == '__main__':

    parser = argparse.ArgumentParser("sproxy")
    parser.add_argument("--config", help="<file> to be used as the configuration file.", required=False, default="etc/sproxy.conf")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    Console.pmsg("Starting sproxy...")
    Server.main(config)

            