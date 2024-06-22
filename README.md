# SPROXY

![SPROXY logo](https://raw.githubusercontent.com/mlowasp/sproxy/main/logo/sproxy.png)

## About

SPROXY is a high-performance socks4/socks5 proxy load-balancer. 

## Usage

SPROXY will start a socks5 proxy server on the configured listen IPv4 and port. It will then forward everything to the configured backend proxy servers.

```
<source> <====> <SPROXY> <===> <random_socks_proxy> <===> <target>
``` 

SPROXY will be installed as a service:

```
service sproxy start
```

You can test SPROXY using curl:

```
curl --socks5 127.0.0.1:1080 -U username:password http://ip-api.com
```

## Configuration

The configuration file is pretty straightforward:

```
[settings]

# available log levels are: none, info, debug
LOG_LEVEL=none
LOG_FILENAME=/var/log/sproxy.log

# available load balancing modes are: leastconn, random
LOAD_BALANCING_MODE=leastconn

# database support for mysql only
DATABASE_HOSTNAME=127.0.0.1
DATABASE_PORT=3306
DATABASE_DBNAME=sproxy
DATABASE_USERNAME=sproxy
DATABASE_PASSWORd=password

[frontend]

LISTEN_IP=127.0.0.1
LISTEN_PORT=1080

# optional (remove or leave empty for no authentication)
AUTH_USERNAME=username
AUTH_PASSWORD=password

# possible values: true|false
AUTH_SCRYPT=false

# change this if using scrypt
AUTH_SCRYPT_SALT=

# possible values: config|database
AUTH_MODE=config

[backend]

# socks5 format (with auth): BACKEND_NAME=socks5://username:password@ipv4:port
# socks5 format (with auth): BACKEND_NAME=socks4://username:password@ipv4:port
# socks4 format (without auth): BACKEND_NAME=socks5://ipv4:port
# socks4 format (without auth): BACKEND_NAME=socks4://ipv4:port
# NOTE: each "BACKEND_NAME" must be unique (ie; BACKEND_0, BACKEND_1, etc...)

BACKEND0=socks5://username:password@ipv4:port1
BACKEND1=socks5://username:password@ipv4:port2
```

If you want to use scrypt hashes for your user's password; use AUTH_SCRYPT=true and use the scrypt hash hex of the password in the config file, ie:

```
# optional (remove or leave empty for no authentication)
AUTH_USERNAME=username

# the password is: password
AUTH_PASSWORD=53e29a037248e6058cb93e58dbf15d80c6139ac452fa0993c864323a9522050833dac73e3ab2ab3e107b72a216ba9ff7dcb93027808175fe03ea728872e0b27f

AUTH_SCRYPT=true

# change this (do not use this salt in production)
AUTH_SCRYPT_SALT=804158fa6e84126ce1dc96d419dc6ad2274aeb8c866e248fce85cbe89096f9a4b5cb4948a8a0e22e7c5cb42c800c278c48e85c2c2ff19338c90bf24fe5512759
```

You can [use this tool to generate the scrypt hash](https://www.browserling.com/tools/scrypt)

## Database based configuration

You can use a mysql database to configure SPROXY authentication users and the backends. Enter the database connection parameters in the 'settings' section of the configuration file:

```
DATABASE_HOSTNAME=127.0.0.1
DATABASE_PORT=3306
DATABASE_DBNAME=sproxy
DATABASE_USERNAME=sproxy
DATABASE_PASSWORd=password
```

In order to use a mysql database to authenticate your users, set the following parameter in the 'frontend' section of the configuration file:

```
[frontend]
# possible values: config|database
AUTH_MODE=database
```

Now create the required tables in your "sproxy" database;

```
sproxy --database-create-tables
```

If you want to use the database for your backends as well, make sure you have the "BACKEND_MODE=database" parameter setup in the "backend" section of your configuration file.

```
[backend]
# possible values: config|database
BACKEND_MODE=database
```

## Creating the database tables

```
sproxy --database-create-tables
```

Here is the SQL for the "backends" table:

```
CREATE TABLE `backends` (
  `id` varchar(64) NOT NULL,
  `proxy` text DEFAULT NULL,  
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Here is the SQL for the "users" table:

```
CREATE TABLE `users` (
  `id` varchar(64) NOT NULL,
  `username` text DEFAULT NULL,
  `password` text DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Listing users

```
sproxy --database-list-users
```

### Listing backends

```
sproxy --database-list-backends
```

## Simple example using TOR

Let's say you have the following TOR circuits setup in your /etc/tor/torrc configuration file:

```
## Configuration file for a typical Tor user
## Last updated 9 October 2013 for Tor 0.2.5.2-alpha.
## (may or may not work for much older or much newer versions of Tor.)
##
## Lines that begin with "## " try to explain what's going on. Lines
## that begin with just "#" are disabled commands: you can enable them
## by removing the "#" symbol.
##
## See 'man tor', or https://www.torproject.org/docs/tor-manual.html,
## for more options you can use in this file.
##
## Tor will look for this file in various places based on your platform:
## https://www.torproject.org/docs/faq#torrc

## Tor opens a socks proxy on port 9050 by default -- even if you don't
## configure one below. Set "SocksPort 0" if you plan to run Tor only
## as a relay, and not make any local application connections yourself.
SocksPort 9050 # Default: Bind to localhost:9050 for local connections.
SocksPort 9051 # Default: Bind to localhost:9051 for local connections.
SocksPort 9052 # Default: Bind to localhost:9052 for local connections.
SocksPort 9053 # Default: Bind to localhost:9053 for local connections.
SocksPort 9054 # Default: Bind to localhost:9054 for local connections.
SocksPort 9055 # Default: Bind to localhost:9055 for local connections.
SocksPort 9056 # Default: Bind to localhost:9056 for local connections.
SocksPort 9057 # Default: Bind to localhost:9057 for local connections.
SocksPort 9058 # Default: Bind to localhost:9058 for local connections.
SocksPort 9059 # Default: Bind to localhost:9059 for local connections.
#...
```

You can use SPROXY to load-balance every incoming tcp connection to a random TOR circuit using the following sproxy.conf file:

```
[settings]

# available log levels are: none, info, debug
LOG_LEVEL=none
LOG_FILENAME=/var/log/sproxy.log

# available load balancing modes are: leastconn, random
LOAD_BALANCING_MODE=random

[frontend]

LISTEN_IP=127.0.0.1
LISTEN_PORT=1080

# optional (remove or leave empty for no authentication)
AUTH_USERNAME=username
AUTH_PASSWORD=password
# possible values: true|false
AUTH_SHA512=false
# possible values: config|database
AUTH_MODE=config

[backend]

# socks5 format (with auth): BACKEND_NAME=socks5://username:password@ipv4:port
# socks5 format (with auth): BACKEND_NAME=socks4://username:password@ipv4:port
# socks4 format (without auth): BACKEND_NAME=socks5://ipv4:port
# socks4 format (without auth): BACKEND_NAME=socks4://ipv4:port
# NOTE: each "BACKEND_NAME" must be unique (ie; BACKEND_0, BACKEND_1, etc...)

TOR0=socks5://127.0.0.1:9050
TOR1=socks5://127.0.0.1:9051
TOR2=socks5://127.0.0.1:9052
TOR3=socks5://127.0.0.1:9053
TOR4=socks5://127.0.0.1:9054
TOR5=socks5://127.0.0.1:9055
TOR6=socks5://127.0.0.1:9056
TOR7=socks5://127.0.0.1:9057
TOR8=socks5://127.0.0.1:9058
TOR9=socks5://127.0.0.1:9059

```

You can test SPROXY using curl, every time curl is executed, a random TOR circuit will be used:

```
curl --socks5 127.0.0.1:1080 -U username:password http://ip-api.com
```

## Proxy load balancing for various tools

Some tools can't be used with proxychains, but you can use SPROXY instead. Here is an example using wpscan:

```
wpscan -v --proxy socks5://127.0.0.1:1080 --proxy-auth username:password --url http://target.tld
```

## TODO

- bandwidth monitoring
- bandwidth quotas
- web based frontend

## License

SPROXY is released under the MIT license and was written by Maxime Labelle <maxime.labelle@owasp.org>