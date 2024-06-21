# SPROXY - high-performance socks4/socks5 proxy load-balancer

SPROXY is a high-performance socks4/socks5 proxy load-balancer. 

```
<source> <====> <SPROXY> <===> <random_socks5_proxy> <===> <target>
``` 

You can test if SPROXY is working by using curl:

```
curl --socks5 127.0.0.1:1080 -U username:password http://ip-api.com
```

The configuration file is very easy to configure:

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