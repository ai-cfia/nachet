#!/bin/bash
# This script sets up the local development environment for the Nachet project.

SCHEMA_VERSION=$1
DB_NAME=$2
DB_USER=$3
PGPASSWORD=$4

if [ -z "$SCHEMA_VERSION" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$PGPASSWORD" ]; then
  echo "Usage: $0 <schema_version> <db_name> <db_user> <db_password>"
  exit 1
fi

# delete and recreate the public schema to ensure a clean state
docker exec -it nachet-db psql -h 127.0.0.1 -U ${DB_USER} -d ${DB_NAME} -c "DROP SCHEMA IF EXISTS \"nachet_${SCHEMA_VERSION}\" CASCADE; CREATE SCHEMA \"nachet_${SCHEMA_VERSION}\";"

# check if files exist
if [ ! -f "datastore/nachet/db/bytebase/schema_nachet_${SCHEMA_VERSION}.sql" ]; then
  echo "Schema file datastore/nachet/db/bytebase/schema_nachet_${SCHEMA_VERSION}.sql not found!"
  exit 1
fi

if [ ! -f "datastore/nachet/db/bytebase/constants_nachet_${SCHEMA_VERSION}.sql" ]; then
  echo "Constants file datastore/nachet/db/bytebase/constants_nachet_${SCHEMA_VERSION}.sql not found!"
  exit 1
fi

if [ ! -f "datastore/nachet/db/bytebase/dev_data_nachet_${SCHEMA_VERSION}.sql" ]; then
  echo "Dev data file datastore/nachet/db/bytebase/dev_data_nachet_${SCHEMA_VERSION}.sql not found!"
  exit 1
fi

# copy the schema files to the container
docker cp datastore/nachet/db/bytebase/schema_nachet_${SCHEMA_VERSION}.sql nachet-db:/schema_nachet_${SCHEMA_VERSION}.sql
docker cp datastore/nachet/db/bytebase/constants_nachet_${SCHEMA_VERSION}.sql nachet-db:/constants_nachet_${SCHEMA_VERSION}.sql
docker cp datastore/nachet/db/bytebase/dev_data_nachet_${SCHEMA_VERSION}.sql nachet-db:/dev_data_nachet_${SCHEMA_VERSION}.sql

# load the schema files
docker exec -it nachet-db psql -h 127.0.0.1 -U ${DB_USER} -d ${DB_NAME} -f /schema_nachet_${SCHEMA_VERSION}.sql
docker exec -it nachet-db psql -h 127.0.0.1 -U ${DB_USER} -d ${DB_NAME} -f /constants_nachet_${SCHEMA_VERSION}.sql
docker exec -it nachet-db psql -h 127.0.0.1 -U ${DB_USER} -d ${DB_NAME} -f /dev_data_nachet_${SCHEMA_VERSION}.sql
