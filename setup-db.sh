#!/bin/sh
set -e

# Create the database
psql -v ON_ERROR_STOP=1 <<-EOSQL
  CREATE DATABASE quota;
EOSQL

# Populate the schema and min/max vlan Ids
psql -v ON_ERROR_STOP=1 --username ${POSTGRES_USER} --dbname quota <<-EOSQL
  CREATE TABLE quota_violations(
    username TEXT PRIMARY KEY NOT NULL,
    triggered  BIGINT NOT NULL,
    last_notified BIGINT
  );
EOSQL
