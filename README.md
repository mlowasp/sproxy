# SPROXY - high-performance socks4/socks5 proxy load-balancer

## About

SPROXY is a high-performance socks4/socks5 proxy load-balancer. 

## Usage

SPROXY will start a socks5 proxy server on the configured listen IPv4 and port. It will then forward everything to the configured backend proxy servers.

```
<source> <====> <SPROXY> <===> <random_socks5_proxy> <===> <target>
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

[frontend]

# available socks versions: 4, 5
SOCKS_VERSION=5

LISTEN_IP=127.0.0.1
LISTEN_PORT=1080

# optional (remove or leave empty for no authentication)
AUTH_USERNAME=username
AUTH_PASSWORD=password

[backend]

# socks5 format (with auth): BACKEND_NAME=socks5://username:password@ipv4:port
# socks5 format (with auth): BACKEND_NAME=socks4://username:password@ipv4:port
# socks4 format (without auth): BACKEND_NAME=socks5://ipv4:port
# socks4 format (without auth): BACKEND_NAME=socks4://ipv4:port
# NOTE: each "BACKEND_NAME" must be unique (ie; BACKEND_0, BACKEND_1, etc...)

BACKEND0=socks5://username:password@ipv4:port1
BACKEND1=socks5://username:password@ipv4:port2
```

### Example using TOR

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

You can use SPROXY to load-balance every tcp connection to a random TOR circuit using the following sproxy.conf file:

```
[settings]

# available log levels are: none, info, debug
LOG_LEVEL=none
LOG_FILENAME=/var/log/sproxy.log

# available load balancing modes are: leastconn, random
LOAD_BALANCING_MODE=random

[frontend]

# available socks versions: 4, 5
SOCKS_VERSION=5

LISTEN_IP=127.0.0.1
LISTEN_PORT=1080

# optional (remove or leave empty for no authentication)
AUTH_USERNAME=username
AUTH_PASSWORD=password

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