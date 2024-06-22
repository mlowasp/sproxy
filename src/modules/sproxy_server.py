import logging
import select
import socket
import struct
import socks
import sys
import random
import hashlib
import mysql.connector

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
        self.connection_manager = {}
        for backend in args['backends']:
            self.connection_manager[backend] = 0

class LoadBalancer(StreamRequestHandler):

    def handle(self):
        self.load_balancing_mode = self.server.args["load_balancing_mode"]
        self.log_level = self.server.args["log_level"]
        self.socks_version = int(self.server.args["socks_version"])
        self.backends = self.server.args["backends"]
        self.username = self.server.args["auth_username"]
        self.password = self.server.args["auth_password"]
        self.auth_sha512 = self.server.args["auth_sha512"]
        self.auth_mode = self.server.args["auth_mode"]
        self.backend_mode = self.server.args["backend_mode"]
        self.database_mode = self.server.args["database_mode"]
        self.database_port = self.server.args["database_port"]
        self.database_hostname = self.server.args["database_hostname"]
        self.database_username = self.server.args["database_username"]
        self.database_password = self.server.args["database_password"]
        self.database_dbname = self.server.args["database_dbname"]

        if self.auth_mode == 'database' or self.backend_mode == 'database':
            self.cnx = mysql.connector.connect(user=self.database_username, password=self.database_password,
                    host=self.database_hostname,
                    port=self.database_port,
                    database=self.database_dbname)

        if self.backend_mode == 'database':
            sql = "SELECT id, proxy FROM backends"
            try:
                self.cursor = self.cnx.cursor()
                self.cursor.execute(sql)
                backends = []
                for (id, proxy) in self.cursor:
                    backends.append(proxy)

                a = set(backends)
                b = set(self.backends)
                if a != b:
                    self.backends = backends
                    self.connection_manager = {}
                    for backend in self.backends:
                        self.connection_manager[backend] = 0

            except mysql.connector.Error as err:
                if self.log_level:
                    logging.info(err.msg)
            try:
                self.cursor.close()
            except:
                pass

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
        if self.auth_mode != "none":
            self.auth = True

        # accept only USERNAME/PASSWORD auth
        if self.auth and 2 not in set(methods):
            # close connection
            self.server.close_request(self.request)
            return

        # send welcome message
        self.connection.sendall(struct.pack("!BB", self.socks_version, 2))

        if not self.verify_credentials():
            if self.log_level:
                logging.info('Invalid username/password for %s:%s' % self.client_address)
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
                    proxy = False
                    if self.load_balancing_mode == "random":
                        proxy = random.choice(self.backends)
                    if self.load_balancing_mode == "leastconn":
                        min_conn = min(self.server.connection_manager.values())
                        possible_proxy = []
                        for key, value in self.server.connection_manager.items():
                            if value <= min_conn:
                                possible_proxy.append(key)
                        proxy = random.choice(possible_proxy)

                    if proxy.find("socks5://") >= 0:
                        proxy_info = proxy.split("socks5://")[1]
                        if proxy_info.find("@") >= 0:
                            proxy_hostname = proxy_info.split("@")[1].split(":")[0]
                            proxy_port = int(proxy_info.split("@")[1].split(":")[1])
                            proxy_username = proxy_info.split("@")[0].split(":")[0]
                            proxy_password = proxy_info.split("@")[0].split(":")[1]
                            remote.set_proxy(socks.SOCKS5, proxy_hostname, proxy_port, True, proxy_username, proxy_password)
                        else:
                            proxy_hostname = proxy_info.split(":")[0]
                            proxy_port = int(proxy_info.split(":")[1])
                            remote.set_proxy(socks.SOCKS5, proxy_hostname, proxy_port)

                    if proxy.find("socks4://") >= 0:
                        proxy_info = proxy.split("socks4://")[1]
                        if proxy_info.find("@") >= 0:
                            proxy_hostname = proxy_info.split("@")[1].split(":")[0]
                            proxy_port = int(proxy_info.split("@")[1].split(":")[1])
                            proxy_username = proxy_info.split("@")[0].split(":")[0]
                            proxy_password = proxy_info.split("@")[0].split(":")[1]
                            remote.set_proxy(socks.SOCKS4, proxy_hostname, proxy_port, True, proxy_username, proxy_password)
                        else:
                            proxy_hostname = proxy_info.split(":")[0]
                            proxy_port = int(proxy_info.split(":")[1])
                            remote.set_proxy(socks.SOCKS4, proxy_hostname, proxy_port)

                except:
                    if self.log_level:
                        logging.info('Failed to select backend. Dropping connection...')
                        self.server.close_request(self.request)
                        return

                if self.load_balancing_mode == "leastconn":
                    self.server.connection_manager[proxy] = self.server.connection_manager[proxy] + 1

                remote.connect((address, port))
                bind_address = remote.getsockname()
                if self.log_level:
                    logging.info('Connected to %s %s via [%s]' % (address, port, proxy))
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

        if self.load_balancing_mode == "leastconn":
            self.server.connection_manager[proxy] = self.server.connection_manager[proxy] - 1

        if self.auth_mode == 'database' or self.backend_mode == 'database':
            self.cnx.close()

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

        if not self.auth or (
                self.auth
                and self.auth_mode == "config"
                and not self.auth_sha512
                and username == self.username
                and password == self.password
            ) or (
                self.auth
                and self.auth_mode == "config"
                and self.auth_sha512
                and username == self.username
                and self.password_hash(password) == self.password
            ):
            # success, status = 0
            response = struct.pack("!BB", version, 0)
            self.connection.sendall(response)
            return True

        if self.auth and self.auth_mode == "database":
            self.cursor = self.cnx.cursor()
            sql = "SELECT username,password FROM users WHERE username='%s'" % username
            try:
                self.cursor.execute(sql)
                for (dbusername, dbpassword) in self.cursor:
                    if self.auth_sha512:
                        password = self.password_hash(password)

                    if password == dbpassword:
                        response = struct.pack("!BB", version, 0)
                        self.connection.sendall(response)
                        self.cursor.close()
                        return True

            except mysql.connector.Error as err:
                if self.log_level:
                    logging.info('DATABASE ERROR: %s' % err.msg)
            except Exception as e:
                if self.log_level:
                    logging.info('Unknown exception %s' % repr(e))

            try:
                self.cursor.close()
            except:
                pass

        # failure, status != 0
        response = struct.pack("!BB", version, 0xFF)
        self.connection.sendall(response)
        self.server.close_request(self.request)
        return False

    def generate_failed_reply(self, address_type, error_number):
        return struct.pack("!BBBBIH", self.socks_version, error_number, 0, address_type, 0, 0)

    def password_hash(self, password):
        password_hash = hashlib.sha512(password.encode('utf-8')).hexdigest()
        return password_hash

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

    auth_mode = "config"
    auth_sha512 = False
    backend_mode = "config"
    log_level = logging.INFO
    log_filename = "sproxy.log"
    load_balancing_mode = "random"
    database_hostname = False
    database_username = False
    database_password = False
    database_port = False
    database_dbname = False
    database_mode = False
    if "settings" in config:
        if "AUTH_SHA512" in config["settings"]:
            if config["settings"]["AUTH_SHA512"] == "true":
                auth_sha512 = True
        if "DATABASE_HOSTNAME" in config["settings"]:
            database_hostname = config["settings"]["DATABASE_HOSTNAME"]
        if "DATABASE_USERNAME" in config["settings"]:
            database_username = config["settings"]["DATABASE_USERNAME"]
        if "DATABASE_PASSWORD" in config["settings"]:
            database_password = config["settings"]["DATABASE_PASSWORD"]
        if "DATABASE_PORT" in config["settings"]:
            database_port = config["settings"]["DATABASE_PORT"]
        if "DATABASE_DBNAME" in config["settings"]:
            database_dbname = config["settings"]["DATABASE_DBNAME"]
        if "DATABASE_MODE" in config["settings"]:
            database_mode = config["settings"]["DATABASE_MODE"]
        if "LOAD_BALANCING_MODE" in config["settings"]:
            load_balancing_mode = config["settings"]["LOAD_BALANCING_MODE"]
        if "AUTH_MODE" in config["settings"]:
            auth_mode = config["settings"]["AUTH_MODE"]
        if "BACKEND_MODE" in config["settings"]:
            backend_mode = config["settings"]["BACKEND_MODE"]
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
        # if "SOCKS_VERSION" in config["frontend"]:
        #     socks_version = config["frontend"]["SOCKS_VERSION"]

    backends = []
    if backend_mode == "config":
        if "backend" in config:
            for key in config["backend"]:
                backends.append(config["backend"][key])

    if backend_mode == "database":
        cnx = mysql.connector.connect(user=database_username, password=database_password,
                    host=database_hostname,
                    port=database_port,
                    database=database_dbname)
        cursor = cnx.cursor()
        sql = "SELECT id,proxy FROM backends"
        try:
            cursor = cnx.cursor()
            cursor.execute(sql)
            for (id, proxy) in cursor:
                backends.append(proxy)
            cursor.close()
            cnx.close()
        except:
            pass

    args = {}
    args["load_balancing_mode"] = load_balancing_mode
    args["log_level"] = log_level
    args["socks_version"] = socks_version
    args["backends"] = backends
    args["auth_username"] = auth_username
    args["auth_password"] = auth_password
    args["auth_sha512"] = auth_sha512
    args["auth_mode"] = auth_mode
    args["backend_mode"] = backend_mode
    args["database_hostname"] = database_hostname
    args["database_username"] = database_username
    args["database_password"] = database_password
    args["database_port"] = database_port
    args["database_dbname"] = database_dbname
    args["database_mode"] = database_mode

    with ThreadingTCPServer((listen_ip, int(listen_port)), LoadBalancer, args) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)