# SPROXY - high-performance socks4/socks5 proxy load-balancer

SPROXY is a high-performance socks4/socks5 proxy load-balancer. 

```
<source> <====> <SPROXY> <===> <random_socks5_proxy> <===> <target>
``` 

You can test if SPROXY is working by using curl:

```
curl --socks5 127.0.0.1:1080 -U username:password http://ip-api.com
```