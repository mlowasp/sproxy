#!/usr/bin/env bash
cd src
pyinstaller -F sproxy.py
cd ..
pandoc src/sproxy.1.md -s -t man > sproxy_1.0-amd64/sproxy.1
cp src/dist/sproxy sproxy_1.0-amd64/
cp -r etc sproxy_1.0-amd64/
dpkg-deb --build --root-owner-group sproxy_1.0-amd64