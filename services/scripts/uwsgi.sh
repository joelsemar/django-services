#!/bin/bash
cd /opt
wget http://projects.unbit.it/downloads/uwsgi-1.0.4.tar.gz
tar -xvf uwsgi-1.0.4.tar.gz
cd uwsgi-1.0.4
make
cp uwsgi /usr/sbin

cat > "/etc/init/igt.conf" << EOF
description "uWSGI server for iGoToo"

start on runlevel [2345]
stop on runlevel [!2345]

respawn
exec /usr/sbin/uwsgi --socket /opt/run/www-data/igt.sock --logto /var/log/uwsgi.log --chmod-socket --module wsgi_app --pythonpath /srv/igotooserver/wsgi/ -p 12
EOF

touch /opt/run/www-data.sock

start igt 

