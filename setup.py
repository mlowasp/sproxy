setup(
    name='sproxy', 
    version='1.0', 
    author='Maxime Labelle',
    author_email='maxime.labelle@owasp.org', 
    description='sproxy is a high-performance socks4/socks5 proxy load-balancer',
    scripts=['sproxy.py'],
    data_files=[('/etc/systemd/system', ['etc/sproxy.service']), ('/etc/sproxy', ['etc/sproxy/sproxy.conf'])], 
    install_requires=['PySocks','termcolor', 'configparser'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
)