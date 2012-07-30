#!/bin/bash
#run this before doing anything else, (set default to utf-8)
apt-get -y install python-software-properties
add-apt-repository ppa:pitti/postgresql
add-apt-repository ppa:ubuntugis/ubuntugis-unstable
apt-get update
apt-get install -y postgresql-9.0 postgresql-server-dev-9.0 postgresql-contrib-9.0 proj libgeos-3.2.2 
apt-get install -y libgeos-c1 libgeos-dev  libgdal1-dev build-essential libxml2 libxml2-dev checkinstall
apt-get -y  install python-psycopg2 


cd /opt

wget http://postgis.refractions.net/download/postgis-1.5.2.tar.gz
tar zxvf postgis-1.5.2.tar.gz && cd postgis-1.5.2/
./configure &&  make && sudo checkinstall --pkgname postgis-1.5.2 --pkgversion 1.5.2-src --default

sudo -u postgres pg_dropcluster --stop 9.0 main
sudo -u postgres pg_createcluster --start -e UTF-8 9.0 main

POSTGIS_SQL_PATH=`pg_config --sharedir`/contrib/postgis-1.5
sudo -u postgres createdb -E utf8 -O postgres -U postgres template_postgis
sudo -u postgres createlang -d template_postgis plpgsql # Adding PLPGSQL language support.
sudo -u postgres psql -d postgres -c "UPDATE pg_database SET datistemplate='true' WHERE datname='template_postgis';"
sudo -u postgres psql -d template_postgis -f $POSTGIS_SQL_PATH/hstore.sql
sudo -u postgres psql -d template_postgis -f $POSTGIS_SQL_PATH/postgis.sql
sudo -u postgres psql -d template_postgis -f $POSTGIS_SQL_PATH/spatial_ref_sys.sql

# Enabling users to alter spatial tables.
sudo -u postgres psql -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;"
sudo -u postgres psql -d template_postgis -c "GRANT ALL ON geography_columns TO PUBLIC;"
sudo -u postgres psql -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"


cat > "/etc/postgresql/9.0/main/pg_hba.conf" << EOF


# This file is read on server startup and when the postmaster receives
# a SIGHUP signal.  If you edit the file on a running system, you have
# to SIGHUP the postmaster for the changes to take effect.  You can
# use "pg_ctl reload" to do that.

# Put your actual configuration here
# ----------------------------------
#
# If you want to allow non-local connections, you need to add more
# "host" records.  In that case you will also need to make PostgreSQL
# listen on a non-local interface via the listen_addresses
# configuration parameter, or via the -i or -h command line switches.




# DO NOT DISABLE!
# If you change this first entry you will need to make sure that the
# database
# super user can access the database using some other method.
# Noninteractive
# access to all databases is required during automatic maintenance
# (custom daily cronjobs, replication, and similar tasks).
#
# Database administrative login by UNIX sockets
local   all         postgres                                    trust

# TYPE  DATABASE        USER            CIDR-ADDRESS            METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     password
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 password
host    tdeserver       tdeserver        0.0.0.0/0       md5
EOF
sudo /etc/init.d/postgresql restart
