import argparse
import sys
import time
import configparser
import hashlib
import mysql.connector
import uuid
import os

from mysql.connector import errorcode
from modules import sproxy_server as Server
from modules import sproxy_console as Console

def hash_password(password):
    hash=hashlib.sha512(text.encode('utf-8')).hexdigest()
    return hash

def sha256(text):
    hash=hashlib.sha256(text.encode('utf-8')).hexdigest()
    return hash
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser("sproxy")
    parser.add_argument("--config", help="<file> to be used as the configuration file.", required=False, default="/etc/sproxy/sproxy.conf")
    parser.add_argument("--database-create-tables", help="Create the required database tables.", required=False, action='store_true')
    parser.add_argument("--database-list-backends", help="List of the database backends.", required=False, action='store_true')
    parser.add_argument("--database-list-users", help="List of the database users.", required=False, action='store_true')
    parser.add_argument("--database-add-backend", help="Adds <backend> to the database.", required=False)
    parser.add_argument("--database-remove-backend", help="Removes <backend> from the database.", required=False)
    parser.add_argument("--database-add-user", help="Adds <username:password> to the database.", required=False)
    parser.add_argument("--database-remove-user", help="Removes <username> from the database.", required=False)
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    if args.database_create_tables:
        if config['settings']['DATABASE_MODE'] == "mysql":
            cnx = mysql.connector.connect(user=config['settings']['DATABASE_USERNAME'], password=config['settings']['DATABASE_PASSWORD'],
                    host=config['settings']['DATABASE_HOSTNAME'],
                    port=config['settings']['DATABASE_PORT'],
                    database=config['settings']['DATABASE_DBNAME'])
            cursor = cnx.cursor()
            Console.pmsg("Creating database tables...")
            TABLES = {}
            TABLES['users'] = '''
                CREATE TABLE `users` (
                `id` varchar(64) NOT NULL,
                `username` text DEFAULT NULL,
                `password` text DEFAULT NULL,
                PRIMARY KEY (`id`),
                UNIQUE KEY `username_UNIQUE` (`username`) USING HASH
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
            TABLES['backends'] = '''
                CREATE TABLE `backends` (
                    `id` varchar(64) NOT NULL,
                    `proxy` text DEFAULT NULL,  
                    PRIMARY KEY (`id`),
                    UNIQUE KEY `proxy_UNIQUE` (`proxy`) USING HASH
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
            for table_name in TABLES:
                table_description = TABLES[table_name]
                try:
                    Console.pmsg("Creating table {}: ".format(table_name))
                    cursor.execute(table_description)
                except mysql.connector.Error as err:
                    if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                        Console.perr("already exists.")
                    else:
                        Console.perr(err.msg)
                else:
                    Console.pmsg("OK")

            cursor.close()
            cnx.close()
            sys.exit(0)
        
    if config['settings']['DATABASE_MODE'] == "mysql" and config['settings']['BACKEND_MODE'] == "database":
        cnx = mysql.connector.connect(user=config['settings']['DATABASE_USERNAME'], password=config['settings']['DATABASE_PASSWORD'],
                        host=config['settings']['DATABASE_HOSTNAME'],
                        port=config['settings']['DATABASE_PORT'],
                        database=config['settings']['DATABASE_DBNAME'])
        cursor = cnx.cursor()

        if args.database_list_backends:
            Console.pmsg("Listing backends in the database...")            
            sql = "SELECT proxy FROM backends"
            try:
                cursor.execute(sql)
                for (proxy) in cursor:
                    Console.pmsg("Backend: %s" % proxy)

            except mysql.connector.Error as err:
                Console.perr(err.msg)
            else:
                Console.pmsg("OK")
            cursor.close()
            cnx.close()
            sys.exit(0)

        if args.database_add_backend:
            Console.pmsg("Adding backend to database...")
            uid = sha256(str(uuid.uuid4()))
            proxy = args.database_add_backend
            sql = "INSERT INTO backends(id, proxy) VALUES('%s','%s')" % (uid, proxy)
            try:
                Console.pmsg("Adding backend {}: ".format(proxy))
                cursor.execute(sql)
                cnx.commit()
            except mysql.connector.Error as err:
                Console.perr(err.msg)
            else:
                Console.pmsg("OK")
            cursor.close()
            cnx.close()
            sys.exit(0)

        if args.database_remove_backend:
            Console.pmsg("Removing backend from database...")            
            proxy = args.database_remove_backend
            sql = "DELETE FROM backends WHERE proxy='%s'" % proxy
            try:
                Console.pmsg("Removing backend {}: ".format(proxy))
                cursor.execute(sql)
                cnx.commit()
            except mysql.connector.Error as err:
                Console.perr(err.msg)
            else:
                Console.pmsg("OK")
            cursor.close()
            cnx.close()
            sys.exit(0)

    if config['settings']['DATABASE_MODE'] == "mysql" and config['settings']['AUTH_MODE'] == "database":
        cnx = mysql.connector.connect(user=config['settings']['DATABASE_USERNAME'], password=config['settings']['DATABASE_PASSWORD'],
                        host=config['settings']['DATABASE_HOSTNAME'],
                        port=config['settings']['DATABASE_PORT'],
                        database=config['settings']['DATABASE_DBNAME'])

        cursor = cnx.cursor()
        if args.database_add_user:
            Console.pmsg("Adding user to database...")
            uid = sha256(str(uuid.uuid4()))
            username = args.database_add_user.split(":")[0]
            password = str(args.database_add_user.split(":")[1])
            if config['frontend']['AUTH_SHA512'] == "true":
                password = hash_password(password)
            sql = "INSERT INTO users(id, username, password) VALUES('%s','%s','%s')" % (uid, username, password)
            try:
                Console.pmsg("Adding user {}: ".format(username))
                cursor.execute(sql)
                cnx.commit()
            except mysql.connector.Error as err:
                Console.perr(err.msg)
            else:
                Console.pmsg("OK")
            cursor.close()
            cnx.close()
            sys.exit(0)

        if args.database_remove_user:
            Console.pmsg("Removing user from database...")            
            username = args.database_remove_user
            sql = "DELETE FROM users WHERE username='%s'" % username
            try:
                Console.pmsg("Removing user {}: ".format(username))
                cursor.execute(sql)
                cnx.commit()
            except mysql.connector.Error as err:
                Console.perr(err.msg)
            else:
                Console.pmsg("OK")
            cursor.close()
            cnx.close()
            sys.exit(0)

        if args.database_list_users:
            Console.pmsg("Listing users in the database...")            
            sql = "SELECT username FROM users"
            try:
                cursor.execute(sql)
                for (username) in cursor:
                    Console.pmsg("Username: %s" % username)

            except mysql.connector.Error as err:
                Console.perr(err.msg)
            else:
                Console.pmsg("OK")
            cursor.close()
            cnx.close()
            sys.exit(0)

    Console.pmsg("Starting sproxy v1.1")
    Server.main(config)

            