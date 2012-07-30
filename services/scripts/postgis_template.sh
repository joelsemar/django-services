#!/bin/bash
#need the template_postgis
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
