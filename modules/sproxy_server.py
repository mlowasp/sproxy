import logging
import select
import socket
import struct
import socks
import sys
import random

from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler
from . import sproxy_console as Console

class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, args = {}):
        TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.args = args        

class LoadBalancer(StreamRequestHandler):

    def handle(self):
        self.load_balancing_mode = self.server.args["load_balancing_mode"]
        self.log_level = self.server.args["log_level"]
        self.socks_version = int(self.server.args["socks_version"])
        self.backends = self.server.args["backends"]
        self.username = self.server.args["auth_username"]
        self.password = self.server.args["auth_password"]
        
        if self.log_level:
            logging.info('Accepting connection from %s:%s' % self.client_address)

        # greeting header
        # read and unpack 2 bytes from a client
        header = self.connection.recv(2)
        version, nmethods = struct.unpack("!BB", header)

        # socks 5
        assert version == self.socks_version
        assert nmethods > 0

        # get available methods
        methods = self.get_available_methods(nmethods)

        self.auth = False
        if self.username and self.password:
            self.auth = True

        # accept only USERNAME/PASSWORD auth
        if self.auth and 2 not in set(methods):
            # close connection
            self.server.close_request(self.request)
            return

        # send welcome message
        self.connection.sendall(struct.pack("!BB", self.socks_version, 2))

        if not self.verify_credentials():
            return

        # request
        version, cmd, _, address_type = struct.unpack("!BBBB", self.connection.recv(4))
        assert version == self.socks_version

        if address_type == 1:  # IPv4
            inet_type = socket.AF_INET
            address = socket.inet_ntop(inet_type, self.connection.recv(4))
        elif address_type == 3:  # Domain name
            domain_length = self.connection.recv(1)[0]
            address = self.connection.recv(domain_length)
            address = socket.gethostbyname(address)
        elif address_type == 4: # IPv6
            inet_type = socket.AF_INET6
            address = socket.inet_ntop(inet_type, self.connection.recv(16))
        port = struct.unpack('!H', self.connection.recv(2))[0]

        # reply
        try:
            if cmd == 1:  # CONNECT
                remote = socks.socksocket()
                try:                    
                    if self.load_balancing_mode == "random" or self.load_balancing_mode == "leastconn":
                        proxy = random.choice(self.backends)
                        proxy = proxy.split("socks5://")[1]
                        if proxy.find("@") >= 0:
                            proxy_hostname = proxy.split("@")[1].split(":")[0]
                            proxy_port = int(proxy.split("@")[1].split(":")[1])
                            proxy_username = proxy.split("@")[0].split(":")[0]
                            proxy_password = proxy.split("@")[0].split(":")[1]
                            remote.set_proxy(socks.SOCKS5, proxy_hostname, proxy_port, True, proxy_username, proxy_password)
                        else:
                            proxy_hostname = proxy.split(":")[0]
                            proxy_port = int(proxy.split(":")[1])
                            remote.set_proxy(socks.SOCKS5, proxy_hostname, proxy_port)
                except:
                    if self.log_level:
                        logging.info('Failed to select backend. Dropping connection...')
                        self.server.close_request(self.request)
                        return

                # remote = socket.socket(inet_type, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_address = remote.getsockname()
                if self.log_level:
                    logging.info('Connected to %s %s' % (address, port))
            else:
                self.server.close_request(self.request)

            addr = struct.unpack("!I", socket.inet_aton(bind_address[0]))[0]
            port = bind_address[1]
            reply = struct.pack("!BBBBIH", self.socks_version, 0, 0, 1,
                                addr, port)

        except Exception as err:
            logging.error(err)
            # return connection refused error
            reply = self.generate_failed_reply(address_type, 5)

        self.connection.sendall(reply)

        # establish data exchange
        if reply[1] == 0 and cmd == 1:
            self.exchange_loop(self.connection, remote)

        self.server.close_request(self.request)

    def get_available_methods(self, n):
        methods = []
        for i in range(n):
            methods.append(ord(self.connection.recv(1)))
        return methods

    def verify_credentials(self):
        version = ord(self.connection.recv(1))
        assert version == 1

        username_len = ord(self.connection.recv(1))
        username = self.connection.recv(username_len).decode('utf-8')

        password_len = ord(self.connection.recv(1))
        password = self.connection.recv(password_len).decode('utf-8')

        if not self.auth or ( username == self.username and password == self.password ):
            # success, status = 0
            response = struct.pack("!BB", version, 0)
            self.connection.sendall(response)
            return True

        # failure, status != 0
        response = struct.pack("!BB", version, 0xFF)
        self.connection.sendall(response)
        self.server.close_request(self.request)
        return False

    def generate_failed_reply(self, address_type, error_number):
        return struct.pack("!BBBBIH", self.socks_version, error_number, 0, address_type, 0, 0)

    def exchange_loop(self, client, remote):

        while True:

            # wait until client or remote is available for read
            r, w, e = select.select([client, remote], [], [])

            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0:
                    break

            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0:
                    break

def main(config):

    log_level = logging.INFO
    log_filename = "sproxy.log"
    load_balancing_mode = "random"
    if "settings" in config:
        if "LOAD_BALANCING_MODE" in config["settings"]:
            load_balancing_mode = config["settings"]["LOAD_BALANCING_MODE"]
        if "LOG_FILENAME" in config["settings"]:
            log_filename = config["settings"]["LOG_FILENAME"]
        if "LOG_LEVEL" in config["settings"]:
            if config["settings"]["LOG_LEVEL"] == "info":
                log_level = logging.INFO 
            if config["settings"]["LOG_LEVEL"] == "none":
                log_level = False
            if config["settings"]["LOG_LEVEL"] == "debug":
                log_level = logging.DEBUG
    
    if log_level:
        logging.basicConfig(filename=log_filename, level=log_level)
    
    listen_ip = "127.0.0.1"
    listen_port = "1080"
    socks_version = 5
    auth_username = False
    auth_password = False
    if "frontend" in config:      
        if "AUTH_USERNAME" in config["frontend"]:
            auth_username =  config["frontend"]["AUTH_USERNAME"]
        if "AUTH_PASSWORD" in config["frontend"]:
            auth_password =  config["frontend"]["AUTH_PASSWORD"]
        if "LISTEN_IP" in config["frontend"]:
            listen_ip = config["frontend"]["LISTEN_IP"]
        if "LISTEN_PORT" in config["frontend"]:
            listen_port = config["frontend"]["LISTEN_PORT"]
        if "SOCKS_VERSION" in config["frontend"]:
            socks_version = config["frontend"]["SOCKS_VERSION"]

    backends = []
    if "backend" in config:
        for key in config["backend"]:
            backends.append(config["backend"][key])

    args = {}
    args["load_balancing_mode"] = load_balancing_mode
    args["log_level"] = log_level
    args["socks_version"] = socks_version
    args["backends"] = backends
    args["auth_username"] = auth_username
    args["auth_password"] = auth_password

    with ThreadingTCPServer((listen_ip, int(listen_port)), LoadBalancer, args) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)