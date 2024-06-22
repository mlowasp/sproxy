#!/usr/bin/env bash
cd src
pyinstaller -F sproxy.py
cd ..
cp src/dist/sproxy sproxy_1.0-amd64/usr/bin/
cp -r src/etc/sproxy/sproxy.conf sproxy_1.0-amd64/etc/sproxy/
cp -r src/etc/sproxy.service sproxy_1.0-amd64/etc/systemd/system/
dpkg-deb --build --root-owner-group sproxy_1.0-amd64