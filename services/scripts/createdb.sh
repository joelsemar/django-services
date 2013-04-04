#!/bin/bash
SERVER_NAME=$1
USE_POSTGIS=$2
echo "CREATE USER  $SERVER_NAME WITH PASSWORD '$SERVER_NAME' --createdb" | sudo -u postgres psql
if [ -z $USE_POSTGIS]
  then
    sudo -u postgres createdb -T template_postgis -E utf8 -O $SERVER_NAME $SERVER_NAME
  else
    sudo -u postgres createdb -E utf8 -O $SERVER_NAME $SERVER_NAME

fi


echo "GRANT ALL PRIVILEGES ON DATABASE $SERVER_NAME to $SERVER_NAME" | sudo -u postgres psql
